param(
    [Parameter(Mandatory = $true)]
    [string]$DraftPath,
    [string]$EditorAgent = '',
    [string]$EditorName = 'website-manager-ai',
    [switch]$NoAutoPublish,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$RepoPath = 'W:\Websites\sites\ghost-in-the-models'
$PolicyPath = Join-Path $RepoPath 'config\site-policy.json'
$ReviewScript = Join-Path $RepoPath 'scripts\review-draft.ps1'
$PromptPath = Join-Path $RepoPath 'docs\prompt-website-manager.md'
$LogDir = Join-Path $RepoPath 'logs\editorial'

$Agents = @{
    'claude' = @{
        Command = 'claude'
        Args = @('--print', '--dangerously-skip-permissions')
        Label = 'Claude'
    }
    'gemini' = @{
        Command = 'antigravity'
        Args = @()
        Label = 'Gemini'
    }
    'codex' = @{
        Command = 'codex.cmd'
        Args = @(
            'exec',
            '--dangerously-bypass-approvals-and-sandbox',
            '-C',
            $RepoPath
        )
        Label = 'Codex'
    }
}

function Get-NormalizedRelativePath {
    param(
        [string]$InputPath,
        [string]$Root
    )

    $candidatePath = $InputPath
    if (-not [System.IO.Path]::IsPathRooted($candidatePath)) {
        $candidatePath = Join-Path $Root $candidatePath
    }

    $fullPath = [System.IO.Path]::GetFullPath($candidatePath)
    $repoRoot = [System.IO.Path]::GetFullPath($Root)

    if (-not $fullPath.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "File must live inside the repo: $fullPath"
    }

    if (-not (Test-Path $fullPath)) {
        throw "File not found: $fullPath"
    }

    return @{
        FullPath = $fullPath
        RelativePath = $fullPath.Substring($repoRoot.Length).TrimStart('\').Replace('\', '/')
    }
}

function Get-Policy {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return @{
            automation = @{
                auto_review_enabled = $false
                default_editor_agent = 'claude'
            }
        }
    }

    return Get-Content -Raw $Path | ConvertFrom-Json
}

function Get-AgentPrompt {
    param(
        [string]$AgentName,
        [string]$DraftRelativePath
    )

    return @"
You are acting as the website manager editor for Ghost in the Models.

Review exactly one draft: $DraftRelativePath

Before you answer:
1. Read docs/prompt-website-manager.md
2. Read docs/editorial-review-policy.md
3. Read docs/agent-writing-packet.md
4. Read the draft file at $DraftRelativePath
5. If needed for fact or date checks, inspect relevant files in news-digests/ and recent posts/
6. If your environment supports web research and the draft makes current or time-sensitive factual claims, verify only what you need

Rules:
- Do not edit the draft
- Do not modify any files
- Do not commit or push anything
- Return JSON only, with no markdown fences and no extra commentary
- Follow the exact JSON schema in docs/prompt-website-manager.md

Your checklist verdict must explicitly cover:
- security_sensitive_data
- context_and_controversy
- facts_and_sourcing
- dates_and_chronology
- writing_edit
- images_and_media
"@
}

function Invoke-EditorAgent {
    param(
        [string]$AgentKey,
        [string]$Prompt,
        [string]$TranscriptPath
    )

    $agent = $Agents[$AgentKey]
    if (-not $agent) {
        throw "Unknown editor agent '$AgentKey'."
    }

    $cliPath = Get-Command $agent.Command -ErrorAction SilentlyContinue
    if (-not $cliPath) {
        throw "$($agent.Command) not found on PATH."
    }

    Write-Host "Launching editor agent: $($agent.Label)" -ForegroundColor Cyan
    Set-Location $RepoPath

    $output = switch ($AgentKey) {
        'claude' { & $agent.Command @($agent.Args + @($Prompt)) 2>&1 }
        'gemini' { & $agent.Command @($agent.Args + @('--prompt', $Prompt)) 2>&1 }
        'codex' { & $agent.Command @($agent.Args + @($Prompt)) 2>&1 }
    }

    $lines = @($output | ForEach-Object { $_.ToString() })
    $rawOutput = ($lines -join [Environment]::NewLine).Trim()
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    Set-Content -Path $TranscriptPath -Value $rawOutput -Encoding UTF8

    if ($LASTEXITCODE -ne 0) {
        throw "Editor agent exited with code $LASTEXITCODE. Transcript: $TranscriptPath"
    }

    return $rawOutput
}

function Parse-ReviewJson {
    param([string]$RawOutput)

    $start = $RawOutput.IndexOf('{')
    $end = $RawOutput.LastIndexOf('}')
    if ($start -lt 0 -or $end -lt $start) {
        throw 'Editor output did not contain a JSON object.'
    }

    $jsonText = $RawOutput.Substring($start, $end - $start + 1)
    try {
        return $jsonText | ConvertFrom-Json
    } catch {
        $tempInput = [System.IO.Path]::GetTempFileName()
        $tempOutput = [System.IO.Path]::GetTempFileName()
        try {
            Set-Content -Path $tempInput -Value $jsonText -Encoding UTF8

            $repairScript = @"
from pathlib import Path
from json_repair import repair_json

source = Path(r'''$tempInput''')
target = Path(r'''$tempOutput''')
target.write_text(repair_json(source.read_text(encoding='utf-8'), ensure_ascii=False), encoding='utf-8')
"@

            $repairScript | python -
            if ($LASTEXITCODE -ne 0) {
                throw
            }

            return Get-Content -Raw $tempOutput | ConvertFrom-Json
        } finally {
            Remove-Item $tempInput, $tempOutput -ErrorAction SilentlyContinue
        }
    }
}

function Require-ChecklistEntry {
    param(
        [object]$Payload,
        [string]$Key
    )

    $entry = $Payload.checks.$Key
    if (-not $entry) {
        throw "Editor JSON is missing checks.$Key"
    }

    return $entry
}

$policy = Get-Policy -Path $PolicyPath
if (-not $EditorAgent) {
    $EditorAgent = [string]$policy.automation.default_editor_agent
}
$EditorAgent = $EditorAgent.ToLowerInvariant()

$draft = Get-NormalizedRelativePath -InputPath $DraftPath -Root $RepoPath
if (-not $draft.RelativePath.StartsWith('drafts/')) {
    throw "Auto review only accepts drafts under drafts/. Got: $($draft.RelativePath)"
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$transcriptPath = Join-Path $LogDir "$timestamp-$EditorAgent-review.txt"

Write-Host '==================================================='
Write-Host '  Ghost in the Models - Auto Review'
Write-Host "  Draft: $($draft.RelativePath)"
Write-Host "  Editor Agent: $EditorAgent"
Write-Host '==================================================='

if ($DryRun) {
    Write-Host "Dry run only. Would review $($draft.RelativePath) with $EditorAgent." -ForegroundColor Cyan
    Write-Host "Prompt file: $PromptPath"
    exit 0
}

$prompt = Get-AgentPrompt -AgentName $EditorAgent -DraftRelativePath $draft.RelativePath
$rawOutput = Invoke-EditorAgent -AgentKey $EditorAgent -Prompt $prompt -TranscriptPath $transcriptPath
$review = Parse-ReviewJson -RawOutput $rawOutput

$requiredChecks = @(
    'security_sensitive_data',
    'context_and_controversy',
    'facts_and_sourcing',
    'dates_and_chronology',
    'writing_edit',
    'images_and_media'
)

if (-not $review.verdict) { throw 'Editor JSON is missing verdict.' }
if (-not $review.summary) { throw 'Editor JSON is missing summary.' }

$reviewParams = @{
    DraftPath = $draft.RelativePath
    Verdict = [string]$review.verdict
    Summary = [string]$review.summary
    Editor = $EditorName
}

foreach ($item in @($review.feedback)) {
    if ($null -ne $item -and [string]::IsNullOrWhiteSpace([string]$item) -eq $false) {
        $existingFeedback = @($reviewParams.Feedback)
        $reviewParams.Feedback = @($existingFeedback + @([string]$item))
    }
}

foreach ($checkKey in $requiredChecks) {
    $entry = Require-ChecklistEntry -Payload $review -Key $checkKey
    switch ($checkKey) {
        'security_sensitive_data' {
            $reviewParams.SecurityStatus = [string]$entry.status
            $reviewParams.SecurityNotes = [string]$entry.notes
        }
        'context_and_controversy' {
            $reviewParams.ContextStatus = [string]$entry.status
            $reviewParams.ContextNotes = [string]$entry.notes
        }
        'facts_and_sourcing' {
            $reviewParams.FactsStatus = [string]$entry.status
            $reviewParams.FactsNotes = [string]$entry.notes
        }
        'dates_and_chronology' {
            $reviewParams.DatesStatus = [string]$entry.status
            $reviewParams.DatesNotes = [string]$entry.notes
        }
        'writing_edit' {
            $reviewParams.WritingStatus = [string]$entry.status
            $reviewParams.WritingNotes = [string]$entry.notes
        }
        'images_and_media' {
            $reviewParams.ImagesStatus = [string]$entry.status
            $reviewParams.ImagesNotes = [string]$entry.notes
        }
    }
}

if ($NoAutoPublish) {
    $reviewParams.NoAutoPublish = $true
}

& $ReviewScript @reviewParams
if ($LASTEXITCODE -ne 0) {
    throw "Failed to record review from $EditorAgent."
}

Write-Host "`nAuto review completed." -ForegroundColor Green
Write-Host "Transcript: $transcriptPath"
