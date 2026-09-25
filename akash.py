# -*- coding: utf-8 -*-
"""
Diggaj Realty - SOBHA Neopolis unit sale PDF generator.

    python akash.py <unit-no> [facing] [price]

    python akash.py 18102 East "3.9"
    python akash.py 13102                 -> facing/price left as placeholders

Unit number format: <wing><2-digit floor><series>   e.g. 18102 = Wing 18, Floor 10, Series 2.
Everything else (type code, BHK, SBA, carpet area, floor plan page) is read straight out of
the developer's Wing sales presenter PDF in the SalesPresenter folder.

FACING RULE: facing is the direction the main ENTRY door arrow points on the floor plan,
read against the plan's N compass. It is NOT the developer's series/facing marketing sheet.
Open page 1 of the output, look at the ENTRY marker, and pass the facing on the command line.

Requires: pymupdf  (pip install pymupdf)
"""
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
PRESENTERS = os.path.join(HERE, "SalesPresenter")
_WEB_PRESENTERS = os.path.join(HERE, "SalesPresenterWeb")
if os.path.isdir(_WEB_PRESENTERS):
    PRESENTERS = _WEB_PRESENTERS
ASSETS = os.path.join(HERE, "assets")
OUTDIR = os.path.join(os.path.expanduser("~"), "Downloads")

# ── brand ────────────────────────────────────────────────────────────────────
W, H = 841.89, 595.28                       # A4 landscape
M = 40
NAVY = (0.09, 0.15, 0.27)
GOLD = (0.70, 0.55, 0.28)
GOLD_L = (0.87, 0.79, 0.64)
INK = (0.13, 0.14, 0.16)
GREY = (0.45, 0.47, 0.50)
GREY_L = (0.62, 0.64, 0.67)
HAIR = (0.88, 0.89, 0.90)
WASH = (0.975, 0.970, 0.960)
WHITE = (1, 1, 1)

CONTACT_NAME = "Akash Kumar Dalai"
CONTACT_ROLE = "Senior Sales Manager - Resale Vertical, Diggaj Realty"
CONTACT_PH = "9902009808"
CONTACT_EM = "akash@diggajrealty.com"
CONTACT_WEB = "www.diggajrealty.com"
FOOT = ("For more details contact %s, Senior Sales Manager Resale vertical, Diggaj Realty, %s  |  %s"
        % (CONTACT_NAME, CONTACT_PH, CONTACT_EM))

LOGO = os.path.join(ASSETS, "logo_diggaj.png")
LOGO_AR = 432.0 / 204.0
PLAN_CLIP = pymupdf.Rect(395, 160, 1155, 665)   # drawing area inside a presenter plan page

TOWER = "2B + G + 18"
PROJECT_FACTS = [("19", "residential towers"), ("1,875", "homes in the community"),
                 ("25+", "acres of development"), (TOWER, "floors per tower"),
                 ("3", "clubhouses, 77,850 sq ft"), ("1,456", "quality checks pre-handover"),
                 ("28", "years of SOBHA")]

WHY_CARDS = [
    ("01", "Verified inventory",
     "Every unit is checked against the developer's own unit plan and floor-wise picklist - wing, floor, series, type, "
     "SBA, carpet area and facing. The numbers here come from those drawings, not from a portal."),
    ("02", "Banking & loan",
     "Sanction before you commit. We line up offers from the banks and NBFCs already approved on the project, compare "
     "rates and processing terms, and coordinate valuation and disbursement to the payment schedule."),
    ("03", "Interiors",
     "Vetted design and execution partners for full-home interiors or a single room, with indicative budgets per scope "
     "so you can plan the fit-out cost alongside the purchase."),
    ("04", "Honest pricing",
     "We tell you what comparable units in the same wing, floor band and facing have actually transacted at, what is "
     "negotiable and what is not. If a unit is overpriced for its floor plate, we will say so."),
    ("05", "Paperwork",
     "Booking, agreement, khata and registration - we track the checklist and the deadlines, coordinate with the "
     "developer's CRM desk, and flag anything in the documents that needs a lawyer's eye."),
    ("06", "We stay after the keys",
     "Handover snag list, utility and society formalities, warranty follow-ups. The relationship does not close when "
     "the registration does."),
    ("07", "Rental",
     "Tenant sourcing, rent benchmarking for the wing and configuration, agreement and deposit handling, and ongoing "
     "management if you are buying this as an investment."),
]

TILES = [
    ("c_club.jpg", "Club Santorini", "3 clubhouses in vibrant Santorini architecture, loaded with indoor pastimes."),
    ("c_entrance.jpg", "Entrance Plaza", "Grand arrival plaza with clock tower and a telescope at its zenith."),
    ("c_patio.jpg", "Patio & Private Garden", "Double-height private garden with pergolas - grow, dine, barbecue."),
    ("c_bed.jpg", "Interiors", "Tall windows, arched entrances, large tiles and smart safety features."),
]


# ── unit lookup ──────────────────────────────────────────────────────────────
def ordinal(n):
    return "%d%s" % (n, "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def lookup(unit):
    """Return every fact about a unit, read out of that wing's sales presenter."""
    if not unit.isdigit() or len(unit) < 4:
        raise SystemExit("Unit number must be digits, e.g. 18102 (wing 18, floor 10, series 2).")
    wing, floor, series = int(unit[:-3]), int(unit[-3:-1]), int(unit[-1])
    path = os.path.join(PRESENTERS, "Neopolis Wing %d SalesPresenter.pdf" % wing)
    if not os.path.exists(path):
        raise SystemExit("No presenter for Wing %d at %s" % (wing, path))

    doc = pymupdf.open(path)
    utype = plan_page = None
    same_type = 0

    # type code sits on the line above the unit number in the picklist grid
    for page in doc:
        t = page.get_text()
        if "Unit Picklist" not in t or unit not in t:
            continue
        lines = [l.strip() for l in t.splitlines()]
        for i, l in enumerate(lines):
            if l == unit:
                for j in range(i - 1, max(i - 4, -1), -1):
                    if re.fullmatch(r"[A-Z]\d{1,2}", lines[j]):
                        utype = lines[j]
                        break
            if utype:
                break
        if utype:
            same_type = sum(1 for l in lines if l == utype)
            break
    if not utype:
        raise SystemExit("Unit %s not found in the Wing %d picklist." % (unit, wing))

    # the plan page that lists this unit under "Apartment Number"
    for i, page in enumerate(doc):
        t = page.get_text()
        if "Unit Plans" in t and unit in t and re.search(r"^\s*%s\s*$" % utype, t, re.M):
            plan_page = i
            break
    if plan_page is None:
        raise SystemExit("No unit plan page found for type %s in Wing %d." % (utype, wing))

    t = doc[plan_page].get_text()
    bhk = re.search(r"(\dBHK)", t).group(1)
    # Some presenters split thousands with whitespace (e.g. Wing 4: 2 481.18).
    def area(label):
        match = re.search(re.escape(label) + r"\s+([\d.]+)\s+SQM\s*\|\s*([\d][\d,.\s]*?)\s+SFT", t)
        if not match:
            raise SystemExit("Could not read %s for unit %s on presenter page %d."
                             % (label, unit, plan_page + 1))
        return match.group(1), re.sub(r"\s+", "", match.group(2))

    sba_m, sba_f = area("SBA")
    car_m, car_f = area("CARPET AREA")
    rooms = dict(re.findall(r"(LIVING/DINING|KITCHEN|GARDEN)\s*\n?\s*(\d+ x \d+)", t))
    return dict(unit=unit, wing=wing, floor=floor, series=series, utype=utype, bhk=bhk,
                sba_m=sba_m, sba_f=sba_f, car_m=car_m, car_f=car_f,
                path=path, plan_page=plan_page, same_type=same_type,
                living=rooms.get("LIVING/DINING", ""), kitchen=rooms.get("KITCHEN", ""),
                garden=rooms.get("GARDEN", ""), doc=doc)


# ── drawing helpers ──────────────────────────────────────────────────────────
def tx(p, x, y, s, size=9, font="helv", color=INK, align=0, w=None, lh=1.4):
    if w is None:
        p.insert_text((x, y), s, fontname=font, fontsize=size, color=color)
    else:
        p.insert_textbox(pymupdf.Rect(x, y - size, x + w, y + 500), s, fontname=font,
                         fontsize=size, color=color, align=align, lineheight=lh)


def spaced(p, x, y, s, size, font, color, gap=1.8):
    for ch in s:
        p.insert_text((x, y), ch, fontname=font, fontsize=size, color=color)
        x += pymupdf.get_text_length(ch, font, size) + gap


def band(p, r, c):
    p.draw_rect(r, color=None, fill=c)


def rule(p, x0, y, x1, c=HAIR, w=0.6):
    p.draw_line((x0, y), (x1, y), color=c, width=w)


def eyebrow(p, x, y, s, w_=None, size=7.2):
    spaced(p, x, y, s, size, "hebo", NAVY, 1.9)
    if w_:
        rule(p, x, y + 6, x + w_, GOLD_L, 0.9)


def logo(p, xr, yc, width=118):
    h_ = width / LOGO_AR
    p.insert_image(pymupdf.Rect(xr - width, yc - h_ / 2, xr, yc + h_ / 2), filename=LOGO, keep_proportion=True)


def header(p, title, kicker, add_diggaj_watermark=True):
    tx(p, M, 44, "SOBHA NEOPOLIS", 16, "hebo", NAVY)
    tx(p, M, 59, kicker, 7.6, "helv", GREY)
    if add_diggaj_watermark:
        logo(p, W - M, 44)
    rule(p, M, 76, W - M, GOLD_L, 1.0)
    rule(p, M, 78.6, W - M, HAIR, 0.6)
    if title:
        spaced(p, M, 92, title, 7.2, "hebo", NAVY, 1.9)


def footer(p, n, add_my_details=True, total=3):
    rule(p, M, H - 34, W - M)
    if add_my_details:
        tx(p, M, H - 22, FOOT, 6.6, "helv", GREY)
    lbl = "%d / %d" % (n, total)
    tx(p, W - M - pymupdf.get_text_length(lbl, "hebo", 7.5), H - 22, lbl, 7.5, "hebo", NAVY)


def photo(p, r, f, cap=None, sub=None):
    p.insert_image(r, filename=os.path.join(ASSETS, f), keep_proportion=False)
    p.draw_rect(r, color=HAIR, width=0.6)
    if cap:
        tx(p, r.x0, r.y1 + 14, cap, 8.4, "hebo", NAVY)
    if sub:
        tx(p, r.x0, r.y1 + 25, sub, 6.8, "helv", GREY, 0, r.width, 1.45)


# ── document ─────────────────────────────────────────────────────────────────
def build(u, facing, price, as_bytes=False, add_diggaj_watermark=True, add_my_details=True):
    src, doc = u["doc"], pymupdf.open()
    unit, bhk = u["unit"], u["bhk"]
    fl = ordinal(u["floor"])

    # ══ PAGE 1 — THE UNIT ══
    p = doc.new_page(width=W, height=H)
    header(p, "UNIT No. %s   |   WING %d   |   %s FOR SALE" % (unit, u["wing"], bhk),
           "The Greek Paradise  -  Panathur, Bengaluru", add_diggaj_watermark)

    x0, cw = M, 300
    y = 126
    tx(p, x0, y, "%s APARTMENT" % bhk, 20, "hebo", NAVY)
    y += 21
    tx(p, x0, y, "Type %s   |   %s Facing   |   %s Floor" % (u["utype"], facing, fl), 10.5, "helv", GOLD)
    y += 11
    p.draw_line((x0, y), (x0 + 64, y), color=GOLD, width=1.8)
    y += 21
    tx(p, x0, y, "A well-planned %s in a %s Grecian tower at SOBHA Neopolis - en-suite bedrooms, a generous "
                 "living/dining spine, private garden and balconies." % (bhk, TOWER),
       8.2, "helv", GREY, 0, cw, 1.5)
    y += 42

    eyebrow(p, x0, y, "UNIT SNAPSHOT", cw)
    rows = [
        ("Project", "SOBHA Neopolis, Panathur, Bengaluru"),
        ("Unit No.", "%s  |  Type %s  |  Wing %d" % (unit, u["utype"], u["wing"])),
        ("Floor", "%s Floor  |  Series %d  |  %s" % (fl, u["series"], TOWER)),
        ("Configuration", "%s + Utility" % bhk),
        ("Facing", "%s  (main entry opens %s)" % (facing, facing.lower())),
        ("SBA", "%s sq m  |  %s sq ft" % (u["sba_m"], u["sba_f"])),
        ("Carpet area", "%s sq m  |  %s sq ft" % (u["car_m"], u["car_f"])),
        ("Outdoor", "Private garden + balconies" if u["garden"] else "Balconies"),
        ("Price", price),
    ]
    for i, (k, v) in enumerate(rows):
        ry = y + 8 + i * 15.5
        if i % 2 == 0:
            band(p, pymupdf.Rect(x0 - 4, ry - 1, x0 + cw + 4, ry + 14.5), WASH)
        tx(p, x0, ry + 10, k, 7.5, "hebo", GREY)
        tx(p, x0 + 88, ry + 10, v, 7.9, "helv", INK)
    y += 8 + len(rows) * 15.5 + 20

    eyebrow(p, x0, y, "WHY THIS HOME STANDS OUT", cw)
    y += 6
    bullets = ["Elevated %s-floor placement in a %s tower." % (fl, TOWER)]
    if u["living"]:
        bullets.append("Living/dining %s mm opening to balcony & garden." % u["living"])
    bullets.append("Bedrooms en-suite; master with walk-in wardrobe.")
    if u["kitchen"]:
        bullets.append("Open kitchen %s mm with attached utility." % u["kitchen"])
    bullets.append("Vaastu-compliant 8 ft entry, foyer and alcove.")
    bullets.append("Series %d of Wing %d - one of only %d such units in the wing."
                   % (u["series"], u["wing"], u["same_type"]))
    for b in bullets[:6]:
        y += 12.6
        p.draw_circle((x0 + 2.5, y - 2.5), 1.5, color=None, fill=GOLD)
        tx(p, x0 + 10, y, b, 7.7, "helv", INK)

    cy = H - 34 - 74
    r = pymupdf.Rect(x0, cy, x0 + cw, cy + 62)
    band(p, r, WASH)
    p.draw_rect(r, color=HAIR, width=0.6)
    p.draw_line((x0, cy), (x0, cy + 62), color=GOLD, width=2.6)
    if add_my_details: tx(p, x0 + 12, cy + 16, "FOR MORE DETAILS CONTACT", 7, "hebo", NAVY)
    if add_my_details: tx(p, x0 + 12, cy + 30, CONTACT_NAME, 10.5, "hebo", NAVY)
    if add_my_details: tx(p, x0 + 12, cy + 41, CONTACT_ROLE, 7.1, "helv", GREY)
    if add_my_details: tx(p, x0 + 12, cy + 52, "%s   |   %s   |   %s" % (CONTACT_PH, CONTACT_EM, CONTACT_WEB), 7.6, "helv", INK)

    px0, py0, px1, py1 = 362, 112, W - M, H - 50
    eyebrow(p, px0, py0 - 8, "UNIT FLOOR PLAN   |   TYPE %s   |   %s SFT" % (u["utype"], u["sba_f"]), px1 - px0)
    pr = pymupdf.Rect(px0, py0 + 8, px1, py1)
    p.draw_rect(pr, color=HAIR, width=0.7)
    p.show_pdf_page(pr + (6, 6, -6, -6), src, u["plan_page"], clip=PLAN_CLIP)
    cr = pymupdf.Rect(px0 + 12, py1 - 34, px0 + 152, py1 - 12)
    band(p, cr, WHITE)
    p.draw_rect(cr, color=GOLD, width=1.0)
    tx(p, cr.x0 + 10, cr.y0 + 14.5, "UNIT FACING: %s" % facing.upper(), 8.4, "hebo", NAVY)
    lb = "Developer drawing - not to scale"
    tx(p, px1 - 14 - pymupdf.get_text_length(lb, "helv", 7), py1 - 18, lb, 7, "helv", GREY_L)
    footer(p, 1, add_my_details, 3 if add_diggaj_watermark else 2)

    # ══ PAGE 2 — THE PROJECT ══
    p = doc.new_page(width=W, height=H)
    header(p, "ABOUT THE PROJECT", "19 neoclassical towers  -  1,875 units  -  25+ acres", add_diggaj_watermark)
    hero = pymupdf.Rect(M, 104, W - M, 284)
    p.insert_image(hero, filename=os.path.join(ASSETS, "c_hero.jpg"), keep_proportion=False)
    p.draw_rect(hero, color=HAIR, width=0.6)
    tx(p, M, 300, "SOBHA NEOPOLIS  -  THE GREEK PARADISE", 11.5, "hebo", NAVY)
    tx(p, M, 314, "Luxury residences in mainland Greek style - bevelled pediments, majestic columns and arches - across 19 "
                  "towers and 1,875 homes on 25+ acres at Panathur, minutes from the ORR IT corridor, Bellandur and "
                  "Marathahalli, with the ongoing CDP road network and Namma Metro Phase 2A/2B improving access across east "
                  "and south Bengaluru.", 7.5, "helv", GREY, 0, W - 2 * M, 1.45)

    fy = 344
    rule(p, M, fy, W - M, GOLD_L, 0.9)
    fw = (W - 2 * M) / len(PROJECT_FACTS)
    for i, (n, l) in enumerate(PROJECT_FACTS):
        x = M + i * fw
        tx(p, x, fy + 20, n, 13.5 if len(n) < 8 else 10.5, "hebo", NAVY)
        tx(p, x, fy + 32, l, 6.5, "helv", GREY, 0, fw - 10, 1.3)
        if i:
            p.draw_line((x - 9, fy + 6), (x - 9, fy + 38), color=HAIR, width=0.6)
    rule(p, M, fy + 46, W - M)

    tw4 = (W - 2 * M - 3 * 12) / 4.0
    th = tw4 * 0.56
    for i, (f, cap, sub) in enumerate(TILES):
        photo(p, pymupdf.Rect(M + i * (tw4 + 12), 406, M + i * (tw4 + 12) + tw4, 406 + th), f, cap, sub)
    footer(p, 2, add_my_details, 3 if add_diggaj_watermark else 2)

    # ══ PAGE 3 — WHY DIGGAJ ══
    p = doc.new_page(width=W, height=H)
    if add_diggaj_watermark:
        logo(p, W - M, 44)
    tx(p, M, 50, "WHY DIGGAJ REALTY", 24, "hebo", NAVY)
    p.draw_line((M, 62), (M + 72, 62), color=GOLD, width=2.4)
    tx(p, M, 82, "We do not list properties. We advise on them.", 11, "helv", GOLD)
    tx(p, M, 100, "Diggaj Realty works with buyers and owners across Bengaluru's premium residential market - from first "
                  "shortlist to registration and beyond - on one principle: you should know exactly what you are buying "
                  "before you pay for it.", 7.7, "helv", GREY, 0, 620, 1.5)
    rule(p, M, 124, W - M, GOLD_L, 0.9)

    cols, gap, chgt, row0 = 4, 14, 175, 152
    cwid = (W - 2 * M - (cols - 1) * gap) / cols
    for i, (num, head, body) in enumerate(WHY_CARDS):
        cx = M + (i % cols) * (cwid + gap)
        cy = row0 + (i // cols) * (chgt + 18)
        r = pymupdf.Rect(cx, cy, cx + cwid, cy + chgt)
        band(p, r, WHITE)
        p.draw_rect(r, color=HAIR, width=0.6)
        p.draw_line((cx, cy), (cx + cwid, cy), color=GOLD, width=2.2)
        tx(p, cx + 12, cy + 26, num, 14, "hebo", GOLD_L)
        tx(p, cx + 12, cy + 46, head, 9.2, "hebo", NAVY, 0, cwid - 24, 1.3)
        tx(p, cx + 12, cy + 68, body, 7.1, "helv", GREY, 0, cwid - 24, 1.5)

    cx = M + 3 * (cwid + gap)
    cy = row0 + (chgt + 18)
    r = pymupdf.Rect(cx, cy, cx + cwid, cy + chgt)
    band(p, r, NAVY)
    p.draw_line((cx, cy), (cx + cwid, cy), color=GOLD, width=2.2)
    tx(p, cx + 12, cy + 26, "TALK TO US ABOUT", 7, "hebo", GOLD_L)
    tx(p, cx + 12, cy + 45, "UNIT %s" % unit, 15, "hebo", WHITE)
    rule(p, cx + 12, cy + 57, cx + cwid - 12, GOLD, 1.0)
    if add_my_details: tx(p, cx + 12, cy + 77, CONTACT_NAME, 10, "hebo", WHITE)
    if add_my_details: tx(p, cx + 12, cy + 90, CONTACT_ROLE, 7, "hebo", (0.78, 0.81, 0.86), 0, cwid - 24, 1.4)
    if add_my_details: tx(p, cx + 12, cy + 123, CONTACT_PH, 11, "hebo", GOLD_L)
    if add_my_details: tx(p, cx + 12, cy + 139, CONTACT_EM, 7.8, "hebo", WHITE)
    if add_my_details: tx(p, cx + 12, cy + 151, CONTACT_WEB, 7.8, "hebo", WHITE)
    tx(p, cx + 12, cy + 166, "Site visits by prior appointment", 6.8, "helv", (0.66, 0.70, 0.77))

    rule(p, M, H - 34, W - M)
    if add_my_details: tx(p, M, H - 22, FOOT, 6.6, "helv", GREY)
    tx(p, W - M - pymupdf.get_text_length("3 / 3", "hebo", 7.5), H - 22, "3 / 3", 7.5, "hebo", NAVY)

    if not add_diggaj_watermark:
        doc.delete_page(-1)
    out = os.path.join(OUTDIR, "Sobha_Neopolis_Unit_%s_Wing%d_Diggaj_Realty.pdf" % (unit, u["wing"]))
    doc.set_metadata({"title": "SOBHA Neopolis - Unit %s, Wing %d - %s for Sale | Diggaj Realty" % (unit, u["wing"], bhk),
                      "author": "Diggaj Realty - %s" % CONTACT_NAME,
                      "subject": "%s %s sq ft, Type %s, %s facing" % (bhk, u["sba_f"], u["utype"], facing)})
    if as_bytes:
        try:
            return doc.tobytes(deflate=True, garbage=4)
        finally:
            doc.close()
    doc.save(out, deflate=True, garbage=4)
    doc.close()
    return out


def make(unit, facing, price_cr):
    """unit -> (facts, output path). facing/price_cr may be empty strings."""
    facing = facing.strip().capitalize() if facing.strip() else "[Facing]"
    price = ("INR %s Cr  (negotiable)" % price_cr.strip()) if price_cr.strip() else "INR [Price] Cr  (negotiable)"
    u = lookup(unit)
    return u, build(u, facing, price), facing


def report(u, out, facing):
    print("\n  Wing %d  |  %s floor  |  Series %d  |  Type %s  |  %s"
          % (u["wing"], ordinal(u["floor"]), u["series"], u["utype"], u["bhk"]))
    print("  SBA %s sq ft  |  Carpet %s sq ft  |  Facing %s" % (u["sba_f"], u["car_f"], facing))
    print("\n  Saved:  %s" % out)
    if facing == "[Facing]":
        print("\n  ! Facing left blank. Open page 1, look at the ENTRY arrow, and run it again\n"
              "    with the facing to fill it in.")


def interactive():
    print("=" * 66)
    print("  DIGGAJ REALTY  -  SOBHA Neopolis unit sale PDF")
    print("=" * 66)
    print("  Enter a unit number (e.g. 18102).  Blank facing/price = placeholders.")
    print("  Press Enter on an empty unit number to quit.\n")
    while True:
        try:
            unit = input("  Unit number : ").strip()
            if not unit:
                print("\n  Bye.")
                return
            facing = input("  Facing      : ").strip()
            price   = input("  Price in Cr : ").strip()
            u, out, facing = make(unit, facing, price)
            report(u, out, facing)
            if input("\n  Open it now? [y/N] ").strip().lower().startswith("y"):
                os.startfile(out)                                   # noqa: S606 (Windows)
        except SystemExit as e:                                     # bad unit number etc.
            print("\n  ! %s" % e)
        except Exception as e:                                      # never drop the window
            print("\n  ! Could not build that one: %s" % e)
        print("\n" + "-" * 66 + "\n")


def main():
    if len(sys.argv) < 2:
        interactive()
        return
    unit = sys.argv[1].strip()
    u, out, facing = make(unit,
                          sys.argv[2] if len(sys.argv) > 2 else "",
                          sys.argv[3] if len(sys.argv) > 3 else "")
    report(u, out, facing)


if __name__ == "__main__":
    main()
