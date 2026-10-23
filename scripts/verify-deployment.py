#!/usr/bin/env python3
"""Compare a served website with generated files, without browser automation."""
import argparse
import hashlib
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_url', help='Published Pages URL, including the repository subpath')
    parser.add_argument('--site', type=Path, default=ROOT / 'site')
    parser.add_argument('--attempts', type=int, default=6)
    parser.add_argument('--delay', type=float, default=5)
    parser.add_argument('--timeout', type=float, default=15)
    parser.add_argument('--allow-http', action='store_true', help='Local test servers only')
    args = parser.parse_args()
    url = urlsplit(args.base_url)
    schemes = ('https', 'http') if args.allow_http else ('https',)
    if url.scheme not in schemes or not url.netloc or url.query or url.fragment:
        parser.error('Provide a valid HTTPS base URL without a query or fragment')
    if args.attempts < 1 or args.delay < 0 or args.timeout <= 0:
        parser.error('Attempts and timeout must be positive, and delay nonnegative')
    files = sorted(path for path in args.site.rglob('*') if path.is_file() and path.name != '.nojekyll')
    if not files:
        parser.error('No generated files found; build the website first')
    pending = {path.relative_to(args.site).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    total = len(pending)
    base = args.base_url.rstrip('/') + '/'
    for attempt in range(1, args.attempts + 1):
        failures = {}
        for relative, expected in pending.items():
            # A content-derived query avoids accepting a stale edge-cache response.
            request = urllib.request.Request(base + quote(relative, safe='/') + '?revision=' + expected[:16],
                                             headers={'User-Agent': 'project-hub-ci', 'Cache-Control': 'no-cache'})
            try:
                with urllib.request.urlopen(request, timeout=args.timeout) as response:
                    if response.status != 200:
                        raise ValueError(f'HTTP {response.status}')
                    actual = hashlib.sha256(response.read()).hexdigest()
                    if actual != expected:
                        raise ValueError('Published content differs from this build')
            except (OSError, ValueError) as error:
                failures[relative] = expected
                print(f'Attempt {attempt}: {relative}: {error}', flush=True)
        if not failures:
            print(f'PASS: {total} published pages/assets match this build.')
            return
        pending = failures
        if attempt < args.attempts:
            time.sleep(args.delay)
    raise SystemExit(f'FAIL: {len(pending)} published files did not match after {args.attempts} attempts.')


if __name__ == '__main__':
    main()
