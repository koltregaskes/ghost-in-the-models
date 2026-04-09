param(
    [Parameter(Mandatory = $true)]
    [Alias('File')]
    [string]$DraftPath,
    [Parameter(Mandatory = $true)]
    [ValidateSet('yay', 'nay', 'needs_images', 'hold')]
    [string]$Verdict,
    [Parameter(Mandatory = $true)]
    [string]$Summary,
    [string]$Editor = 'website-manager',
    [string[]]$Feedback = @(),
    [ValidateSet('pass', 'fail', 'pending', 'not_applicable')]
    [string]$SecurityStatus = 'pending',
    [string]$SecurityNotes = '',
    [ValidateSet('pass', 'fail', 'pending', 'not_applicable')]
    [string]$ContextStatus = 'pending',
    [string]$ContextNotes = '',
    [ValidateSet('pass', 'fail', 'pending', 'not_applicable')]
    [string]$FactsStatus = 'pending',
    [string]$FactsNotes = '',
    [ValidateSet('pass', 'fail', 'pending', 'not_applicable')]
    [string]$DatesStatus = 'pending',
    [string]$DatesNotes = '',
    [ValidateSet('pass', 'fail', 'pending', 'not_applicable')]
    [string]$WritingStatus = 'pending',
    [string]$WritingNotes = '',
    [ValidateSet('pass', 'fail', 'pending', 'not_applicable')]
    [string]$ImagesStatus = 'pending',
    [string]$ImagesNotes = '',
    [switch]$NoAutoPublish
)

$ErrorActionPreference = 'Stop'

$RepoPath = "W:\Websites\sites\ghost-in-the-models"
$RecorderScript = "W:\Websites\shared\website-tools\pipelines\articles\scripts\record-editorial-review.py"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

function Get-NormalizedRelativePath {
    param(
        [string]$InputPath,
        [string]$Root
    )

    $CandidatePath = $InputPath
    if (-not [System.IO.Path]::IsPathRooted($CandidatePath)) {
        $CandidatePath = Join-Path $Root $CandidatePath
    }

    $FullPath = [System.IO.Path]::GetFullPath($CandidatePath)
    $RepoRoot = [System.IO.Path]::GetFullPath($Root)

    if (-not $FullPath.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "File must live inside the repo: $FullPath"
    }

    if (-not (Test-Path $FullPath)) {
        throw "File not found: $FullPath"
    }

    return $FullPath.Substring($RepoRoot.Length).TrimStart('\').Replace('\', '/')
}

$RelativePath = Get-NormalizedRelativePath -InputPath $DraftPath -Root $RepoPath

$Payload = @{
    site = 'ghost-in-the-models'
    relative_path = $RelativePath
    verdict = $Verdict
    summary = $Summary
    editor = $Editor
    feedback = @($Feedback)
    no_auto_publish = [bool]$NoAutoPublish
    checklist = @{
        security_sensitive_data = @{
            status = $SecurityStatus
            notes = $SecurityNotes
        }
        context_and_controversy = @{
            status = $ContextStatus
            notes = $ContextNotes
        }
        facts_and_sourcing = @{
            status = $FactsStatus
            notes = $FactsNotes
        }
        dates_and_chronology = @{
            status = $DatesStatus
            notes = $DatesNotes
        }
        writing_edit = @{
            status = $WritingStatus
            notes = $WritingNotes
        }
        images_and_media = @{
            status = $ImagesStatus
            notes = $ImagesNotes
        }
    }
}

$PayloadPath = [System.IO.Path]::GetTempFileName()
Write-Utf8NoBom -Path $PayloadPath -Content (($Payload | ConvertTo-Json -Depth 10) + "`n")

Write-Host "==================================================="
Write-Host "  Ghost in the Models - Editorial Review"
Write-Host "  File: $RelativePath"
Write-Host "  Verdict: $Verdict"
Write-Host "==================================================="

try {
    python $RecorderScript --payload-file $PayloadPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to record editorial review."
    }
} finally {
    Remove-Item $PayloadPath -ErrorAction SilentlyContinue
}

if ($Verdict -eq 'yay' -and -not $NoAutoPublish) {
    Write-Host "`nApproved review recorded. Ghost in the Models auto-publish policy has been applied." -ForegroundColor Green
} else {
    Write-Host "`nReview recorded." -ForegroundColor Green
}
