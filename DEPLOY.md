# Deploy the website to Vercel

## One-time setup

1. Put this folder in a Vercel project, or deploy this folder directly with `vercel --prod`. Include `SalesPresenterWeb/`, `assets/`, `data/owners.csv`, the Python files, `templates/`, `static/`, `requirements.txt`, `.python-version`, `.vercelignore`, and `vercel.json`. The client CSV is explicitly included by `.gitignore`.
2. If using the Vercel dashboard, choose **Add New > Project** and import the project source.
3. Select **Flask** as the framework preset if it is not detected automatically. Use the repository root as the root directory. The included configuration sets the build command; leave the output-directory setting at its framework default.
4. Click **Deploy**. Open the resulting HTTPS website URL.
5. Try unit **4102**, generate a PDF, and test Owner Search and a combined PDF. Test the link on your phone as well.

No environment variables, database, password or desktop software are required. The website has no login, as requested. Anyone who can access its deployment can use both tabs.

## What deployment includes

Vercel runs `app.py` as a Python Flask function. `build_vercel.py` checks that all 19 compact presenters and the CSV are included, then copies the browser files to `public/static/` for Vercel's CDN. The owner CSV and presenter PDFs stay in the server bundle; they are not copied to the public folder. PDFs are created in memory and returned for download.

The existing sample PDFs are about 1.47 MB. Vercel documents a 4.5 MB function response limit. The compact presenter set is about 31 MB; the original 292 MB presenter set is excluded from the deployed function. Do not upload the local virtual environment or generated test files; `.vercelignore` and the function exclusions handle these folders. Deployment on a Vercel account still needs to be performed and checked; local testing alone is not a hosted deployment test.

## Updating the site

Push changes to the connected repository to redeploy. Replace `data/owners.csv` when your client sheet changes. Retain its Unit column and the existing column headings.

Some units in the sheet cannot be resolved by the existing presenter lookup. Their owner records remain searchable, but the website only offers a combined PDF when it can read a matching plan.

## References

- [Flask deployment and CDN assets](https://vercel.com/docs/frameworks/backend/flask)
- [Python version and bundle configuration](https://vercel.com/docs/functions/runtimes/python)
- [Function limits](https://vercel.com/docs/functions/limitations)
