# Neopolis website

A simple, mobile-friendly website for Diggaj Realty with two tabs:

- **Generate PDF:** enter a unit number, optional facing and price; choose whether to show "negotiable"; download the finished brochure.
- **Owner Search:** search all fields in the supplied booked-clients sheet. View every applicant for a unit, then combine the owner details with the brochure when the generator has a matching plan.

No login, desktop launcher or installation is needed to use the deployed website. Open its HTTPS link on your phone, tablet or computer.

## Deploy

See [DEPLOY.md](DEPLOY.md). The project is configured for Vercel with `vercel.json`, Python 3.12 and a browser-asset build step.

## Project files

- `app.py`: website routes and PDF download endpoint.
- `akash.py`: brochure layout and presenter lookup engine.
- `owners.py`: CSV search and owner pages in combined PDFs.
- `templates/` and `static/`: website interface.
- `SalesPresenter/` and `assets/`: developer source PDFs and brochure images.
- `data/owners.csv`: the client sheet used by the website.

Replace `data/owners.csv` and redeploy to update client records. The website uses the included copy, not the original file in Downloads.

## Local development (optional)

Install `requirements.txt` and run `python app.py`, then visit http://127.0.0.1:8000. This is for development; other devices use the deployed Vercel link.
