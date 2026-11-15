"""Real OpenSSH attacks; all private keys are throwaway temporary fixtures."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from approval import approved_record, is_legacy, legacy_hashes, verify_public, BASELINE
from approval_trust import ApprovalError, digest, trusted_signers
from approval_test_support import Fixture, command
from public_artifact import allowed, build

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('publisher',Path(__file__).with_name('publish-approved.py'))
publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)


class SignedApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='gitm-test-only-');self.addCleanup(self.tmp.cleanup)
        self.f=Fixture(Path(self.tmp.name));self.root=self.f.root
        self.article=self.root/'publish-queue/2026-11-15-test.html'
        self.article.write_bytes(b'<html data-voice="grok"><meta name="referrer"><meta http-equiv="Content-Security-Policy"><p>Draft</p></html>\n')

    def approve(self):return self.f.record(self.article)
    def check(self):return approved_record(self.article,self.root,trusted_signers(self.root,self.f.pin))
    def edit_record(self,field,value,resign=False):
        path=self.approve();record=json.loads(path.read_text());record[field]=value;self.f.write(path,record)
        if resign:self.f.sign(path)

    def rotate(self,bad_key=False,namespace='gitm-approval-rotation'):
        new=self.f.signer_bytes(self.f.other)
        record=dict(schema='gitm-signer-rotation-v1',sequence=1,from_sha256=self.f.pin,to_sha256=digest(new),signer='gitm-chief',approved_at='2026-11-15T12:00:00Z',recorded_by='Claude Chief / synthetic rotation')
        path=self.root/'approvals/rotations/000001.json';self.f.write(path,record)
        self.f.sign(path,key=self.f.other if bad_key else self.f.key,namespace=namespace)
        (self.root/'approvals/allowed_signers').write_bytes(new);self.f.commit()
        return new

    def test_valid_record(self):
        self.approve();self.assertEqual(self.check()['signer'],'gitm-chief')
    def test_missing_record(self):
        with self.assertRaises(ApprovalError):self.check()
    def test_missing_signature(self):
        path=self.approve();path.with_suffix('.json.sig').rename(path.with_suffix('.held-signature'))
        with self.assertRaises(ApprovalError):self.check()
    def test_one_byte_change(self):
        self.approve();self.article.write_bytes(self.article.read_bytes()+b' ')
        with self.assertRaises(ApprovalError):self.check()
    def test_wrong_key(self):
        self.f.sign(self.approve(),key=self.f.other)
        with self.assertRaises(ApprovalError):self.check()
    def test_wrong_namespace(self):
        self.f.sign(self.approve(),namespace='not-gitm-approval')
        with self.assertRaises(ApprovalError):self.check()
    def test_tampered_quote_hash(self):
        self.edit_record('quote_sha256','0'*64)
        with self.assertRaises(ApprovalError):self.check()
    def test_unknown_signer(self):
        self.edit_record('signer','drafting-agent',resign=True)
        with self.assertRaises(ApprovalError):self.check()
    def test_path_reuse(self):
        path=self.approve();other=self.article.with_name('2026-11-15-renamed.html');other.write_bytes(self.article.read_bytes())
        target=path.with_name(other.stem+'.json');shutil.copyfile(path,target);shutil.copyfile(path.with_suffix('.json.sig'),target.with_suffix('.json.sig'))
        with self.assertRaises(ApprovalError):approved_record(other,self.root,trusted_signers(self.root,self.f.pin))
    def test_tampered_path(self):
        self.edit_record('path','posts/2026-11-15-other.html')
        with self.assertRaises(ApprovalError):self.check()
    def test_plaintext_quote_field_rejected(self):
        self.edit_record('quote','Synthetic text only',resign=True)
        with self.assertRaises(ApprovalError):self.check()
    def test_missing_approved_at_rejected(self):
        path=self.approve();record=json.loads(path.read_text());record.pop('approved_at');self.f.write(path,record);self.f.sign(path)
        with self.assertRaises(ApprovalError):self.check()
    def test_unconfigured_external_root(self):
        with self.assertRaises(ApprovalError):trusted_signers(self.root,'')
    def test_unknown_external_root(self):
        with self.assertRaises(ApprovalError):trusted_signers(self.root,'0'*64)
    def test_signer_swap_without_rotation(self):
        (self.root/'approvals/allowed_signers').write_bytes(self.f.signer_bytes(self.f.other));self.f.commit()
        with self.assertRaises(ApprovalError):trusted_signers(self.root,self.f.pin)
    def test_valid_old_key_rotation(self):
        new=self.rotate();self.assertEqual(trusted_signers(self.root,self.f.pin),new)
        path=self.approve();self.f.sign(path,key=self.f.other);self.assertEqual(self.check()['signer'],'gitm-chief')
    def test_new_key_cannot_authorise_itself(self):
        self.rotate(bad_key=True)
        with self.assertRaises(ApprovalError):trusted_signers(self.root,self.f.pin)
    def test_wrong_rotation_namespace(self):
        self.rotate(namespace='gitm-approval')
        with self.assertRaises(ApprovalError):trusted_signers(self.root,self.f.pin)
    def test_rollback_to_old_key_rejected(self):
        self.rotate();(self.root/'approvals/rotations').rename(self.root/'held-rotations')
        (self.root/'approvals/allowed_signers').write_bytes(self.f.signers);self.f.commit()
        with self.assertRaises(ApprovalError):trusted_signers(self.root,self.f.pin)
    def test_missing_pin_cannot_apply(self):
        with self.assertRaises(SystemExit):publisher.main(['--apply'])
    def test_publish_preserves_bytes(self):
        self.approve();original=self.article.read_bytes();now=datetime.fromisoformat('2026-11-15T12:00:00+00:00')
        with patch.object(publisher,'london_now',lambda value=None:value):
            result=publisher.publish_one(self.root,now,apply=True,skip_rebuild=True,signers=trusted_signers(self.root,self.f.pin))
        self.assertEqual((self.root/result).read_bytes(),original);self.assertFalse(self.article.exists())
    def test_edit_during_move_fails_and_restores_queue(self):
        self.approve();move=publisher.shutil.move
        def intercepted(source,destination):
            result=move(source,destination)
            if Path(destination).parent.name=='posts':Path(destination).write_bytes(Path(destination).read_bytes()+b' ')
            return result
        now=datetime.fromisoformat('2026-11-15T12:00:00+00:00')
        with patch.object(publisher,'london_now',lambda value=None:value),patch.object(publisher.shutil,'move',side_effect=intercepted):
            with self.assertRaises(ApprovalError):publisher.publish_one(self.root,now,apply=True,skip_rebuild=True,signers=trusted_signers(self.root,self.f.pin))
        self.assertTrue(self.article.exists());self.assertFalse((self.root/'posts'/self.article.name).exists())


class LegacyAndBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.essays,cls.redirects=legacy_hashes(ROOT)
    def test_43_legacy_essays_unchanged_versus_changed(self):
        self.assertEqual(len(self.essays),43);self.assertEqual(len(self.redirects),1)
        name=next(iter(self.essays));raw=command('git','show',BASELINE+':'+name,cwd=ROOT)
        self.assertTrue(is_legacy(name,raw,self.essays));self.assertFalse(is_legacy(name,raw+b' ',self.essays))
        self.assertFalse(is_legacy('posts/2026-11-15-copied.html',raw,self.essays))
    def test_changed_legacy_without_record_rejected(self):
        name=next(iter(self.essays));raw=command('git','show',BASELINE+':'+name,cwd=ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'posts').mkdir();(root/name).write_bytes(raw+b' ')
            with patch('approval.legacy_hashes',return_value=(self.essays,{})):
                with self.assertRaises(ApprovalError):verify_public(root,b'not used without a record')
    def test_force_stops_before_any_repository_operation(self):
        source=(ROOT/'scripts/publish-draft.ps1').read_text(encoding='utf-8')
        self.assertTrue(source.splitlines()[1].startswith("throw 'Direct publication is disabled"))
        if not shutil.which('powershell'):
            self.skipTest('Windows-only runtime; unconditional PowerShell throw verified statically')
        result=subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'scripts/publish-draft.ps1'),'-Force'],capture_output=True,text=True)
        if 'running scripts is disabled' in result.stderr or 'UnauthorizedAccess' in result.stderr:
            self.skipTest('Windows execution policy blocks the runtime test; leading unconditional throw verified statically')
        self.assertNotEqual(result.returncode,0);self.assertIn('Direct publication is disabled',result.stdout+result.stderr)
    def test_artifact_excludes_root_draft_and_checks_actual_post_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);source=folder/'source';source.mkdir()
            (source/'config').mkdir();(source/'config/contact.json').write_text('{"address":null}')
            (source/'assets').mkdir();(source/'posts').mkdir();(source/'voice').mkdir()
            (source/'index.html').write_text('<p>Public shell</p>')
            (source/'unapproved-draft.html').write_text('<p>Must not ship</p>')
            name=next(iter(self.essays));raw=command('git','show',BASELINE+':'+name,cwd=ROOT)
            (source/name).write_bytes(raw)
            artifact=folder/'artifact';build(source,artifact)
            self.assertFalse((artifact/'unapproved-draft.html').exists())
            self.assertFalse(allowed('unapproved-draft.html'))
            # Source remains unchanged; rejection must be based on artifact bytes.
            (artifact/name).write_bytes(raw+b' ')
            with patch('approval.legacy_hashes',return_value=({name:self.essays[name]},{})):
                with self.assertRaises(ApprovalError):verify_public(source,b'unused without record',artifact=artifact)


if __name__=='__main__':unittest.main()
