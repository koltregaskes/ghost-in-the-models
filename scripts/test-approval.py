"""Offline adversarial tests for the exact-byte gate; no clock/database needed."""
import hashlib
import json
import tempfile
import unittest
import importlib.util
from datetime import datetime
from unittest.mock import patch
from pathlib import Path
from approval import approved_record

spec = importlib.util.spec_from_file_location('publisher', Path(__file__).with_name('publish-approved.py'))
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'publish-queue').mkdir()
        (self.root / 'approvals').mkdir()
        self.article = self.root / 'publish-queue/2026-11-15-test.html'
        self.article.write_bytes(b'<p>AI draft</p>\n')
        self.manifest = self.root / 'approvals/2026-11-15-test.json'

    def approve(self):
        record = dict(article='publish-queue/' + self.article.name,
                      sha256=hashlib.sha256(self.article.read_bytes()).hexdigest(),
                      approver='koltregaskes', approved_at='2026-11-15T12:00:00Z')
        self.manifest.write_text(json.dumps(record), encoding='utf-8')
        return {self.manifest.relative_to(self.root).as_posix(): hashlib.sha256(self.manifest.read_bytes()).hexdigest()}

    def test_missing(self):
        with self.assertRaises(ValueError): approved_record(self.article, self.root)

    def test_forged_comment(self):
        self.article.write_bytes(b'<!-- gitm-approved-by: kol -->')
        with self.assertRaises(ValueError): approved_record(self.article, self.root)

    def test_hash_mismatch(self):
        receipts = self.approve()
        self.article.write_bytes(b'changed')
        with self.assertRaises(ValueError): approved_record(self.article, self.root, receipts)

    def test_edited_article_one_byte(self):
        receipts = self.approve()
        self.article.write_bytes(self.article.read_bytes() + b' ')
        with self.assertRaises(ValueError): approved_record(self.article, self.root, receipts)

    def test_forged_manifest_no_receipt(self):
        self.approve()
        with self.assertRaises(ValueError): approved_record(self.article, self.root, {})

    def test_edited_manifest(self):
        receipts = self.approve()
        self.manifest.write_bytes(self.manifest.read_bytes() + b' ')
        with self.assertRaises(ValueError): approved_record(self.article, self.root, receipts)

    def test_valid(self):
        receipts = self.approve()
        self.assertEqual(approved_record(self.article, self.root, receipts)['approver'], 'koltregaskes')

    def test_apply_requires_external_receipt(self):
        with self.assertRaisesRegex(SystemExit, 'verified owner-merge receipts'):
            publisher.main(['--apply'])

    def test_publish_preserves_exact_approved_bytes(self):
        original = b'''<html data-voice="grok"><meta name="referrer"><meta http-equiv="Content-Security-Policy"><p>Final reviewed draft</p></html>\n'''
        self.article.write_bytes(original)
        receipts = self.approve()
        now = datetime.fromisoformat('2026-11-15T12:00:00+00:00')
        # The byte gate does not depend on timezone data. Window regressions
        # remain in test-publish-approved.py and need the real London zone.
        with patch.object(publisher, 'london_now', lambda value=None: value):
            result = publisher.publish_one(self.root, now, apply=True, skip_rebuild=True, receipts=receipts)
        self.assertEqual(result, 'posts/' + self.article.name)
        self.assertFalse(self.article.exists())
        self.assertEqual((self.root/result).read_bytes(), original)


if __name__ == '__main__': unittest.main()
