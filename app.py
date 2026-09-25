"""Neopolis PDF Studio and owner directory."""
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from threading import Lock
from flask import Flask, g, jsonify, render_template, request, send_file
import akash
import owners

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4096
pdf_request_lock = Lock()
FACINGS = {'', 'North', 'South', 'East', 'West', 'North-east', 'North-west', 'South-east', 'South-west'}


@app.before_request
def serialize_pdf_requests():
    # PyMuPDF operations must not overlap within one serverless process.
    if request.path in ('/api/generate', '/api/owners/search', '/api/owners/unit'):
        pdf_request_lock.acquire()
        g.pdf_lock_held = True


@app.teardown_request
def release_pdf_lock(error):
    if g.pop('pdf_lock_held', False):
        pdf_request_lock.release()


@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.post('/api/owners/search')
def search_owners():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Enter a search term.'), 400
    query, page = data.get('query', ''), data.get('page', 1)
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 120 or type(page) is not int or not 1 <= page <= 10000:
        return jsonify(error='Search using 2 to 120 characters.'), 400
    try:
        result = owners.search(query.strip(), page)
        for group in result['results']:
            group['can_combine'] = owners.available(group['unit'])
        return jsonify(result)
    except (OSError, ValueError):
        app.logger.exception('Owner data unavailable')
        return jsonify(error='The client sheet is unavailable. Please check the server CSV file.'), 503


@app.post('/api/owners/unit')
def owner_unit():
    data = request.get_json(silent=True)
    unit = data.get('unit') if isinstance(data, dict) else None
    if not isinstance(unit, str) or not re.fullmatch(r'[0-9]{4,5}', unit):
        return jsonify(error='Enter a valid unit number.'), 400
    try:
        rows = owners.for_unit(unit)
        return {'unit': unit, 'records': rows, 'can_combine': bool(rows) and owners.available(unit)}
    except (OSError, ValueError):
        return jsonify(error='The client sheet is unavailable.'), 503


@app.get('/')
def home():
    try:
        rows = owners.records()
        count = len(rows)
        units = len({row.get('Unit') for row in rows})
    except (OSError, ValueError):
        count = units = 0
    return render_template('index.html', record_count=f'{count:,}', unit_count=f'{units:,}')


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/brand-logo')
def brand_logo():
    return send_file(akash.LOGO)


@app.post('/api/generate')
def generate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Please submit unit details.'), 400
    unit, facing, price = (data.get(k, '') for k in ('unit', 'facing', 'price'))
    if not all(isinstance(v, str) for v in (unit, facing, price)):
        return jsonify(error='Unit, facing and price must be text values.'), 400
    unit, facing, price = unit.strip(), facing.strip(), price.strip()
    combined = data.get('include_owners', False)
    negotiable = data.get('negotiable', True)
    add_diggaj_watermark = data.get('add_diggaj_watermark', True)
    add_my_details = data.get('add_my_details', True)
    if type(negotiable) is not bool:
        return jsonify(error='Invalid price negotiable option.'), 400
    if type(combined) is not bool:
        return jsonify(error='Invalid combined PDF option.'), 400
    if type(add_diggaj_watermark) is not bool or type(add_my_details) is not bool:
        return jsonify(error='Invalid branding option.'), 400
    if not re.fullmatch(r'[0-9]{4,5}', unit):
        return jsonify(error='Enter a 4 or 5 digit unit number, such as 4102 or 18102.'), 400
    if facing not in FACINGS:
        return jsonify(error='Choose a facing from the list.'), 400
    if price:
        try:
            if not re.fullmatch(r'\d{1,3}(?:\.\d{1,4})?', price) or not Decimal('0') < Decimal(price) <= Decimal('999'):
                raise InvalidOperation
        except InvalidOperation:
            return jsonify(error='Enter a price greater than 0 and up to 999 crore.'), 400
    u = None
    try:
        u = akash.lookup(unit)
        rows = owners.for_unit(unit) if combined else []
        if combined and not rows:
            return jsonify(error='No owner records match this unit. Generate a brochure without owner details instead.'), 422
        display_price = 'INR %s Cr' % (price or '[Price]')
        if negotiable:
            display_price += '  (negotiable)'
        pdf = akash.build(u, facing or '[Facing]', display_price, as_bytes=True, add_diggaj_watermark=add_diggaj_watermark, add_my_details=add_my_details)
        if combined:
            pdf = owners.append_records(pdf, unit, rows, add_diggaj_watermark, add_my_details)
        filename = 'Sobha_Neopolis_Unit_%s_Wing%d_Diggaj_Realty.pdf' % (unit, u['wing'])
        if combined:
            filename = filename.replace('.pdf', '_With_Owner_Records.pdf')
        response = send_file(BytesIO(pdf), mimetype='application/pdf', as_attachment=True, download_name=filename, max_age=0)
        response.headers['Cache-Control'] = 'no-store'
        return response
    except SystemExit:
        return jsonify(error='This unit could not be found or read in the wing presenter. Check the unit number.'), 422
    except Exception:
        app.logger.exception('PDF generation failed for unit %s', unit)
        return jsonify(error='The PDF could not be generated. Please try again or contact Akash.'), 500
    finally:
        if u is not None:
            u['doc'].close()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, threaded=False)
