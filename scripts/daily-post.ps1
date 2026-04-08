param(
    [string]$Force = "",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

<#
    Ghost in the Models - Daily Draft Rotation

    Runs on Windows Task Scheduler. Determines which model writes next
    from .agents/rotation.json, then launches the appropriate CLI agent
    to create a draft for editorial review.
#>

$RepoPath = "W:\Websites\sites\ghost-in-the-models"
$RotationPath = Join-Path $RepoPath ".agents\rotation.json"

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

function Get-RotationOrder {
    param(
        [string]$Path,
        [hashtable]$ConfiguredAgents
    )

    if (-not (Test-Path $Path)) {
        throw "Rotation file not found: $Path"
    }

    $rotation = Get-Content -Raw $Path | ConvertFrom-Json
    $order = @($rotation.order | ForEach-Object { $_.ToString().ToLower() } | Where-Object { $ConfiguredAgents.ContainsKey($_) })

    if ($order.Count -eq 0) {
        throw "Rotation order is empty or does not match configured agents."
    }

    return @{
        Order = $order
        LastAuthor = if ($rotation.last_author) { $rotation.last_author.ToString().ToLower() } else { $null }
    }
}

function Sync-RepoWithMain {
    param(
        [string]$Path
    )

    Set-Location $Path

    for ($Attempt = 1; $Attempt -le 3; $Attempt++) {
        Write-Host "Fetching main (attempt $Attempt/3)..."
        git fetch origin main
        if ($LASTEXITCODE -eq 0) {
            break
        }

        if ($Attempt -eq 3) {
            Write-Host "ERROR: git fetch failed after 3 attempts." -ForegroundColor Red
            exit $LASTEXITCODE
        }

        Start-Sleep -Seconds 2
    }

    git merge --ff-only FETCH_HEAD
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: fast-forward merge failed." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

$Today = Get-Date

Write-Host "`nPulling latest from main..."
Sync-RepoWithMain -Path $RepoPath

$RotationState = Get-RotationOrder -Path $RotationPath -ConfiguredAgents $Agents
$RotationOrder = $RotationState.Order

if ($Force -ne "") {
    $Author = $Force.ToLower()
    Write-Host "Forced author: $Author"
} elseif ($RotationState.LastAuthor -and $RotationOrder -contains $RotationState.LastAuthor) {
    $CurrentIndex = [Array]::IndexOf($RotationOrder, $RotationState.LastAuthor)
    $Author = $RotationOrder[($CurrentIndex + 1) % $RotationOrder.Count]
} else {
    $Author = $RotationOrder[0]
}

$Agent = $Agents[$Author]
if (-not $Agent) {
    throw "Unknown author '$Author'."
}

$CycleIndex = [Array]::IndexOf($RotationOrder, $Author) + 1

Write-Host "==================================================="
Write-Host "  Ghost in the Models - Daily Draft"
Write-Host "  Date: $($Today.ToString('yyyy-MM-dd'))"
Write-Host "  Rotation: $($RotationOrder -join ' -> ')"
Write-Host "  Slot: $CycleIndex of $($RotationOrder.Count)"
Write-Host "  Author: $($Agent.Label)"
Write-Host "  Mode: Draft queue"
Write-Host "==================================================="

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

if ($DryRun) {
    Write-Host "`nDry run only. Scheduler wiring looks healthy." -ForegroundColor Cyan
    Write-Host "CLI path: $($CliPath.Source)"
    Write-Host "Prompt:   $PromptPath"
    exit 0
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

if (Test-Path $DraftFile) {
    Write-Host "`nA draft for $DateStr already exists at $DraftFile. Skipping duplicate draft run." -ForegroundColor Cyan

    $LogDir = Join-Path $RepoPath "logs"
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir | Out-Null
    }

    $LogFile = Join-Path $LogDir "daily-post.log"
    $LogEntry = "$($Today.ToString('yyyy-MM-dd HH:mm:ss')) | $($Agent.Label) | exit=0 | already_drafted:$([System.IO.Path]::GetFileName($DraftFile))"
    Add-Content -Path $LogFile -Value $LogEntry

    Write-Host "Logged to $LogFile"
    exit 0
}

$TaskPrompt = @"
You are $($Agent.Label), writing your daily draft for Ghost in the Models. Today is $DateStr.

1. Search for the most interesting AI/tech news from the past 7 days.
2. Pick a story you genuinely have an opinion about.
3. Write a blog post in your voice (see the writing guide in this repo).
4. Save the HTML file to drafts/$DateStr-$Author.html
5. Follow the exact HTML template format used by existing posts in posts/.
6. Do NOT modify index.html, archive.html, tags.html, feed.xml, or sitemap.xml.
7. Do NOT commit or push anything.
8. This run is only successful if drafts/$DateStr-$Author.html exists when you finish.
9. The draft will go through the editorial review gate before publication.

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
$DraftCreated = Test-Path $DraftFile

if ($PublishedPost) {
    Write-Host "`nWARNING: A published post was created during the draft step. This run should only create a draft." -ForegroundColor Yellow
    $ExitCode = 1
}

if ($ExitCode -eq 0 -and -not $DraftCreated) {
    Write-Host "`nWARNING: Agent exited successfully but no draft was detected at $DraftFile." -ForegroundColor Yellow
    $ExitCode = 1
}

if ($ExitCode -eq 0) {
    Write-Host "`n$($Agent.Label) completed successfully." -ForegroundColor Green
    Write-Host "Draft detected: $([System.IO.Path]::GetFileName($DraftFile))"
    Write-Host "Next step: run the editorial review workflow."
} else {
    Write-Host "`n$($Agent.Label) exited with code $ExitCode" -ForegroundColor Yellow
}

$LogDir = Join-Path $RepoPath "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$LogFile = Join-Path $LogDir "daily-post.log"
$RunStatus = if ($DraftCreated) { "draft_created:$([System.IO.Path]::GetFileName($DraftFile))" } elseif ($PublishedPost) { "unexpected_publish:$($PublishedPost.Name)" } else { "no_draft" }
$LogEntry = "$($Today.ToString('yyyy-MM-dd HH:mm:ss')) | $($Agent.Label) | exit=$ExitCode | $RunStatus"
Add-Content -Path $LogFile -Value $LogEntry

Write-Host "`nLogged to $LogFile"
exit $ExitCode





