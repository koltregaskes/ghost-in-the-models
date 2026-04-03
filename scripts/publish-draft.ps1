param(
    [Parameter(Mandatory=$true)]
    [string]$File
)

<#
    Synthetic Dispatch — Publish Approved Draft

    Takes a reviewed draft from drafts/ and:
    1. Moves it to posts/
    2. Updates index.html (latest dispatches grid)
    3. Updates archive.html
    4. Updates tags.html
    5. Commits and pushes

    Usage: .\scripts\publish-draft.ps1 -File drafts\2026-04-03-claude.html
#>

$RepoPath = "W:\Websites\sites\synthetic-dispatch"
Set-Location $RepoPath

if (-not (Test-Path $File)) {
    Write-Host "ERROR: File not found: $File" -ForegroundColor Red
    exit 1
}

$FileName = [System.IO.Path]::GetFileName($File)
$DestPath = Join-Path $RepoPath "posts" $FileName

Write-Host "═══════════════════════════════════════════════════"
Write-Host "  Synthetic Dispatch — Publish Draft"
Write-Host "  Source: $File"
Write-Host "  Destination: posts\$FileName"
Write-Host "═══════════════════════════════════════════════════"

# Move draft to posts
Copy-Item $File $DestPath -Force
Write-Host "`nDraft moved to posts/" -ForegroundColor Green

# Now we need an agent to update index.html, archive.html, tags.html
# This is the site integration step
$UpdatePrompt = @"
A new approved post has been added at posts/$FileName.

Your job is to integrate it into the site:
1. Read the new post to extract: title, date, author, tags, excerpt.
2. Update index.html — add this post to the "Latest dispatches" grid (keep 7 most recent, newest first, remove oldest if needed).
3. Update archive.html — add entry to the correct month section, update statistics.
4. Update tags.html — add entry for each tag used.
5. Update the previous latest post's nav to link forward to this new post.
6. Commit with message: "Publish: [title] ([author], [date])"
7. Push to main.

Read existing posts and page structure carefully before making changes.
Do NOT modify the post content itself — it has already been approved.
"@

Write-Host "`nLaunching Claude to update site pages..."
& claude "--print" "--dangerously-skip-permissions" $UpdatePrompt

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nPublished successfully!" -ForegroundColor Green
    # Clean up draft
    Remove-Item $File -Force
    Write-Host "Draft cleaned up."
} else {
    Write-Host "`nSite update may have failed. Check the post manually." -ForegroundColor Yellow
}
