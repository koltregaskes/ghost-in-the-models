param(
    [string]$SiteRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

Set-Location $SiteRoot

$errors = New-Object System.Collections.Generic.List[string]

$requiredFiles = @(
    "index.html",
    "about.html",
    "archive.html",
    "tags.html",
    "feed.xml",
    "sitemap.xml",
    "assets/style.css",
    "assets/script.js"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $file)) {
        $errors.Add("Missing required file: $file")
    }
}

$forbiddenPatterns = @(
    "(?<![A-Za-z])Synthetic Dispatch(?![A-Za-z])",
    "(?<![A-Za-z])synthetic-dispatch(?![A-Za-z])",
    "(?<![A-Za-z])SYNTHETIC DISPATCH(?![A-Za-z])",
    "(?<![A-Za-z])Ghost in the Three Minds(?![A-Za-z])",
    "(?<![A-Za-z])GHOST IN THE THREE MINDS(?![A-Za-z])",
    "(?<![A-Za-z])Ghost in the Model(?!s)",
    "(?<![A-Za-z])GHOST IN THE MODEL(?!S)"
)

$textExtensions = @(".html", ".xml", ".txt", ".md", ".js", ".css", ".ps1", ".bat", ".json", ".yml", ".yaml")
$trackedFiles = @(git ls-files)
$textFiles = $trackedFiles | Where-Object {
    $textExtensions -contains [System.IO.Path]::GetExtension($_).ToLower()
}

foreach ($file in $textFiles) {
    if ($file -eq "scripts/validate-site.ps1") {
        continue
    }

    $raw = Get-Content -Raw -LiteralPath $file
    foreach ($pattern in $forbiddenPatterns) {
        if ([regex]::IsMatch($raw, $pattern)) {
            $errors.Add("Forbidden pattern '$pattern' found in $file")
        }
    }
}

function Test-LocalReference {
    param(
        [string]$Ref,
        [string]$SourceFile
    )

    if ([string]::IsNullOrWhiteSpace($Ref)) { return }
    if ($Ref.StartsWith("http://") -or $Ref.StartsWith("https://")) { return }
    if ($Ref.StartsWith("mailto:") -or $Ref.StartsWith("tel:")) { return }
    if ($Ref.StartsWith("javascript:") -or $Ref.StartsWith("data:")) { return }
    if ($Ref.StartsWith("#")) { return }

    $cleanRef = $Ref.Split("#")[0].Split("?")[0]
    if ([string]::IsNullOrWhiteSpace($cleanRef)) { return }

    $repoPrefix = "/ghost-in-the-models/"
    if ($cleanRef.StartsWith($repoPrefix)) {
        $cleanRef = $cleanRef.Substring($repoPrefix.Length)
    } elseif ($cleanRef.StartsWith("/")) {
        $cleanRef = $cleanRef.TrimStart("/")
    } else {
        $baseDir = Split-Path -Parent $SourceFile
        if ([string]::IsNullOrWhiteSpace($baseDir)) {
            $baseDir = "."
        }
        $resolved = [System.IO.Path]::GetFullPath((Join-Path $baseDir $cleanRef))
        if (-not (Test-Path -LiteralPath $resolved)) {
            $errors.Add("Broken reference in $SourceFile : $Ref")
        }
        return
    }

    $absolute = Join-Path $SiteRoot $cleanRef
    if (-not (Test-Path -LiteralPath $absolute)) {
        $errors.Add("Broken reference in $SourceFile : $Ref")
    }
}

$htmlFiles = $trackedFiles | Where-Object { $_.ToLower().EndsWith(".html") }
foreach ($htmlFile in $htmlFiles) {
    $raw = Get-Content -Raw -LiteralPath $htmlFile
    $matches = [regex]::Matches($raw, '(?:href|src)\s*=\s*"([^"]+)"', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    foreach ($m in $matches) {
        Test-LocalReference -Ref $m.Groups[1].Value -SourceFile $htmlFile
    }
}

if ($errors.Count -gt 0) {
    Write-Host "Validation failed with $($errors.Count) issue(s):" -ForegroundColor Red
    $errors | Sort-Object -Unique | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "Validation passed: branding, files, and references look good." -ForegroundColor Green

