$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$dailyPost = Join-Path $PSScriptRoot 'daily-post.ps1'
$liveRepoRoot = 'W:\websites\sites\ghost-in-the-models'
$liveRotationPath = Join-Path $liveRepoRoot '.agents\rotation.json'
$failureLogPath = Join-Path $liveRepoRoot 'logs\daily-post.log'

function Get-OptionalFileState {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return 'absent'
    }

    $item = Get-Item -LiteralPath $Path
    $hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    return "present|$($item.Length)|$hash"
}

if (-not (Test-Path -LiteralPath $liveRotationPath)) {
    throw "Live rotation file not found: $liveRotationPath"
}

$tokens = $null
$parseErrors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
    $dailyPost,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -gt 0) {
    throw "daily-post.ps1 has parser errors: $($parseErrors -join '; ')"
}

$before = @(git -C $liveRepoRoot status --porcelain)
$failureLogBefore = Get-OptionalFileState -Path $failureLogPath
$disabledCursorRotationPath = [System.IO.Path]::GetTempFileName()

try {
    @{
        order = @('claude', 'gemini', 'codex')
        last_author = 'gemini'
    } | ConvertTo-Json | Set-Content -LiteralPath $disabledCursorRotationPath -Encoding UTF8

    $rotationOutput = & powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $dailyPost `
        -DryRun `
        -RepositoryPath $liveRepoRoot `
        -RotationPathOverride $disabledCursorRotationPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Disabled-cursor rotation preflight failed with exit code $LASTEXITCODE."
    }
    if (($rotationOutput -join "`n") -notmatch 'Author:\s+Codex') {
        throw "Disabled-cursor rotation did not advance to Codex: $($rotationOutput -join ' ')"
    }
}
finally {
    Remove-Item -LiteralPath $disabledCursorRotationPath -Force -ErrorAction SilentlyContinue
}

& powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $dailyPost `
    -DryRun `
    -Force codex `
    -RepositoryPath $liveRepoRoot `
    -RotationPathOverride $liveRotationPath | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Codex dry-run preflight failed with exit code $LASTEXITCODE."
}

$disabledOutput = & powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $dailyPost `
    -DryRun `
    -Force gemini `
    -RepositoryPath $liveRepoRoot `
    -RotationPathOverride $liveRotationPath 2>&1
if ($LASTEXITCODE -eq 0) {
    throw 'Disabled Gemini author unexpectedly passed dry-run preflight.'
}
if (($disabledOutput -join "`n") -notmatch "Author 'gemini' is disabled") {
    throw "Disabled Gemini failure was not explicit: $($disabledOutput -join ' ')"
}

$after = @(git -C $liveRepoRoot status --porcelain)
$failureLogAfter = Get-OptionalFileState -Path $failureLogPath
if (Compare-Object -ReferenceObject $before -DifferenceObject $after) {
    throw 'Dry-run preflight changed the repository.'
}
if ($failureLogAfter -ne $failureLogBefore) {
    throw 'Dry-run preflight changed logs\daily-post.log.'
}

[pscustomobject]@{
    parser = 'passed'
    codexDryRun = 'passed'
    disabledGemini = 'passed'
    disabledCursorRotation = 'passed'
    repositoryUnchanged = 'passed'
    failureLogUnchanged = 'passed'
} | ConvertTo-Json
