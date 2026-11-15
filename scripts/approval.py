"""Exact-byte Chief signatures, with the explicit 43-essay legacy exception."""
import re
from pathlib import Path
from urllib.parse import urlsplit
from approval_trust import (ApprovalError, APPROVAL_NAMESPACE, HASH, digest,
                            document, git, metadata, regular_bytes, verify_signature)

BASELINE = "a478d8c79dfe335b27e1faed3fe68166989640e5"
ARTICLE_NAME = re.compile(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.html")
FIELDS = {"schema", "slug", "path", "sha256", "quote_sha256", "private_evidence",
          "signer", "approved_at", "recorded_by"}


def approved_record(article: Path, root: Path, signers: bytes, *, content: bytes | None = None) -> dict:
    relative = article.relative_to(root).as_posix()
    if not ARTICLE_NAME.fullmatch(article.name) or relative not in {"posts/" + article.name, "publish-queue/" + article.name}:
        raise ApprovalError("Article must have its exact canonical post/queue path")
    manifest = root / "approvals" / (article.stem + ".json")
    raw = regular_bytes(manifest, root)
    record = document(raw, FIELDS)
    metadata(record)
    if record["schema"] != "gitm-approval-v1" or record["slug"] != article.stem or record["path"] != "posts/" + article.name:
        raise ApprovalError("Approval slug/path reuse is forbidden")
    if not isinstance(record["sha256"], str) or not HASH.fullmatch(record["sha256"]) or not isinstance(record["quote_sha256"], str) or not HASH.fullmatch(record["quote_sha256"]):
        raise ApprovalError("Article and private-quote SHA-256 hashes are required")
    # A private hub issue comment is a locator, not an authentication signal.
    pointer = urlsplit(record["private_evidence"])
    if pointer.scheme != "https" or pointer.netloc != "github.com" or not re.fullmatch(r"/koltregaskes/rooms-os-hub/issues/\d+", pointer.path) or not re.fullmatch(r"issuecomment-\d+", pointer.fragment) or pointer.query:
        raise ApprovalError("Private evidence must point to a private hub issue comment")
    article_bytes = regular_bytes(article, root) if content is None else content
    if digest(article_bytes) != record["sha256"]:
        raise ApprovalError("Article bytes differ from the signed approval")
    verify_signature(raw, regular_bytes(manifest.with_suffix(".json.sig"), root), signers, APPROVAL_NAMESPACE)
    return record


def legacy_hashes(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    essays, redirects = {}, {}
    names = git(root, "ls-tree", "-r", "--name-only", BASELINE, "--", "posts/").decode("utf-8").splitlines()
    for name in names:
        if not name.endswith(".html"):
            continue
        raw = git(root, "show", f"{BASELINE}:{name}")
        target = redirects if re.search(br'http-equiv=["\']refresh["\']', raw, re.I) else essays
        target[name] = digest(raw)
    if len(essays) != 43 or len(redirects) != 1:
        raise ApprovalError("The immutable 43-essay baseline is unavailable or unexpected")
    return essays, redirects


def is_legacy(name: str, content: bytes, hashes: dict[str, str]) -> bool:
    return name in hashes and digest(content) == hashes[name]


def verify_public(root: Path, signers: bytes, *, artifact: Path | None = None) -> tuple[int, int]:
    essays, redirects = legacy_hashes(root)
    article_root = artifact or root
    legacy = signed = 0
    if any(not (article_root / name).is_file() for name in essays):
        raise ApprovalError("A legacy essay is missing; silent archive removal is not approved")
    for article in sorted((article_root / "posts").rglob("*.html")):
        name = article.relative_to(article_root).as_posix()
        raw = regular_bytes(article, article_root)
        if is_legacy(name, raw, essays):
            legacy += 1
        elif is_legacy(name, raw, redirects):
            continue  # One unchanged redirect is not a 44th legacy essay.
        else:
            approved_record(root / name, root, signers, content=raw)
            signed += 1
    return legacy, signed
