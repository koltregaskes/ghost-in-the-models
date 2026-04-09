param(
    [string]$Force = "",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

<#
    Ghost in the Models - Draft Writer

    Writes a draft article but does not publish it.
    Drafts go to drafts/ for review.
#>

$RepoPath = "W:\Websites\sites\ghost-in-the-models"
$DraftsDir = Join-Path $RepoPath "drafts"
$RotationPath = Join-Path $RepoPath ".agents\rotation.json"
$HubBuildScript = "W:\Websites\shared\website-tools\pipelines\articles\scripts\build-editorial-hub.py"
$RunLogsDir = Join-Path $RepoPath "logs\agent-runs"

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

function Refresh-EditorialHub {
    param([string]$ScriptPath)

    if (-not (Test-Path $ScriptPath)) {
        return
    }

    python $ScriptPath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to rebuild editorial hub state.'
    }
}

function Invoke-AgentTask {
    param(
        [string]$AuthorKey,
        [hashtable]$AgentConfig,
        [string]$Prompt,
        [string]$LogsDirectory
    )

    if (-not (Test-Path $LogsDirectory)) {
        New-Item -ItemType Directory -Path $LogsDirectory -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $transcriptPath = Join-Path $LogsDirectory "$timestamp-$AuthorKey-write-draft.txt"

    $output = switch ($AuthorKey) {
        'claude' { & $AgentConfig.Command @($AgentConfig.Args + @($Prompt)) 2>&1 }
        'gemini' { & $AgentConfig.Command @($AgentConfig.Args + @('--prompt', $Prompt)) 2>&1 }
        'codex' { & $AgentConfig.Command @($AgentConfig.Args + @($Prompt)) 2>&1 }
    }

    $lines = @($output | ForEach-Object { $_.ToString() })
    Set-Content -Path $transcriptPath -Value (($lines -join [Environment]::NewLine).Trim()) -Encoding UTF8

    return @{
        ExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
        TranscriptPath = $transcriptPath
    }
}

$Today = Get-Date
$DateStr = $Today.ToString("yyyy-MM-dd")

if (-not (Test-Path $DraftsDir)) {
    New-Item -ItemType Directory -Path $DraftsDir | Out-Null
}

Sync-RepoWithMain -Path $RepoPath

$RotationState = Get-RotationOrder -Path $RotationPath -ConfiguredAgents $Agents
$RotationOrder = $RotationState.Order

if ($Force -ne "") {
    $Author = $Force.ToLower()
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
Write-Host "  Ghost in the Models - Draft Writer"
Write-Host "  Date: $DateStr"
Write-Host "  Rotation: $($RotationOrder -join ' -> ')"
Write-Host "  Slot: $CycleIndex of $($RotationOrder.Count)"
Write-Host "  Author: $($Agent.Label)"
Write-Host "  Mode: DRAFT (will not publish)"
Write-Host "==================================================="

$CliPath = Get-Command $Agent.Command -ErrorAction SilentlyContinue
if (-not $CliPath) {
    Write-Host "ERROR: $($Agent.Command) not found." -ForegroundColor Red
    exit 1
}

if ($DryRun) {
    Write-Host "`nDry run only. Draft scheduler wiring looks healthy." -ForegroundColor Cyan
    Write-Host "CLI path: $($CliPath.Source)"
    exit 0
}

$TaskPrompt = @"
You are $($Agent.Label), writing your daily dispatch for Ghost in the Models.
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
    default {}
}

$Invocation = Invoke-AgentTask -AuthorKey $Author -AgentConfig $Agent -Prompt $TaskPrompt -LogsDirectory $RunLogsDir
$ExitCode = $Invocation.ExitCode
$TranscriptPath = $Invocation.TranscriptPath

$DraftFile = Join-Path $DraftsDir "$DateStr-$Author.html"
if (Test-Path $DraftFile) {
    Write-Host "`nDraft created: $DraftFile" -ForegroundColor Green
    Write-Host "Transcript: $TranscriptPath"
    Refresh-EditorialHub -ScriptPath $HubBuildScript
    Write-Host "Review it with: .\scripts\review-draft.ps1 -DraftPath $DraftFile -Verdict <yay|nay|needs_images|hold> -Summary ""..."""
    Write-Host "If the verdict is 'yay', Ghost in the Models will auto-publish after the review is recorded."
} else {
    Write-Host "`nWARNING: No draft file found at $DraftFile" -ForegroundColor Yellow
    Write-Host "Transcript: $TranscriptPath"
    Write-Host "The agent may have saved it elsewhere. Check drafts/ folder."
}

$LogDir = Join-Path $RepoPath "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$LogFile = Join-Path $LogDir "draft-writer.log"
$HasDraft = if (Test-Path $DraftFile) { "draft_created" } else { "no_draft" }
$LogEntry = "$($Today.ToString('yyyy-MM-dd HH:mm:ss')) | $($Agent.Label) | exit=$ExitCode | $HasDraft | transcript:$([System.IO.Path]::GetFileName($TranscriptPath))"
Add-Content -Path $LogFile -Value $LogEntry

exit $ExitCode





