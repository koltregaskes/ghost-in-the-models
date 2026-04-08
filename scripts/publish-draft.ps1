$ErrorActionPreference = 'Stop'

function Get-InvocationOptions {
    param([string[]]$Arguments)

    $draftPath = $null
    $force = $false

    for ($index = 0; $index -lt $Arguments.Count; $index++) {
        $current = $Arguments[$index]
        switch -Regex ($current) {
            '^(?i)-force$' {
                $force = $true
                continue
            }
            '^(?i)-(draftpath|file)$' {
                if ($index + 1 -ge $Arguments.Count) {
                    throw "Missing value for $current"
                }
                $index++
                $draftPath = $Arguments[$index]
                continue
            }
            default {
                if (-not $draftPath) {
                    $draftPath = $current
                } else {
                    throw "Unexpected argument: $current"
                }
            }
        }
    }

    if (-not $draftPath) {
        throw 'Usage: publish-draft.ps1 -DraftPath <path> [-Force]'
    }

    return @{
        DraftPath = $draftPath
        Force = $force
    }
}

<#$
    Ghost in the Models - Publish Approved Draft

    Takes a reviewed draft from drafts/ and:
    1. Verifies there is an approved editorial review
    2. Copies it to posts/
    3. Rebuilds derived site files
    4. Validates the site
    5. Moves the review record onto the published article
#>

$RepoPath = 'W:\Websites\sites\ghost-in-the-models'
$SiteId = 'ghost-in-the-models'
$ManifestPath = 'W:\Websites\shared\website-tools\registry\sites\ghost-in-the-models.json'
$HubBuildScript = 'W:\Websites\shared\website-tools\pipelines\articles\scripts\build-editorial-hub.py'
$BlockingChecks = @(
    'security_sensitive_data',
    'context_and_controversy',
    'facts_and_sourcing',
    'dates_and_chronology',
    'writing_edit',
    'images_and_media'
)
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

function Get-NormalizedDraftInfo {
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

    $relativePath = $fullPath.Substring($repoRoot.Length).TrimStart('\').Replace('\', '/')
    if (-not $relativePath.StartsWith('drafts/')) {
        throw "publish-draft.ps1 expects a draft under drafts/. Got: $relativePath"
    }

    return @{
        FullPath = $fullPath
        RelativePath = $relativePath
        FileName = [System.IO.Path]::GetFileName($fullPath)
    }
}

function Get-ReviewRecordInfo {
    param(
        [string]$RelativePath,
        [pscustomobject]$Manifest,
        [string]$CurrentSiteId
    )

    $articleId = "${CurrentSiteId}:$RelativePath"
    $safeName = $articleId -replace '[^A-Za-z0-9._-]+', '__'
    $reviewDir = $Manifest.review.review_dir
    return @{
        ArticleId = $articleId
        ReviewDir = $reviewDir
        ReviewPath = Join-Path $reviewDir "$safeName.json"
    }
}

function Test-ApprovedReview {
    param(
        [string]$ReviewPath,
        [string[]]$RequiredChecks
    )

    if (-not (Test-Path $ReviewPath)) {
        throw "No editorial review found for this draft. Expected: $ReviewPath"
    }

    $review = Get-Content -Raw $ReviewPath | ConvertFrom-Json
    if ($review.verdict -ne 'yay') {
        throw "Draft review verdict must be 'yay' before publishing. Current verdict: $($review.verdict)"
    }

    foreach ($check in $RequiredChecks) {
        $entry = $review.checklist.$check
        if (-not $entry) {
            throw "Review checklist is missing '$check'."
        }

        $status = [string]$entry.status
        if ($status -notin @('pass', 'not_applicable')) {
            throw "Checklist item '$check' must be pass or not_applicable before publishing. Current status: $status"
        }
    }

    return $review
}

function Refresh-EditorialHub {
    param([string]$ScriptPath)

    python $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to rebuild editorial hub state.'
    }
}

$options = Get-InvocationOptions -Arguments $args
$DraftPath = $options.DraftPath
$Force = $options.Force

Set-Location $RepoPath

if (-not (Test-Path $ManifestPath)) {
    throw "Editorial site manifest not found: $ManifestPath"
}

$manifest = Get-Content -Raw $ManifestPath | ConvertFrom-Json
$draft = Get-NormalizedDraftInfo -InputPath $DraftPath -Root $RepoPath
$destinationPath = Join-Path (Join-Path $RepoPath 'posts') $draft.FileName
$draftReview = Get-ReviewRecordInfo -RelativePath $draft.RelativePath -Manifest $manifest -CurrentSiteId $SiteId
$publishedRelativePath = "posts/$($draft.FileName)"
$publishedReview = Get-ReviewRecordInfo -RelativePath $publishedRelativePath -Manifest $manifest -CurrentSiteId $SiteId

Write-Host '==================================================='
Write-Host '  Ghost in the Models - Publish Draft'
Write-Host "  Source: $($draft.RelativePath)"
Write-Host "  Destination: $publishedRelativePath"
Write-Host '==================================================='

$review = $null
if (-not $Force) {
    $review = Test-ApprovedReview -ReviewPath $draftReview.ReviewPath -RequiredChecks $BlockingChecks
    Write-Host "Approved review found: $($draftReview.ReviewPath)" -ForegroundColor Green
} else {
    Write-Host 'Force flag set: bypassing editorial gate.' -ForegroundColor Yellow
}

Copy-Item $draft.FullPath $destinationPath -Force
Write-Host "`nDraft copied to posts/" -ForegroundColor Green

Write-Host "`nRebuilding derived site files..."
python "$RepoPath\scripts\rebuild-derived.py"
if ($LASTEXITCODE -ne 0) {
    throw 'Derived site rebuild failed.'
}

Write-Host 'Running site validation...'
powershell -NoProfile -ExecutionPolicy Bypass -File "$RepoPath\scripts\validate-site.ps1"
if ($LASTEXITCODE -ne 0) {
    throw 'Site validation failed.'
}

if ($review) {
    $review.article_id = $publishedReview.ArticleId
    $review.relative_path = $publishedRelativePath
    $review | Add-Member -NotePropertyName published_at -NotePropertyValue ((Get-Date).ToString('o')) -Force
    $reviewJson = $review | ConvertTo-Json -Depth 10

    if (-not (Test-Path $publishedReview.ReviewDir)) {
        New-Item -ItemType Directory -Path $publishedReview.ReviewDir -Force | Out-Null
    }

    Write-Utf8NoBom -Path $publishedReview.ReviewPath -Content ($reviewJson + "`n")
    if ($draftReview.ReviewPath -ne $publishedReview.ReviewPath -and (Test-Path $draftReview.ReviewPath)) {
        Remove-Item $draftReview.ReviewPath -Force
    }
}

if (Test-Path $draft.FullPath) {
    Remove-Item $draft.FullPath -Force
    Write-Host 'Draft cleaned up.'
}

Refresh-EditorialHub -ScriptPath $HubBuildScript

Write-Host "`nPublished successfully!" -ForegroundColor Green
Write-Host 'Review gate passed and hub state refreshed.'
