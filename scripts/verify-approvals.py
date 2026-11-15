"""Read-only signature gate. Safe to execute from a separately pinned checkout."""
from pathlib import Path
import argparse
import sys

# Also supports python -I: only this verifier's own pinned module directory is
# added, never the candidate checkout or its scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from approval import approved_record, verify_public
from approval_trust import ApprovalError, trusted_signers
from public_artifact import allowed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--trust-root-sha256", required=True)
    parser.add_argument("--mode", choices=["public", "queue", "all"], default="all")
    parser.add_argument("--artifact", type=Path, help="Verify essay bytes INSIDE this exact allowlisted upload directory")
    args = parser.parse_args()
    root = args.root.resolve()
    signers = trusted_signers(root, args.trust_root_sha256)
    artifact = args.artifact.resolve() if args.artifact else None
    if artifact:
        files = [p for p in artifact.rglob('*') if p.is_file()]
        if not files:
            raise ApprovalError("Upload artifact is empty or missing")
        for path in files:
            if not allowed(path.relative_to(artifact).as_posix()) or path.is_symlink():
                raise ApprovalError("Upload artifact contains a file outside the public allowlist")
    if args.mode in {"public", "all"}:
        legacy, signed = verify_public(root, signers, artifact=artifact)
        print(f"Verified public essays: {legacy} unchanged legacy, {signed} signed; baseline has exactly 43 essays.")
    if args.mode in {"queue", "all"}:
        queued = list((root / "publish-queue").rglob("*.html"))
        for article in queued:
            approved_record(article, root, signers)
        print(f"Verified {len(queued)} signed queued article(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ApprovalError, TypeError, KeyError) as exc:
        print(f"APPROVAL REJECTED: {exc}", file=sys.stderr)
        raise SystemExit(1)
