"""Prepare browser assets for Vercel's CDN and verify required source files."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def main():
    required = [ROOT / 'data' / 'owners.csv', ROOT / 'assets' / 'logo_diggaj.png']
    required.extend(ROOT / 'SalesPresenterWeb' / ('Neopolis Wing %d SalesPresenter.pdf' % wing)
                    for wing in range(1, 20))
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit('Required website data is missing: ' + ', '.join(missing))
    target = ROOT / 'public' / 'static'
    target.mkdir(parents=True, exist_ok=True)
    for filename in ('app.js', 'style.css'):
        shutil.copy2(ROOT / 'static' / filename, target / filename)
    print('Website assets prepared; all 19 presenters and client data are present.')


if __name__ == '__main__':
    main()
