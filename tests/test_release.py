"""Release packaging uses synthetic inputs, neutral metadata and stable bytes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

TOOLS = Path(__file__).resolve().parent.parent / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('release_tools', str(TOOLS / 'package_release.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        for name in release.FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic public file\n', encoding='utf-8')
        (self.root / 'src').mkdir()
        (self.root / 'src/server.py').write_text("VERSION='0.1.0'\n", encoding='utf-8')
        (self.root / 'artifacts').mkdir()
        (self.root / 'artifacts/private.json').write_text('PRIVATE_MARKER', encoding='utf-8')
        (self.root / 'src/.DS_Store').write_bytes(b'PRIVATE_MARKER')
        self.root_patch = mock.patch.object(release, 'ROOT', self.root)
        self.build_patch = mock.patch.object(release, 'build', lambda: self.root / 'codexview')
        self.root_patch.start()
        self.build_patch.start()
    def tearDown(self):
        self.build_patch.stop()
        self.root_patch.stop()
        self.tmp.cleanup()
    def test_reproducible_archives_and_checksums(self):
        artifacts = release.package()
        hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts]
        for path in self.root.rglob('*'):
            if path.is_file() and 'dist' not in path.parts:
                import os
                os.utime(str(path), (1700000000, 1700000000))
        self.assertEqual(hashes, [hashlib.sha256(path.read_bytes()).hexdigest() for path in release.package()])
        with tarfile.open(str(artifacts[1])) as tar:
            for member in tar.getmembers():
                self.assertEqual((member.uid, member.gid, member.mtime, member.uname, member.gname), (0, 0, 0, '', ''))
                self.assertNotIn(b'PRIVATE_MARKER', tar.extractfile(member).read())
        with zipfile.ZipFile(str(artifacts[2])) as archive:
            for member in archive.infolist():
                self.assertEqual(member.date_time, release.ZIP_EPOCH)
                self.assertNotIn(b'PRIVATE_MARKER', archive.read(member))
        for line in (self.root / 'dist/SHA256SUMS').read_text().splitlines():
            digest, name = line.split('  ')
            self.assertEqual(hashlib.sha256((self.root / 'dist' / name).read_bytes()).hexdigest(), digest)
        self.assertTrue((self.root / 'dist/codexview-0.1.0-source/LICENSE').exists())
    def test_redirected_source_is_rejected(self):
        path = self.root / 'src/redirect.py'
        path.symlink_to(self.root / 'artifacts/private.json')
        with self.assertRaises(ValueError):
            release.package()
