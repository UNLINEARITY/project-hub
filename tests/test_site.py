import functools
import hashlib
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class WebsiteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='project-hub-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'source'
        self.root.mkdir()
        shutil.copy2(SOURCE / 'projects.json', self.root)
        for name in ('scripts', 'projects', 'shared'):
            shutil.copytree(SOURCE / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__'))
        self.site = self.root / 'site'
        self.run_script('build.py')

    def run_script(self, name, *arguments, succeeds=True):
        result = subprocess.run([sys.executable, str(self.root / 'scripts' / name), *map(str, arguments)],
                                cwd=self.root, text=True, capture_output=True, timeout=30)
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, 'Invalid website unexpectedly passed')
        return result.stdout + result.stderr

    def test_valid_site_and_deterministic_clean_rebuild(self):
        def hashes():
            return {str(p.relative_to(self.site)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.site.rglob('*') if p.is_file()}
        self.run_script('check.py')
        expected = hashes()
        (self.site / 'removed-asset.css').write_text('old content')
        self.run_script('build.py')
        self.assertEqual(hashes(), expected)
        self.run_script('check.py')

    def test_broken_asset_link_fails_validation(self):
        (self.site / 'assets' / 'site.css').unlink()
        self.assertIn('missing target', self.run_script('check.py', succeeds=False))

    def test_language_switch_must_keep_the_same_page(self):
        page = self.site / 'event-horizon' / 'index.html'
        data = page.read_text().replace('hreflang="zh-Hans" href="index-zh-hans.html"',
                                        'hreflang="zh-Hans" href="support-zh-hans.html"')
        page.write_text(data)
        self.assertIn('wrong language destination', self.run_script('check.py', succeeds=False))

    def test_deployment_rejects_non_web_files(self):
        (self.site / 'private.env').write_text('disposable test value')
        self.assertIn('Non-web file', self.run_script('check.py', succeeds=False))

    def test_symlink_source_is_rejected_before_packaging(self):
        outside = self.root / 'outside.txt'
        outside.write_text('disposable test value')
        (self.root / 'shared' / 'linked.png').symlink_to(outside)
        self.assertIn('Symbolic links are not allowed', self.run_script('build.py', succeeds=False))

    def test_project_slug_cannot_escape_source_directory(self):
        manifest = self.root / 'projects.json'
        projects = json.loads(manifest.read_text())
        projects[0]['slug'] = '../outside'
        manifest.write_text(json.dumps(projects))
        self.assertIn('Invalid or duplicate project slug', self.run_script('build.py', succeeds=False))

    def test_page_language_must_match_its_route(self):
        page = self.site / 'event-horizon' / 'privacy-zh-hans.html'
        page.write_text(page.read_text().replace('lang="zh-Hans"', 'lang="en"', 1))
        self.assertIn('language does not match route', self.run_script('check.py', succeeds=False))

    def serve_and_verify(self, change_content):
        parent = Path(self.temporary.name) / 'served'
        destination = parent / 'project-hub'
        shutil.copytree(self.site, destination)
        if change_content:
            (destination / 'assets' / 'site.css').write_text('a different deployment')
        handler = functools.partial(QuietHandler, directory=str(parent))
        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                return self.run_script('verify-deployment.py',
                                       f'http://127.0.0.1:{server.server_port}/project-hub/',
                                       '--allow-http', '--attempts', '1', '--timeout', '2',
                                       succeeds=not change_content)
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_all_pages_and_assets_work_under_repository_subpath(self):
        self.assertIn('published pages/assets match', self.serve_and_verify(False))

    def test_deployment_verification_rejects_mismatched_content(self):
        self.assertIn('Published content differs', self.serve_and_verify(True))


if __name__ == '__main__':
    unittest.main()
