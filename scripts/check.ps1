$ErrorActionPreference = "Stop"

$python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

Invoke-NativeCommand -FilePath $python -Arguments @("-m", "ruff", "check", ".")
Invoke-NativeCommand -FilePath $python -Arguments @("scripts/export_contract_schemas.py", "--check")
Invoke-NativeCommand -FilePath $python -Arguments @("scripts/validate_phase3_assets.py")
Invoke-NativeCommand -FilePath $python -Arguments @("scripts/build_rag_index.py", "--check")
Invoke-NativeCommand -FilePath $python -Arguments @("scripts/evaluate_mcp_tools.py")
Invoke-NativeCommand -FilePath $python -Arguments @(
    "-m", "pytest",
    "--cov=app", "--cov=peopleops_mcp", "--cov-report=term-missing", "--cov-fail-under=85"
)

Push-Location ui
try {
    $env:NODE_USE_SYSTEM_CA = "1"
    Invoke-NativeCommand -FilePath "npm" -Arguments @("ci")
    Invoke-NativeCommand -FilePath "npm" -Arguments @("run", "test")
    Invoke-NativeCommand -FilePath "npm" -Arguments @("run", "build")
}
finally {
    Pop-Location
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerArguments = @("build", "-t", "peopleops-assistant:local", ".")
    if ($env:PEOPLEOPS_DOCKER_TLS_INSPECTION -eq "1") {
        $dockerArguments = @(
            "build",
            "--build-arg", "NPM_CONFIG_STRICT_SSL=false",
            "--build-arg", "PIP_TRUSTED_HOST=pypi.org files.pythonhosted.org",
            "-t", "peopleops-assistant:local",
            "."
        )
    }
    Invoke-NativeCommand -FilePath "docker" -Arguments $dockerArguments
}
