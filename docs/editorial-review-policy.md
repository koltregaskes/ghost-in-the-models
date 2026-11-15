# Ghost in the Models editorial review and signed approval

AI drafting and an editorial `yay` are preparation, never Kol's permission.
Kol does not use GitHub. Agents share the koltregaskes account, so a review,
merge, account name or comment marker says nothing about Kol's decision.

The Chief of Staff (the Claude session on the Mini PC) records Kol's own words
from chat or Todoist privately, then signs an exact-byte approval. The signature
proves that the Chief's dedicated key signed, not that Kol spoke. Checking the
words, scope, source and timing is the Chief's responsibility. Do not invent
an approval, quote, date, human identity or original model provenance.

## Record and signature

Keep final HTML in publish-queue/YYYY-MM-DD-slug.html. The record is
approvals/YYYY-MM-DD-slug.json and its detached signature is the same name
with .sig appended. Its exact fields are:

```json
{
  "schema": "gitm-approval-v1",
  "slug": "YYYY-MM-DD-slug",
  "path": "posts/YYYY-MM-DD-slug.html",
  "sha256": "SHA-256 OF THE FINAL RAW HTML BYTES",
  "quote_sha256": "SHA-256 OF THE EXACT PRIVATE QUOTE IN UTF-8",
  "private_evidence": "https://github.com/koltregaskes/rooms-os-hub/issues/NUMBER#issuecomment-NUMBER",
  "signer": "gitm-chief",
  "approved_at": "ACTUAL KOL APPROVAL TIME WITH TIMEZONE",
  "recorded_by": "Claude Chief of Staff / recording session identifier"
}
```

This is a shape example, not a valid approval. Store the full quote and its
original chat/Todoist locator in an existing PRIVATE hub issue comment. The
public record contains only the quote hash and private comment pointer.
Hash the exact agreed quote bytes, with any newline convention documented
privately. Public hashes of short predictable phrases can be guessed by
dictionary attack; they do not make a quote confidential. The pointer exposes
an issue/comment identifier, though reading the comment requires private access.
Do not put the quote, credentials or personal context in the public record.
The strict schema rejects extra fields, including a plaintext quote.

Serialise the record as UTF-8, LF, no BOM, and sign its exact bytes with the
namespace gitm-approval. The article path always names its eventual posts/
destination; only the matching publish-queue/ staging path is an alias. An edit
to the HTML, path, slug, quote hash, time or recording agent invalidates the
record/signature. approved_at is required in every mode. Rebuild before approval.
Final signatures must cover the COMBINED bytes after PR #48's privacy footers
and PR #50's corrections. Never sign an earlier version and then add a footer.

## One-time setup: Kol and the Chief, not drafting agents

No real key or valid signer is supplied by this patch. The placeholder and
missing external pins deliberately block publishing until setup is complete.

1. Kol authorises the signing boundary through the Chief in chat. Use a Chief-only
   OS identity or signing device that drafting agents cannot use. A key merely
   stored outside Git, or in an ssh-agent shared by the same Windows user, does
   NOT isolate it from other processes with that user's access. Kol handles any
   required Windows/account/security changes separately. No such changes occur
   in this patch. Do not use a Drive/NAS/synchronised folder for the private key.
2. In that isolated Chief session, click Start, type PowerShell, and open Windows
   PowerShell. Choose a dedicated local private-key path outside every repo.
   Run `ssh-keygen -t ed25519 -f <CHIEF-ONLY-PRIVATE-KEY-PATH> -C gitm-chief`.
   Kol enters a passphrase at the prompt. Never put a passphrase in a command,
   log, environment variable or repository, and never let an agent read it.
   Never use an existing personal/login key for this role. A signing tool uses
   the protected key; agents must not open, print, copy or inspect its contents.
3. Open ONLY the newly created .pub file in Notepad. Copy its public algorithm
   and Base64 fields. Replace the placeholder in approvals/allowed_signers with
   `gitm-chief ssh-ed25519 BASE64_PUBLIC_KEY`, followed by one LF newline. Do not
   copy the private file. The Chief commits the public list through the existing
   agent workflow; Kol is not asked to visit, review or merge on GitHub.
4. In the isolated session, calculate SHA-256 of the RAW allowed_signers file
   (`Get-FileHash -Algorithm SHA256 approvals/allowed_signers`). Keep the
   lowercase digest as the bootstrap pin. Confirm that the committed blob and
   local bytes match. .gitattributes disables newline conversion for article,
   approval and signature bytes. The bootstrap list must be in committed history.
5. Through the Chief's existing authorised GitHub browser/session, open this
   repository, click Settings, Secrets and variables, Actions, then Variables.
   Click New repository variable. Name it GITM_APPROVAL_ROOT_SHA256 and paste
   the independently calculated public digest. Save it. These are PUBLIC pins,
   not secrets. This settings action needs Kol's separate authorisation and
   must be unavailable to drafting agents' credentials, even though their
   displayed GitHub account name is the same. Do not sign in as Kol.
6. In the same Variables screen create GITM_APPROVAL_VERIFIER_COMMIT containing
   the full 40-character commit of this reviewed verifier implementation (or a
   reviewed integrated descendant). Confirm the pinned code is present on the
   remote before enabling workflows. Do not point it at a mutable branch name.
   A later verifier update needs its own Chief/Kol-approved settings change.
7. Run the throwaway-key tests and an existing Actions check using the configured
   PUBLIC pins. Confirm the log reports actual verified counts, then prove one
   signed article end to end before queuing a batch. This patch does not claim
   setup, a real signature, a successful job or a public readback has happened.

The pins and the workflow/deployment entrypoint are part of the external trust
boundary. Restrict drafting credentials to content/PR work, not Actions variable
administration, trusted workflow changes, key access or deploy-environment
control. Enforce the pinned gate through the existing protected workflow or
deployment environment before relying on it. Repository code cannot stop an
actor who can rewrite/bypass the workflow, change its external pins or deploy
directly. The shared GitHub account name is never an identity guarantee.

## Recording an actual decision

1. The Chief presents the final combined essay to Kol through chat or Todoist.
   Preserve the exact HTML version; do not ask Kol to use GitHub.
2. After Kol's own explicit words arrive, the Chief stores the full quote and
   source locator in an existing private hub issue comment. Record its actual
   approval time. Compute the HTML hash and quote hash; write the public JSON
   above without the full quote. Do not log or publish the private quote.
3. In the isolated signing session run
   `ssh-keygen -Y sign -n gitm-approval -f <CHIEF-ONLY-PRIVATE-KEY-PATH> approvals/<slug>.json`.
   It creates approvals/<slug>.json.sig. Key unlocking/signing must remain
   inaccessible to drafting sessions. Never expose the key or passphrase to them.
4. The Chief checks with `ssh-keygen -Y verify -f approvals/allowed_signers
   -I gitm-chief -n gitm-approval -s approvals/<slug>.json.sig`, providing the
   exact JSON bytes on stdin. Use a binary-safe command runner, not Windows
   PowerShell 5.1 Get-Content piping (which can change encoding/newlines).
   The Python gate performs this safely with subprocess input=raw_bytes.
5. Commit only the article, public JSON and detached signature. No real private
   key, full quote or private export goes into this repository. The Chief/agent
   may merge content; the merge is not the approval evidence.

## Key rotation

Never overwrite the external initial root pin as an ordinary rotation. Keep the
initial public signer blob and the entire rotation chain in Git history.
Prepare the new allowed_signers bytes and a contiguous record named
approvals/rotations/000001.json (then 000002, etc.) with exactly schema
gitm-signer-rotation-v1, sequence, from_sha256, to_sha256, signer gitm-chief,
approved_at with timezone, and recorded_by. from/to hash the entire old/new
PUBLIC signer files. Sign the record with the EXISTING key, namespace
gitm-approval-rotation, producing .json.sig. Commit the list and rotation together.
The new key cannot authorise itself. First-parent signer history must match the
retained signed chain, so deleting rotations or reverting to an old list fails.
Keep older public keys in the new list while their article signatures must
remain valid, or reissue those records through the Chief before retiring them.
Compromise/lost-key recovery needs a separately authorised external rebootstrap;
there is no unsigned reset flag in the gate.

## Publication and the known hosting limit

Both Actions paths use the same allowlisted artifact policy as PR #48. The
pinned verifier checks the essay bytes INSIDE _site, then the upload step uses
that SAME _site directory. No article generation runs between check and upload.
Unknown root HTML, drafts, queue, scripts, config and approvals are excluded.
The trusted verifier is checked out at the externally pinned commit; candidate
code is not used to authenticate its own proposed keys or signatures.

Repository tokens have contents:read. The scheduled job prepares a verified
candidate artifact only; it cannot push a commit or merge. The Chief's existing
agent workflow must commit the exact candidate essay/derived bytes and the
queue move, then the normal Pages workflow verifies the built artifact again.
Until that commit, repeated schedules can prepare the same queue entry. A
prepared artifact is not a publication or a delivery receipt. Deployment jobs
alone retain pages:write and id-token:write, which Pages needs; no job has
contents:write or pull-requests permissions.

The explicit legacy exception is exactly the 43 unchanged essay files and raw
hashes at a478d8c79dfe335b27e1faed3fe68166989640e5, plus one separately recognised
unchanged redirect. Renames, additions and byte changes need a signed record;
the archive is not retrospectively approved. Silent legacy removal is refused.
The direct PowerShell publisher always stops before -Force can do anything.

**Verified Pages setting: legacy, main:/.** This route publishes from the main
branch independently of Actions. Neither this signature gate nor PR #48's
Actions allowlist protects that LIVE route. Keep unapproved integrated content
off main. Kol must separately approve switching to an enforced deployment
source, and the existing owner must verify the actual setting and public
artifact afterwards. This patch changes no Pages, account, DNS or security
settings and supplies no launch/publication approval.
