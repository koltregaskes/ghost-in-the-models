"""Byte approval contract. Identity is checked separately against GitHub metadata."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

OWNER = "koltregaskes"


def approved_record(article: Path, root: Path, receipts: dict | None = None) -> dict:
    manifest = root / "approvals" / (article.stem + ".json")
    if not manifest.is_file() or manifest.is_symlink() or article.is_symlink():
        raise ValueError(f"Missing regular approval record for {article.name}")
    raw = manifest.read_bytes()
    record = json.loads(raw)
    expected = "publish-queue/" + article.name
    if record.get("article") != expected or record.get("approver") != OWNER:
        raise ValueError(f"Invalid approval identity/path for {article.name}")
    timestamp = datetime.fromisoformat(record["approved_at"].replace("Z", "+00:00"))
    if timestamp.utcoffset() is None or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
        raise ValueError(f"Invalid approval time/hash for {article.name}")
    if hashlib.sha256(article.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError(f"Approved bytes changed: {article.name}")
    if receipts is not None:
        # The workflow creates this outside the checkout after querying GitHub.
        # A repository-authored receipt is never used by the workflow.
        digest = hashlib.sha256(raw).hexdigest()
        if receipts.get(manifest.relative_to(root).as_posix()) != digest:
            raise ValueError(f"Missing verified owner-merge receipt for {article.name}")
    return record
