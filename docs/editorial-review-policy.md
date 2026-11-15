# Ghost in the Models Editorial Review Policy

Ghost in the Models uses the estate-wide editorial review system before publication.

## Rule

No draft should go straight from writing to publication without an editorial pass.

## Editor

The website manager acts as the editor.

They must review each draft for:

1. security or sensitive-data leaks
2. context and controversy risks
3. factual accuracy
4. date and chronology accuracy
5. writing quality
6. image suitability

## Verdicts

The editor records one of:

- `yay`
- `nay`
- `needs_images`
- `hold`

## Publication Behaviour

Ghost in the Models does not publish automatically after the editor records `yay`.

That means:

1. the writer creates the draft
2. the editor reviews it
3. if the verdict is `yay`, the draft becomes `approved-ready`
4. `yay` does not create, move, commit, push, deploy, or publish content
5. Kol must explicitly approve the exact draft before the separate publication action runs
6. the explicit action is the approved queue workflow after the reviewed approval PR is merged by Kol
7. if the verdict is `nay`, the draft goes back for changes
8. if the verdict is `hold`, do not publish

## Shared Documents

Use these estate-wide documents for the real process:

- `W:\Websites\shared\website-tools\pipelines\articles\website-manager-editor-packet.md`
- `W:\Websites\shared\website-tools\pipelines\articles\editorial-review-workflow.md`
- `W:\Websites\shared\website-tools\pipelines\articles\editorial-checklist.md`

## Exact-byte publication approval

Prepare final HTML in `publish-queue/YYYY-MM-DD-slug.html`, including its visible
AI author attribution and an accurate statement of editorial responsibility.
Kol makes the final publication decision; AI drafting and an AI review verdict
do not constitute that decision. Do not invent a past approval for archive essays.

In the same PR add `approvals/YYYY-MM-DD-slug.json` with `article` (the queue path),
`sha256` (SHA-256 of the final raw HTML bytes), `approver` (`koltregaskes`) and
`approved_at` (the actual approval time with timezone). Do not fill in Kol's
decision or time on his behalf. The PR needs a non-bot approval review of its
final head and must be merged into main by the repository owner, koltregaskes.
Changing one byte invalidates approval. Rebuild before review, not afterwards.

Actions fetches GitHub merge, review and merged-file metadata. It compares both
the manifest and article to that owner-merged PR, writes a receipt outside the
checkout, and refuses missing/mismatching approval. Comment markers and the old
`-ConfirmedByKol` path cannot authorise publication. The scheduled move preserves
the approved bytes even when rebuilding derived pages.

The deployment check also rejects new or modified public essays without that
evidence. Unchanged archive bytes at a478d8c are a legacy exception, not proof
of human approval. Approval records are retained after a queued file is moved.

This proves reviewed bytes and an owner-account merge, not the identity of the
person using that account, editorial truth, or model provenance. Repository code
cannot defend against an actor allowed to rewrite the workflow or main branch.
Kol must separately approve branch protection, workflow protection and access
restrictions that keep drafting agents away from main, approvals and publishing.
Those settings are not changed by this patch. Legacy branch Pages publishing
would bypass the Actions check; verify the Pages source before relying on it.
