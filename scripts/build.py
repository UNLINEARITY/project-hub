#!/usr/bin/env python3
"""Build the shared static directory and bilingual per-project pages."""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'site'
LANGUAGES = ('en', 'zh-Hans')
PAGES = ('index', 'support', 'privacy')
WORDS = {
    'en': dict(home='Apps', support='Support', privacy='Privacy', overview='Overview',
               skip='Skip to content', navigation='Navigation', language='简体中文',
               heading='Apps by unlinearity.', description='Explore each app, find help, and read how it handles your data.',
               macOS='Mac apps', explore='Explore the app', contact='Get in touch',
               appearance='Appearance', system='System', light='Light', dark='Dark'),
    'zh-Hans': dict(home='应用', support='支持', privacy='隐私政策', overview='产品介绍',
                    skip='跳到正文', navigation='导航', language='English',
                    heading='独立制作的应用。', description='了解每款应用，查找使用帮助与隐私政策。',
                    macOS='Mac 应用', explore='了解应用', contact='联系开发者',
                    appearance='外观', system='跟随系统', light='浅色', dark='深色'),
}


def filename(page, language):
    return f'{page}{"-zh-hans" if language == "zh-Hans" else ""}.html'


def escape(value):
    return html.escape(value, quote=True)


def shell(language, title, description, body, project=None, page='index'):
    w = WORDS[language]
    prefix = '../' if project else ''
    other = 'zh-Hans' if language == 'en' else 'en'
    home = prefix + filename('index', language)
    links = f'<a href="{home}">{w["home"]}</a>' if project else f'<a href="#projects">{w["home"]}</a>'
    if project:
        for key in PAGES:
            current = ' aria-current="page"' if key == page else ''
            label = w['overview' if key == 'index' else key]
            links += f'<a href="{filename(key, language)}"{current}>{label}</a>'
    else:
        links += f'<a href="#contact">{w["contact"]}</a>'
    links += f'<a href="{filename(page, other)}" lang="{other}" hreflang="{other}">{w["language"]}</a>'
    icon = 'assets/app-icon.png' if project else 'assets/favicon.svg'
    brand = escape(project['name']) if project else 'unlinearity'
    brand_image = '<img src="assets/app-icon.png" alt="" width="36" height="36">' if project else ''
    brand_href = filename('index', language)
    alternate = ''.join(f'<link rel="alternate" hreflang="{lang}" href="{filename(page, lang)}">' for lang in LANGUAGES)
    return f'''<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light"><meta name="description" content="{escape(description)}">
<title>{escape(title)}</title>
{alternate}
<link rel="icon" href="{icon}"><link rel="stylesheet" href="{prefix}assets/site.css">
<script src="{prefix}assets/theme.js" defer></script>
</head>
<body>
<a class="skip" href="#main">{w['skip']}</a>
<header class="bar"><a class="brand" href="{brand_href}">{brand_image}{brand}</a>
<nav aria-label="{w['navigation']}">{links}</nav></header>
<main id="main" class="{'document' if project else 'directory'}">{body}</main>
<footer id="contact"><div><h2>{w['contact']}</h2><a class="email" href="mailto:unlinearity@gmail.com">unlinearity@gmail.com</a></div>
<div class="footer-controls"><label class="theme" hidden>{w['appearance']}
<select aria-label="{w['appearance']}"><option value="system">{w['system']}</option><option value="light">{w['light']}</option><option value="dark">{w['dark']}</option></select></label>
<p>© 2026 unlinearity</p></div></footer>
</body></html>
'''


def homepage(projects, language):
    w = WORDS[language]
    content = f'<header class="directory-intro"><h1>{w["heading"]}</h1><p>{w["description"]}</p></header><div id="projects">'
    categories = list(dict.fromkeys(p['category'] for p in projects))
    for category in categories:
        content += f'<section class="category"><h2>{escape(w.get(category, category))}</h2>'
        for project in (p for p in projects if p['category'] == category):
            base = escape(project['slug']) + '/'
            content += f'''<article class="project">
<a class="project-art" href="{base}{filename('index', language)}" tabindex="-1" aria-hidden="true"><img src="{base}assets/app-icon.png" alt="" width="256" height="256"></a>
<div class="project-copy"><h3>{escape(project['name'])}</h3>
<p>{escape(project['summary'][language])}</p><p class="status">{escape(project['platform'])} · {escape(project['status'][language])}</p>
<a class="button" href="{base}{filename('index', language)}">{w['explore']}</a>
<div class="project-links"><a href="{base}{filename('support', language)}">{w['support']}</a><a href="{base}{filename('privacy', language)}">{w['privacy']}</a></div></div></article>'''
        content += '</section>'
    return shell(language, 'unlinearity — ' + w['home'], w['description'], content + '</div>')


def main():
    projects = json.loads((ROOT / 'projects.json').read_text())
    seen = set()
    for project in projects:
        slug = project['slug']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or slug in seen:
            raise ValueError(f'Invalid or duplicate project slug: {slug}')
        seen.add(slug)
        for language in LANGUAGES:
            for page in PAGES:
                path = ROOT / 'projects' / slug / 'pages' / filename(page, language)
                if not path.is_file():
                    raise FileNotFoundError(path)
    # Never follow a source link into files outside the public website.
    for folder in (ROOT / 'shared', ROOT / 'projects'):
        if folder.is_symlink() or any(path.is_symlink() for path in folder.rglob('*')):
            raise ValueError(f'Symbolic links are not allowed in website sources: {folder}')
    if OUTPUT.is_symlink():
        raise ValueError('The generated site directory must not be a symbolic link')
    # A removed page or asset must not survive in a later deployment.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()
    shutil.copytree(ROOT / 'shared', OUTPUT / 'assets', dirs_exist_ok=True)
    (OUTPUT / '.nojekyll').touch()
    for language in LANGUAGES:
        (OUTPUT / filename('index', language)).write_text(homepage(projects, language))
    for project in projects:
        target = OUTPUT / project['slug']
        target.mkdir(exist_ok=True)
        source = ROOT / 'projects' / project['slug']
        shutil.copytree(source / 'assets', target / 'assets', dirs_exist_ok=True)
        for language in LANGUAGES:
            for page in PAGES:
                body = (source / 'pages' / filename(page, language)).read_text()
                heading = project['name'] if page == 'index' else WORDS[language][page]
                title = heading if page == 'index' else heading + ' · ' + project['name']
                description = html.unescape(re.sub(r'<[^>]+>', '', re.search(r'<p>(.*?)</p>', body, re.S).group(1)))
                output = shell(language, title, description, body, project, page)
                (target / filename(page, language)).write_text(output)
    print(f'Built {2 + len(projects) * 6} pages in {OUTPUT}')


if __name__ == '__main__':
    main()
