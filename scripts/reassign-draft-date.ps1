param(
    [Parameter(Mandatory = $true)]
    [string]$DraftPath,
    [string]$NewDate = '',
    [switch]$NextFree
)

$ErrorActionPreference = 'Stop'

$RepoPath = 'W:\Websites\sites\ghost-in-the-models'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Get-NormalizedDraftPath {
    param(
        [string]$InputPath,
        [string]$Root
    )

    $candidate = $InputPath
    if (-not [System.IO.Path]::IsPathRooted($candidate)) {
        $candidate = Join-Path $Root $candidate
    }

    $fullPath = [System.IO.Path]::GetFullPath($candidate)
    $repoRoot = [System.IO.Path]::GetFullPath($Root)
    if (-not $fullPath.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Draft must live inside the repo: $fullPath"
    }

    if (-not (Test-Path $fullPath)) {
        throw "Draft not found: $fullPath"
    }

    return $fullPath
}

function Format-LongDate {
    param([string]$DateText)

    $date = [datetime]::ParseExact($DateText, 'yyyy-MM-dd', $null)
    return '{0} {1:MMMM yyyy}' -f $date.Day, $date
}

function Get-NextFreeDate {
    param(
        [string]$Root,
        [string]$StartDate
    )

    $occupied = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    Get-ChildItem (Join-Path $Root 'posts') -Filter '*.html' | ForEach-Object {
        if ($_.Name -match '^(\d{4}-\d{2}-\d{2})') {
            [void]$occupied.Add($matches[1])
        }
    }
    Get-ChildItem (Join-Path $Root 'drafts') -Filter '*.html' | ForEach-Object {
        if ($_.Name -match '^(\d{4}-\d{2}-\d{2})') {
            [void]$occupied.Add($matches[1])
        }
    }

    $cursor = [datetime]::ParseExact($StartDate, 'yyyy-MM-dd', $null)
    for ($attempt = 0; $attempt -lt 366; $attempt++) {
        $candidate = $cursor.ToString('yyyy-MM-dd')
        if (-not $occupied.Contains($candidate)) {
            return $candidate
        }
        $cursor = $cursor.AddDays(1)
    }

    throw 'Unable to find a free draft date in the next 365 days.'
}

if (-not $NewDate -and -not $NextFree) {
    throw 'Provide -NewDate <yyyy-MM-dd> or -NextFree.'
}

$fullPath = Get-NormalizedDraftPath -InputPath $DraftPath -Root $RepoPath
$fileName = [System.IO.Path]::GetFileName($fullPath)
if ($fileName -notmatch '^(\d{4}-\d{2}-\d{2})(-.+)$') {
    throw "Draft file name does not start with a date: $fileName"
}

$oldDate = $matches[1]
$suffix = $matches[2]
$targetDate = if ($NextFree) { Get-NextFreeDate -Root $RepoPath -StartDate $oldDate } else { $NewDate }

if ($targetDate -notmatch '^\d{4}-\d{2}-\d{2}$') {
    throw "Invalid date format: $targetDate"
}

$targetPath = Join-Path (Split-Path -Parent $fullPath) ($targetDate + $suffix)
if ((Test-Path $targetPath) -and ($targetPath -ne $fullPath)) {
    throw "Target draft already exists: $targetPath"
}

$raw = Get-Content -Raw -LiteralPath $fullPath
$updated = [regex]::Replace(
    $raw,
    '<time([^>]+datetime=\")(\d{4}-\d{2}-\d{2})(\">)(.*?)(</time>)',
    ('<time$1' + $targetDate + '$3' + (Format-LongDate -DateText $targetDate) + '$5'),
    1
)

[System.IO.File]::WriteAllText($fullPath, $updated, $Utf8NoBom)

if ($fullPath -ne $targetPath) {
    Move-Item -LiteralPath $fullPath -Destination $targetPath -Force
}

Write-Host "Reassigned draft date: $oldDate -> $targetDate" -ForegroundColor Green
Write-Host "Draft path: $targetPath"
