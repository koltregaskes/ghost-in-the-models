param(
    [string]$Force = ""
)

<#
    Synthetic Dispatch — Draft Writer

    Writes a draft article but does NOT publish it.
    Drafts go to drafts/ folder for Kol to review.
    Once approved, run publish-draft.ps1 to move to posts/ and update the site.

    3-day cycle: Claude (Day 1) → Gemini (Day 2) → Codex (Day 3) → repeat
    Scheduled: Daily at 22:00
#>

$RepoPath = "W:\Websites\sites\synthetic-dispatch"
$DraftsDir = Join-Path $RepoPath "drafts"
$EpochDate = [datetime]"2026-03-09"  # Day 0 = Claude

# CLI commands for each agent
$Agents = @{
    "claude" = @{
        Command = "claude"
        Label = "Claude"
        PromptFile = "docs\prompt-claude.md"
    }
    "gemini" = @{
        Command = "gemini"
        Label = "Gemini"
        PromptFile = "docs\prompt-gemini.md"
    }
    "codex" = @{
        Command = "codex.cmd"
        Label = "Codex"
        PromptFile = "docs\prompt-codex.md"
    }
}

# ─── Rotation Logic ───────────────────────────────────────────────

$Today = Get-Date
$DaysSinceEpoch = ($Today - $EpochDate).Days
$CycleDay = $DaysSinceEpoch % 3

if ($Force -ne "") {
    $Author = $Force.ToLower()
} else {
    switch ($CycleDay) {
        0 { $Author = "claude" }
        1 { $Author = "gemini" }
        2 { $Author = "codex" }
    }
}

$Agent = $Agents[$Author]
$DateStr = $Today.ToString("yyyy-MM-dd")

Write-Host "═══════════════════════════════════════════════════"
Write-Host "  Synthetic Dispatch — Draft Writer"
Write-Host "  Date: $DateStr"
Write-Host "  Author: $($Agent.Label)"
Write-Host "  Mode: DRAFT (will not publish)"
Write-Host "═══════════════════════════════════════════════════"

# Ensure drafts directory exists
if (-not (Test-Path $DraftsDir)) { New-Item -ItemType Directory -Path $DraftsDir | Out-Null }

Set-Location $RepoPath
git pull origin main 2>&1

# Check CLI exists
$CliPath = Get-Command $Agent.Command -ErrorAction SilentlyContinue
if (-not $CliPath) {
    Write-Host "ERROR: $($Agent.Command) not found." -ForegroundColor Red
    exit 1
}

# ─── Build the Prompt ─────────────────────────────────────────────

$TaskPrompt = @"
You are $($Agent.Label), writing your daily dispatch for Synthetic Dispatch.
Today is $DateStr.

IMPORTANT: You are writing a DRAFT. Do NOT commit or push. Do NOT modify index.html, archive.html, or tags.html.

Your task:
1. Check the news digests in news-digests/ for recent stories worth writing about.
2. Pick a topic you genuinely have an opinion about — something worth more than a summary.
3. Write a compelling, professional blog post in your voice (see $($Agent.PromptFile)).
4. Save the HTML file to: drafts/$DateStr-$Author.html
5. Follow the exact HTML template format used by existing posts in posts/.
6. The post MUST be at least 800 words of substance.
7. The post MUST have a strong opening hook — no generic introductions.
8. Do NOT commit, push, or modify any files outside of drafts/.

This is a showcase of what AI agents can produce at their best. Every word matters.
Read your voice guidelines at $($Agent.PromptFile) carefully.
Read your previous posts in posts/ for voice consistency.
"@

# ─── Run the Agent ────────────────────────────────────────────────

Write-Host "`nLaunching $($Agent.Label) to write draft..."

switch ($Author) {
    "claude" {
        & $Agent.Command "--print" "--dangerously-skip-permissions" $TaskPrompt
    }
    "gemini" {
        & $Agent.Command $TaskPrompt
    }
    "codex" {
        & codex.cmd exec --dangerously-bypass-approvals-and-sandbox --search -C $RepoPath $TaskPrompt
    }
}

$ExitCode = $LASTEXITCODE

# Check if draft was created
$DraftFile = Join-Path $DraftsDir "$DateStr-$Author.html"
if (Test-Path $DraftFile) {
    Write-Host "`nDraft created: $DraftFile" -ForegroundColor Green
    Write-Host "Review it, then run: .\scripts\publish-draft.ps1 -File $DraftFile"
} else {
    Write-Host "`nWARNING: No draft file found at $DraftFile" -ForegroundColor Yellow
    Write-Host "The agent may have saved it elsewhere. Check drafts/ folder."
}

# ─── Log ──────────────────────────────────────────────────────────

$LogDir = Join-Path $RepoPath "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir "draft-writer.log"
$HasDraft = if (Test-Path $DraftFile) { "draft_created" } else { "no_draft" }
$LogEntry = "$($Today.ToString('yyyy-MM-dd HH:mm:ss')) | $($Agent.Label) | exit=$ExitCode | $HasDraft"
Add-Content -Path $LogFile -Value $LogEntry
