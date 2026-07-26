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
6. the explicit action is `scripts\publish-draft.ps1 -DraftPath <draft> -ConfirmedByKol`
7. if the verdict is `nay`, the draft goes back for changes
8. if the verdict is `hold`, do not publish

## Shared Documents

Use these estate-wide documents for the real process:

- `W:\Websites\shared\website-tools\pipelines\articles\website-manager-editor-packet.md`
- `W:\Websites\shared\website-tools\pipelines\articles\editorial-review-workflow.md`
- `W:\Websites\shared\website-tools\pipelines\articles\editorial-checklist.md`
