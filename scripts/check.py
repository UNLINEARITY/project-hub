#!/usr/bin/env python3
"""Validate generated pages, links, and each project's language routes."""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.links = []
        self.ids = set()
        self.languages = []
        self.h1s = 0
        self.has_description = False
        self.alternates = {}
        self.feed(path.read_text())

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag == 'html':
            self.languages.append(attrs.get('lang'))
        if tag == 'h1':
            self.h1s += 1
        if tag == 'meta' and attrs.get('name') == 'description':
            self.has_description = bool(attrs.get('content'))
        if tag == 'img':
            assert 'alt' in attrs, f'{self.path}: image missing alt'
            assert 'width' in attrs and 'height' in attrs, f'{self.path}: image missing dimensions'
        if tag == 'link' and attrs.get('rel') == 'alternate':
            language = attrs.get('hreflang')
            assert language not in self.alternates, f'{self.path}: duplicate language route'
            self.alternates[language] = attrs.get('href')
        if attrs.get('id'):
            assert attrs['id'] not in self.ids, f'{self.path}: duplicate id {attrs["id"]}'
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if attrs.get(key):
                self.links.append(attrs[key])


def main():
    projects = json.loads((ROOT / 'projects.json').read_text())
    paths = sorted(SITE.rglob('*.html'))
    names = ('index', 'support', 'privacy')
    suffixes = {'en': '', 'zh-Hans': '-zh-hans', 'ja': '-ja'}
    languages_by_folder = {SITE.resolve(): ('en', 'zh-Hans')}
    expected = {SITE / 'index.html', SITE / 'index-zh-hans.html'}
    for project in projects:
        languages = project.get('languages', ('en', 'zh-Hans'))
        languages_by_folder[(SITE / project['slug']).resolve()] = languages
        expected.update(SITE / project['slug'] / f'{name}{suffixes[language]}.html'
                        for name in names for language in languages)
    assert set(paths) == expected, 'Unexpected or missing generated pages.'
    allowed = {'.html', '.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.avif', '.ico', '.woff', '.woff2'}
    for asset in SITE.rglob('*'):
        assert not asset.is_symlink(), f'Symbolic link in deployment artifact: {asset}'
        if asset.is_file():
            assert asset.stat().st_nlink == 1, f'Hard link in deployment artifact: {asset}'
            assert asset == SITE / '.nojekyll' or (asset.suffix.lower() in allowed
                and not any(part.startswith('.') for part in asset.relative_to(SITE).parts)), f'Non-web file in deployment artifact: {asset}'
    assert (SITE / '.nojekyll').is_file(), 'Missing .nojekyll marker'
    pages = {path.resolve(): Page(path) for path in paths}
    checked = 0
    for path, page in pages.items():
        languages = languages_by_folder[path.parent]
        assert len(page.languages) == 1 and page.languages[0] in languages, f'{path}: invalid language'
        assert page.h1s == 1, f'{path}: expected one main heading'
        assert page.has_description, f'{path}: missing description'
        assert set(page.alternates) == set(languages), f'{path}: missing language route'
        stem = path.stem.removesuffix('-zh-hans').removesuffix('-ja')
        for language in languages:
            assert page.alternates[language] == f'{stem}{suffixes[language]}.html', f'{path}: wrong language destination'
        expected_language = next((language for language, suffix in suffixes.items() if suffix and path.stem.endswith(suffix)), 'en')
        assert page.languages == [expected_language], f'{path}: language does not match route'
        for link in page.links:
            url = urlsplit(link)
            if url.scheme:
                assert url.scheme in ('mailto', 'https'), f'{path}: unexpected external URL {link}'
                continue
            assert not url.netloc and not url.path.startswith('/'), f'{path}: use portable relative links'
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            assert target.is_relative_to(SITE), f'{path}: link escapes website {link}'
            assert target.is_file(), f'{path}: missing target {link}'
            if url.fragment:
                assert target in pages and url.fragment in pages[target].ids, f'{path}: broken fragment {link}'
            checked += 1
    print(f'PASS: {len(pages)} multilingual pages, {checked} local links/assets, headings, and language routes.')


if __name__ == '__main__':
    main()
