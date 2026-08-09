param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,
    [string]$ExpectedEnvironment,
    [string]$ExpectedReleaseSha,
    [string]$ExpectedLlmProvider,
    [int]$DeadlineSeconds = 180,
    [string]$Output = "artifacts/deployment-smoke.json"
)

$ErrorActionPreference = "Stop"
$python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
$arguments = @(
    "scripts/smoke_deployment.py",
    "--base-url", $BaseUrl,
    "--deadline-seconds", $DeadlineSeconds,
    "--output", $Output
)
if ($ExpectedEnvironment) {
    $arguments += @("--expected-environment", $ExpectedEnvironment)
}
if ($ExpectedReleaseSha) {
    $arguments += @("--expected-release-sha", $ExpectedReleaseSha)
}
if ($ExpectedLlmProvider) {
    $arguments += @("--expected-llm-provider", $ExpectedLlmProvider)
}

& $python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Deployment smoke failed with exit code $LASTEXITCODE"
}
