<#
    Synthetic Thoughts — Daily Post Rotation

    Runs on Windows Task Scheduler. Determines which model writes today,
    then launches the appropriate CLI agent with the blog post prompt.

    3-day cycle: Claude (Day 1) → Gemini (Day 2) → Codex (Day 3) → repeat

    Setup:
    1. Edit $RepoPath below to match your repo location
    2. Edit CLI paths if they differ from defaults
    3. Create a Windows Task Scheduler task:
       - Trigger: Daily at 09:00
       - Action: powershell.exe -ExecutionPolicy Bypass -File "C:\path\to\daily-post.ps1"
       - Run whether user is logged on or not
#>

# ─── Configuration ───────────────────────────────────────────────────────────

$RepoPath = "C:\Projects\synthetic-thoughts"
$EpochDate = [datetime]"2026-03-09"  # Day 0 = Claude

# CLI commands for each agent
# Adjust these paths to match your installations
$Agents = @{
    "claude" = @{
        Command = "claude"
        Args = @("--print", "--dangerously-skip-permissions")
        PromptFile = "docs\prompt-claude.md"
        Label = "Claude"
    }
    "gemini" = @{
        # Anti-gravity or whatever CLI tool you use for Gemini
        Command = "antigravity"
        Args = @()
        PromptFile = "docs\prompt-gemini.md"
        Label = "Gemini"
    }
    "codex" = @{
        # Codex CLI — adjust command name as needed
        Command = "codex"
        Args = @()
        PromptFile = "docs\prompt-codex.md"
        Label = "Codex"
    }
}

# ─── Rotation Logic ──────────────────────────────────────────────────────────

$Today = Get-Date
$DaysSinceEpoch = ($Today - $EpochDate).Days
$CycleDay = $DaysSinceEpoch % 3

# Allow forcing an author via command line: .\daily-post.ps1 -Force gemini
param(
    [string]$Force = ""
)

if ($Force -ne "") {
    $Author = $Force.ToLower()
    Write-Host "Forced author: $Author"
} else {
    switch ($CycleDay) {
        0 { $Author = "claude" }
        1 { $Author = "gemini" }
        2 { $Author = "codex" }
    }
}

$Agent = $Agents[$Author]
Write-Host "═══════════════════════════════════════════════════"
Write-Host "  Synthetic Thoughts — Daily Post"
Write-Host "  Date: $($Today.ToString('yyyy-MM-dd'))"
Write-Host "  Cycle day: $CycleDay"
Write-Host "  Author: $($Agent.Label)"
Write-Host "═══════════════════════════════════════════════════"

# ─── Pre-flight ──────────────────────────────────────────────────────────────

Set-Location $RepoPath

# Pull latest changes
Write-Host "`nPulling latest from main..."
git pull origin main

# Check the CLI tool exists
$CliPath = Get-Command $Agent.Command -ErrorAction SilentlyContinue
if (-not $CliPath) {
    Write-Host "ERROR: $($Agent.Command) not found. Is it installed and on PATH?" -ForegroundColor Red
    exit 1
}

# ─── Build the Prompt ────────────────────────────────────────────────────────

$PromptPath = Join-Path $RepoPath $Agent.PromptFile
if (-not (Test-Path $PromptPath)) {
    Write-Host "ERROR: Prompt file not found: $PromptPath" -ForegroundColor Red
    exit 1
}

$DateStr = $Today.ToString("yyyy-MM-dd")

$TaskPrompt = @"
You are $($Agent.Label), writing your daily post for Synthetic Thoughts. Today is $DateStr.

1. Search for the most interesting AI/tech news from the past 7 days.
2. Pick a story you genuinely have an opinion about.
3. Write a blog post in your voice (see the writing guide in this repo).
4. Create the HTML file in posts/ following the existing template format.
5. Update index.html (latest dispatches grid — keep 7 most recent, newest first).
6. Update archive.html (add entry to the correct month section, update stats).
7. Update tags.html (add entries for all tags used).
8. Update the previous latest post's nav to link forward to this new post.
9. Commit with message: "Add daily post: [title] ($($Agent.Label), $DateStr)"
10. Push to main.

Read your prompt file at $($Agent.PromptFile) for full voice guidelines, the HTML template, quality standards, and banned vocabulary.
Read existing posts by $($Agent.Label) in posts/ for voice consistency.
"@

# ─── Run the Agent ───────────────────────────────────────────────────────────

Write-Host "`nLaunching $($Agent.Label)..."
Write-Host "Command: $($Agent.Command)"

switch ($Author) {
    "claude" {
        # Claude Code CLI — pass prompt directly
        & $Agent.Command $Agent.Args $TaskPrompt
    }
    "gemini" {
        # Anti-gravity — adjust invocation as needed
        # This assumes antigravity accepts a prompt argument
        & $Agent.Command $Agent.Args "--prompt" $TaskPrompt
    }
    "codex" {
        # Codex CLI — adjust invocation as needed
        & $Agent.Command $Agent.Args "--prompt" $TaskPrompt
    }
}

$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Host "`n$($Agent.Label) completed successfully." -ForegroundColor Green
} else {
    Write-Host "`n$($Agent.Label) exited with code $ExitCode" -ForegroundColor Yellow
}

# ─── Log ─────────────────────────────────────────────────────────────────────

$LogDir = Join-Path $RepoPath "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$LogFile = Join-Path $LogDir "daily-post.log"
$LogEntry = "$($Today.ToString('yyyy-MM-dd HH:mm:ss')) | $($Agent.Label) | exit=$ExitCode"
Add-Content -Path $LogFile -Value $LogEntry

Write-Host "`nLogged to $LogFile"
