#!/usr/bin/env python3
"""The same offline checks used locally and by GitHub Actions."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments):
    print('+ ' + ' '.join(map(str, arguments)), flush=True)
    subprocess.run(arguments, cwd=ROOT, check=True)


def main():
    run(sys.executable, '-m', 'compileall', '-q', 'scripts', 'tests')
    for source in sorted((ROOT / 'shared').rglob('*.js')):
        run('node', '--check', str(source))
    run(sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v')
    run(sys.executable, 'scripts/build.py')
    run(sys.executable, 'scripts/check.py')
    print('PASS: website CI checks completed; site/ is ready for packaging.')


if __name__ == '__main__':
    main()
