$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$dailyPost = Join-Path $PSScriptRoot 'daily-post.ps1'
$liveRepoRoot = 'W:\websites\sites\ghost-in-the-models'
$liveRotationPath = Join-Path $liveRepoRoot '.agents\rotation.json'

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
if (Compare-Object -ReferenceObject $before -DifferenceObject $after) {
    throw 'Dry-run preflight changed the repository.'
}

[pscustomobject]@{
    parser = 'passed'
    codexDryRun = 'passed'
    disabledGemini = 'passed'
    repositoryUnchanged = 'passed'
} | ConvertTo-Json
