"""Create a small source-and-evidence ZIP; excludes secrets, caches and model files."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
FILES = ['README.md', 'SUBMISSION.md', 'requirements.txt', 'run_eval.py', 'run.ps1', 'import_manual.py', 'package_submission.py']
DIRECTORIES = ['tasks', 'reference', 'graders', 'tests', 'results', 'transcripts', 'manual_frontier']


def main():
    if not list((ROOT / 'results').glob('*/summary.json')):
        raise SystemExit('Complete a model run before packaging evidence.')
    paths = [ROOT / name for name in FILES]
    for name in DIRECTORIES:
        paths.extend(p for p in (ROOT / name).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts
                     and p.suffix in {'.py', '.json', '.csv', '.md', '.txt'})
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise SystemExit('Missing required files: ' + ', '.join(missing))
    destination = ROOT / 'dist' / 'iam-reasoning-eval.zip'
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            archive.write(path, 'iam-reasoning-eval/' + path.relative_to(ROOT).as_posix())
    with ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise SystemExit('Archive integrity check failed')
        count = len(archive.namelist())
    if destination.stat().st_size > 50_000_000:
        raise SystemExit('Archive exceeds the guide limit of 50 MB')
    print(f'Created {destination} ({destination.stat().st_size:,} bytes, {count} files); integrity verified.')


if __name__ == '__main__':
    main()
