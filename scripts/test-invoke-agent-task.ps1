param([string]$DailyPostPath = (Join-Path $PSScriptRoot 'daily-post.ps1'))

$ErrorActionPreference = 'Stop'

# Load only the function under test: never execute the daily writer's preflight,
# git sync, agent selection, editorial review, or publishing-adjacent code.
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $DailyPostPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw "Daily writer parser errors: $parseErrors" }
$function = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq 'Invoke-AgentTask'
}, $true)
if (-not $function) { throw 'Invoke-AgentTask was not found.' }
. ([scriptblock]::Create($function.Extent.Text))

$fixtureRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('gitm-native-test-' + [guid]::NewGuid())
[void](New-Item -ItemType Directory -Path $fixtureRoot)
try {
    foreach ($expectedExit in @(0, 7)) {
        $caseRoot = Join-Path $fixtureRoot "exit-$expectedExit"
        [void](New-Item -ItemType Directory -Path $caseRoot)
        $fixture = Join-Path $caseRoot 'fixture.cmd'
        @(
            '@echo off'
            'echo fixture-stdout-before'
            'echo fixture-stderr-banner 1>&2'
            'echo fixture-stdout-after'
            "exit /b $expectedExit"
        ) | Set-Content -LiteralPath $fixture -Encoding ASCII

        $result = Invoke-AgentTask -AuthorKey 'claude' -AgentConfig @{
            Command = $env:ComSpec
            Args = @('/d', '/c', $fixture)
        } -Prompt 'synthetic prompt; no agent is launched' -LogsDirectory $caseRoot

        if ($result.ExitCode -ne $expectedExit) {
            throw "Expected native exit $expectedExit, got $($result.ExitCode)."
        }
        $transcript = Get-Content -LiteralPath $result.TranscriptPath -Raw
        foreach ($marker in @('fixture-stdout-before', 'fixture-stderr-banner', 'fixture-stdout-after')) {
            if (-not $transcript.Contains($marker)) {
                throw "Missing transcript marker: $marker (native exit $expectedExit)."
            }
        }
        if ($ErrorActionPreference -ne 'Stop') {
            throw 'Invocation did not restore ErrorActionPreference.'
        }
    }
    Write-Host 'Passed native stderr transcript and exit-code regression cases (0 and 7).'
}
finally {
    # This uniquely named temporary directory belongs only to this test.
    $resolvedFixture = [IO.Path]::GetFullPath($fixtureRoot)
    $tempPrefix = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (-not $resolvedFixture.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Fixture escaped temporary directory.' }
    Remove-Item -LiteralPath $resolvedFixture -Recurse -Force
}

