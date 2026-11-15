"""SSH approval verification. Never reads or signs with a private key.

An external public digest anchors allowed_signers; rotations are authorised by
the previous list, never by the proposed replacement. Git stores public history.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

PRINCIPAL = "gitm-chief"
APPROVAL_NAMESPACE = "gitm-approval"
ROTATION_NAMESPACE = "gitm-approval-rotation"
SIGNERS = "approvals/allowed_signers"
HASH = re.compile(r"[0-9a-f]{64}")


class ApprovalError(ValueError):
    pass


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def regular_bytes(path: Path, root: Path) -> bytes:
    try:
        relative = path.relative_to(root)
        if any((root / parent).is_symlink() for parent in [relative, *relative.parents]):
            raise ApprovalError("Approval paths must not be symlinks")
        if root.resolve() not in path.resolve().parents:
            raise ApprovalError("Approval path escaped the checkout")
        return path.read_bytes()
    except (OSError, ValueError) as exc:
        raise ApprovalError(f"Missing or unsafe approval input: {path.name}") from exc


def document(raw: bytes, fields: set[str]) -> dict:
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ApprovalError("Duplicate JSON field")
            obj[key] = value
        return obj
    try:
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
            raise ApprovalError("Records must be UTF-8 LF without a BOM")
        record = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
        if not isinstance(record, dict) or set(record) != fields:
            raise ApprovalError("Unexpected record fields (never put the quote here)")
        return record
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ApprovalError("Invalid UTF-8 JSON record") from exc


def metadata(record: dict):
    if record.get("signer") != PRINCIPAL:
        raise ApprovalError("Unknown signer identity")
    if not isinstance(record.get("recorded_by"), str) or not record["recorded_by"].strip():
        raise ApprovalError("Recording agent is required")
    try:
        stamp = datetime.fromisoformat(record["approved_at"].replace("Z", "+00:00"))
        if stamp.utcoffset() is None:
            raise ValueError("Timezone required")
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise ApprovalError("Approval time must include a timezone") from exc


def validate_signers(raw: bytes):
    # Only dedicated Ed25519 public keys and the one Chief identity are accepted.
    try:
        lines = [s for line in raw.decode("ascii").splitlines() if (s := line.strip()) and not s.startswith("#")]
    except UnicodeError as exc:
        raise ApprovalError("Invalid signer list") from exc
    if not lines or any(not re.fullmatch(r"gitm-chief ssh-ed25519 [A-Za-z0-9+/]+={0,3}", line) for line in lines):
        raise ApprovalError("Chief public signer list is not initialised or has unsupported entries")


def verify_signature(raw: bytes, signature: bytes, signers: bytes, namespace: str):
    validate_signers(signers)
    # Only public verifier input and detached signatures enter this directory.
    # Signing is deliberately absent from production code.
    with tempfile.TemporaryDirectory(prefix="gitm-verify-") as temporary:
        folder = Path(temporary)
        allowed = folder / "allowed_signers"
        detached = folder / "record.sig"
        allowed.write_bytes(signers)
        detached.write_bytes(signature)
        try:
            result = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", PRINCIPAL,
                 "-n", namespace, "-s", str(detached)],
                input=raw, capture_output=True, timeout=20, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ApprovalError("OpenSSH verification unavailable or timed out") from exc
        if result.returncode:
            raise ApprovalError("Invalid Chief signature, signer or namespace")


def git(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, check=False)
    if result.returncode:
        raise ApprovalError("Required public Git history is unavailable; fetch full history")
    return result.stdout


def trusted_signers(root: Path, root_sha256: str) -> bytes:
    if not HASH.fullmatch(root_sha256 or ""):
        raise ApprovalError("External Chief trust-root SHA-256 is not configured")
    current = regular_bytes(root / SIGNERS, root)
    validate_signers(current)
    versions = {digest(current): current}
    # Read only this PUBLIC file from Git history. No key/secret paths are read.
    commits = git(root, "log", "--all", "--format=%H", "--", SIGNERS).decode("ascii").splitlines()
    for commit in commits:
        result = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{SIGNERS}"], capture_output=True)
        if result.returncode == 0:
            versions[digest(result.stdout)] = result.stdout
    if root_sha256 not in versions:
        raise ApprovalError("Pinned initial public signer file is absent from history")
    trusted = versions[root_sha256]
    validate_signers(trusted)
    expected_history = [root_sha256]
    rotation_dir = root / "approvals" / "rotations"
    records = sorted(rotation_dir.glob("*.json")) if rotation_dir.exists() else []
    for number, path in enumerate(records, 1):
        if path.name != f"{number:06d}.json":
            raise ApprovalError("Signer rotations must be contiguous, starting at 000001")
        raw = regular_bytes(path, root)
        record = document(raw, {"schema", "sequence", "from_sha256", "to_sha256", "signer", "approved_at", "recorded_by"})
        metadata(record)
        if record["schema"] != "gitm-signer-rotation-v1" or type(record["sequence"]) is not int or record["sequence"] != number:
            raise ApprovalError("Invalid signer rotation schema/sequence")
        if record["from_sha256"] != digest(trusted) or record["to_sha256"] not in versions or record["to_sha256"] == record["from_sha256"]:
            raise ApprovalError("Signer rotation is disconnected from the trusted key")
        verify_signature(raw, regular_bytes(path.with_suffix(".json.sig"), root), trusted, ROTATION_NAMESPACE)
        trusted = versions[record["to_sha256"]]
        validate_signers(trusted)
        expected_history.append(digest(trusted))
    if digest(trusted) != digest(current):
        raise ApprovalError("Unsigned allowed_signers replacement; old-key rotation required")
    # Reverting to an old signed list must not silently undo a key revocation.
    # The live/PR merge first-parent history must match the retained signed chain.
    history = []
    for commit in git(root, "log", "--first-parent", "--reverse", "--format=%H", "--", SIGNERS).decode("ascii").splitlines():
        result = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{SIGNERS}"], capture_output=True)
        if result.returncode == 0:
            value = digest(result.stdout)
            if not history or history[-1] != value:
                history.append(value)
    if root_sha256 not in history:
        raise ApprovalError("Initial signer bootstrap must be committed in the candidate history")
    history = history[history.index(root_sha256):]
    if digest(current) != history[-1]:
        history.append(digest(current))  # Also catches uncommitted local swaps.
    if history != expected_history:
        raise ApprovalError("Signer history/rollback differs from its old-key-signed rotation chain")
    return trusted
