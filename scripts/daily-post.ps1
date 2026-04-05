param(
    [string]$Force = ""
)

$ErrorActionPreference = 'Stop'

<#
    Ghost in the Model - Daily Post Rotation

    Runs on Windows Task Scheduler. Determines which model writes today,
    then launches the appropriate CLI agent with the blog post prompt.

    3-day cycle: Claude (Day 1) -> Gemini (Day 2) -> Codex (Day 3) -> repeat
#>

$RepoPath = "W:\Websites\sites\ghost-in-the-models"
$EpochDate = [datetime]"2026-03-09"

$Agents = @{
    "claude" = @{
        Command = "claude"
        Args = @("--print", "--dangerously-skip-permissions")
        PromptFile = "docs\prompt-claude.md"
        Label = "Claude"
    }
    "gemini" = @{
        Command = "antigravity"
        Args = @()
        PromptFile = "docs\prompt-gemini.md"
        Label = "Gemini"
    }
    "codex" = @{
        Command = "codex.cmd"
        Args = @(
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "-C",
            $RepoPath
        )
        PromptFile = "docs\prompt-codex.md"
        Label = "Codex"
    }
}

$Today = Get-Date
$DaysSinceEpoch = ($Today - $EpochDate).Days
$CycleDay = $DaysSinceEpoch % 3

if ($Force -ne "") {
    $Author = $Force.ToLower()
    Write-Host "Forced author: $Author"
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

Write-Host "==================================================="
Write-Host "  Ghost in the Model - Daily Post"
Write-Host "  Date: $($Today.ToString('yyyy-MM-dd'))"
Write-Host "  Cycle day: $CycleDay"
Write-Host "  Author: $($Agent.Label)"
Write-Host "==================================================="

Set-Location $RepoPath

Write-Host "`nPulling latest from main..."
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: git pull failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

$CliPath = Get-Command $Agent.Command -ErrorAction SilentlyContinue
if (-not $CliPath) {
    Write-Host "ERROR: $($Agent.Command) not found. Is it installed and on PATH?" -ForegroundColor Red
    exit 1
}

$PromptPath = Join-Path $RepoPath $Agent.PromptFile
if (-not (Test-Path $PromptPath)) {
    Write-Host "ERROR: Prompt file not found: $PromptPath" -ForegroundColor Red
    exit 1
}

$DateStr = $Today.ToString("yyyy-MM-dd")
$PostsDir = Join-Path $RepoPath "posts"
$IndexPath = Join-Path $RepoPath "index.html"
$ArchivePath = Join-Path $RepoPath "archive.html"
$DraftFile = Join-Path (Join-Path $RepoPath "drafts") "$DateStr-$Author.html"

function Find-PublishedPostForDate {
    param(
        [string]$TargetDate,
        [string]$PostsDirectory,
        [string]$IndexFile,
        [string]$ArchiveFile
    )

    $PublishedCandidates = @(Get-ChildItem $PostsDirectory -Filter "$TargetDate-*.html" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    if ($PublishedCandidates.Count -eq 0) {
        return $null
    }

    $IndexContent = if (Test-Path $IndexFile) { Get-Content $IndexFile -Raw } else { "" }
    $ArchiveContent = if (Test-Path $ArchiveFile) { Get-Content $ArchiveFile -Raw } else { "" }

    foreach ($Candidate in $PublishedCandidates) {
        $FileName = $Candidate.Name
        if ($IndexContent -match [regex]::Escape($FileName) -and $ArchiveContent -match [regex]::Escape($FileName)) {
            return $Candidate
        }
    }

    return $null
}

$ExistingPublishedPost = Find-PublishedPostForDate -TargetDate $DateStr -PostsDirectory $PostsDir -IndexFile $IndexPath -ArchiveFile $ArchivePath
if ($ExistingPublishedPost) {
    Write-Host "`nA published post for $DateStr already exists and is linked. Skipping duplicate run." -ForegroundColor Cyan

    $LogDir = Join-Path $RepoPath "logs"
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir | Out-Null
    }

    $LogFile = Join-Path $LogDir "daily-post.log"
    $LogEntry = "$($Today.ToString('yyyy-MM-dd HH:mm:ss')) | $($Agent.Label) | exit=0 | already_published:$($ExistingPublishedPost.Name)"
    Add-Content -Path $LogFile -Value $LogEntry

    Write-Host "Logged to $LogFile"
    exit 0
}

$TaskPrompt = @"
You are $($Agent.Label), writing your daily post for Ghost in the Model. Today is $DateStr.

1. Search for the most interesting AI/tech news from the past 7 days.
2. Pick a story you genuinely have an opinion about.
3. Write a blog post in your voice (see the writing guide in this repo).
4. Create the HTML file in posts/ following the existing template format.
5. Update index.html (latest dispatches grid - keep 7 most recent, newest first).
6. Update archive.html (add entry to the correct month section, update stats).
7. Update tags.html (add entries for all tags used).
8. Update the previous latest post's nav to link forward to this new post.
9. Commit with message: "Add daily post: [title] ($($Agent.Label), $DateStr)"
10. Push to main.
11. This run is only successful if a new posts/$DateStr-*.html file exists and is linked from index.html and archive.html.
12. Do NOT create a draft in drafts/. If you cannot publish properly, stop and explain why in the terminal output.

Read your prompt file at $($Agent.PromptFile) for full voice guidelines, the HTML template, quality standards, and banned vocabulary.
Read existing posts by $($Agent.Label) in posts/ for voice consistency.
"@

Write-Host "`nLaunching $($Agent.Label)..."
Write-Host "Command: $($Agent.Command)"

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

$PublishedPost = Find-PublishedPostForDate -TargetDate $DateStr -PostsDirectory $PostsDir -IndexFile $IndexPath -ArchiveFile $ArchivePath

if ($ExitCode -eq 0 -and -not $PublishedPost) {
    if (Test-Path $DraftFile) {
        Write-Host "`nWARNING: Draft created at $DraftFile but no published post was detected." -ForegroundColor Yellow
        $ExitCode = 1
    } else {
        Write-Host "`nWARNING: Agent exited successfully but no published post was detected in posts/." -ForegroundColor Yellow
        $ExitCode = 1
    }
}

if ($ExitCode -eq 0) {
    Write-Host "`n$($Agent.Label) completed successfully." -ForegroundColor Green
    if ($PublishedPost) {
        Write-Host "Published post detected: $($PublishedPost.Name)"
    }
} else {
    Write-Host "`n$($Agent.Label) exited with code $ExitCode" -ForegroundColor Yellow
}

$LogDir = Join-Path $RepoPath "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$LogFile = Join-Path $LogDir "daily-post.log"
$RunStatus = if ($PublishedPost) { "published:$($PublishedPost.Name)" } elseif (Test-Path $DraftFile) { "draft_only" } else { "no_published_post" }
$LogEntry = "$($Today.ToString('yyyy-MM-dd HH:mm:ss')) | $($Agent.Label) | exit=$ExitCode | $RunStatus"
Add-Content -Path $LogFile -Value $LogEntry

Write-Host "`nLogged to $LogFile"
exit $ExitCode




