param(
    [string]$Force = ""
)

$ErrorActionPreference = 'Stop'

<#
    Ghost in the Model - Draft Writer

    Writes a draft article but does not publish it.
    Drafts go to drafts/ for review.
#>

$RepoPath = "W:\Websites\sites\ghost-in-the-models"
$DraftsDir = Join-Path $RepoPath "drafts"
$EpochDate = [datetime]"2026-03-09"

$Agents = @{
    "claude" = @{
        Command = "claude"
        Args = @("--print", "--dangerously-skip-permissions")
        Label = "Claude"
        PromptFile = "docs\prompt-claude.md"
    }
    "gemini" = @{
        Command = "antigravity"
        Args = @()
        Label = "Gemini"
        PromptFile = "docs\prompt-gemini.md"
    }
    "codex" = @{
        Command = "codex.cmd"
        Args = @(
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "-C",
            $RepoPath
        )
        Label = "Codex"
        PromptFile = "docs\prompt-codex.md"
    }
}

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
        default { throw "Unexpected cycle day: $CycleDay" }
    }
}

$Agent = $Agents[$Author]
if (-not $Agent) {
    throw "Unknown author '$Author'."
}

$DateStr = $Today.ToString("yyyy-MM-dd")

Write-Host "==================================================="
Write-Host "  Ghost in the Model - Draft Writer"
Write-Host "  Date: $DateStr"
Write-Host "  Author: $($Agent.Label)"
Write-Host "  Mode: DRAFT (will not publish)"
Write-Host "==================================================="

if (-not (Test-Path $DraftsDir)) {
    New-Item -ItemType Directory -Path $DraftsDir | Out-Null
}

Set-Location $RepoPath
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: git pull failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

$CliPath = Get-Command $Agent.Command -ErrorAction SilentlyContinue
if (-not $CliPath) {
    Write-Host "ERROR: $($Agent.Command) not found." -ForegroundColor Red
    exit 1
}

$TaskPrompt = @"
You are $($Agent.Label), writing your daily dispatch for Ghost in the Model.
Today is $DateStr.

IMPORTANT: You are writing a DRAFT. Do NOT commit or push. Do NOT modify index.html, archive.html, or tags.html.

Your task:
1. Check the news digests in news-digests/ for recent stories worth writing about.
2. Pick a topic you genuinely have an opinion about - something worth more than a summary.
3. Write a compelling, professional blog post in your voice (see $($Agent.PromptFile)).
4. Save the HTML file to: drafts/$DateStr-$Author.html
5. Follow the exact HTML template format used by existing posts in posts/.
6. The post must be at least 800 words of substance.
7. The post must have a strong opening hook - no generic introductions.
8. Do NOT commit, push, or modify any files outside of drafts/.

This is a showcase of what AI agents can produce at their best. Every word matters.
Read your voice guidelines at $($Agent.PromptFile) carefully.
Read your previous posts in posts/ for voice consistency.
"@

Write-Host "`nLaunching $($Agent.Label) to write draft..."

switch ($Author) {
    "claude" {
        & $Agent.Command @($Agent.Args + @($TaskPrompt))
    }
    "gemini" {
        & $Agent.Command @($Agent.Args + @("--prompt", $TaskPrompt))
    }
    "codex" {
        & $Agent.Command @($Agent.Args + @($TaskPrompt))
    }
}

$ExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }

$DraftFile = Join-Path $DraftsDir "$DateStr-$Author.html"
if (Test-Path $DraftFile) {
    Write-Host "`nDraft created: $DraftFile" -ForegroundColor Green
    Write-Host "Review it, then run: .\scripts\publish-draft.ps1 -File $DraftFile"
} else {
    Write-Host "`nWARNING: No draft file found at $DraftFile" -ForegroundColor Yellow
    Write-Host "The agent may have saved it elsewhere. Check drafts/ folder."
}

$LogDir = Join-Path $RepoPath "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$LogFile = Join-Path $LogDir "draft-writer.log"
$HasDraft = if (Test-Path $DraftFile) { "draft_created" } else { "no_draft" }
$LogEntry = "$($Today.ToString('yyyy-MM-dd HH:mm:ss')) | $($Agent.Label) | exit=$ExitCode | $HasDraft"
Add-Content -Path $LogFile -Value $LogEntry

exit $ExitCode




