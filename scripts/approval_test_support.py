"""Throwaway signing fixtures ONLY for tests. Never uses a real signing key."""
import json
import subprocess
from pathlib import Path
from approval_trust import digest


def command(*args, cwd=None):
    result = subprocess.run(list(args), cwd=cwd, capture_output=True, check=False, timeout=30)
    if result.returncode:
        raise RuntimeError(f"Test fixture command failed: {args[0]} (exit {result.returncode})")
    return result.stdout


class Fixture:
    def __init__(self, temporary: Path):
        self.root = temporary / "repo"
        self.root.mkdir()
        (self.root / "approvals").mkdir()
        (self.root / "publish-queue").mkdir()
        (self.root / "posts").mkdir()
        self.keys = temporary / "throwaway-keys"
        self.keys.mkdir()
        self.key = self.new_key("chief")
        self.other = self.new_key("other")
        self.signers = self.signer_bytes(self.key)
        (self.root / "approvals/allowed_signers").write_bytes(self.signers)
        command("git", "init", "-b", "main", str(self.root))
        command("git", "config", "user.name", "Throwaway fixture", cwd=self.root)
        command("git", "config", "user.email", "fixture@example.invalid", cwd=self.root)
        self.commit()
        self.pin = digest(self.signers)

    def new_key(self, name):
        key = self.keys / name
        command("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "throwaway-test-only", "-f", str(key))
        return key

    def signer_bytes(self, key):
        public = key.with_suffix(".pub").read_text(encoding="ascii").split()
        return ("gitm-chief " + " ".join(public[:2]) + "\n").encode("ascii")

    def commit(self):
        command("git", "add", "--", "approvals/allowed_signers", cwd=self.root)
        command("git", "commit", "-m", "Public signer fixture", cwd=self.root)

    def record(self, article):
        record = {"schema": "gitm-approval-v1", "slug": article.stem,
                  "path": "posts/" + article.name, "sha256": digest(article.read_bytes()),
                  "quote_sha256": digest(b"Synthetic test approval, not Kol's words"),
                  "private_evidence": "https://github.com/koltregaskes/rooms-os-hub/issues/1#issuecomment-1",
                  "approved_at": "2026-11-15T12:00:00Z", "recorded_by": "Claude Chief of Staff / synthetic fixture",
                  "signer": "gitm-chief"}
        path = self.root / "approvals" / (article.stem + ".json")
        self.write(path, record)
        self.sign(path)
        return path

    def write(self, path, record):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")

    def sign(self, path, *, key=None, namespace="gitm-approval"):
        # Each test signs a fresh path; no key material is printed or committed.
        signature = path.with_suffix(path.suffix + ".sig")
        if signature.exists():
            signature.rename(signature.with_name(signature.name + ".previous"))
        command("ssh-keygen", "-Y", "sign", "-f", str(key or self.key), "-n", namespace, str(path))
