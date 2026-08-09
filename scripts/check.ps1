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
Invoke-NativeCommand -FilePath $python -Arguments @("scripts/evaluate_workflows.py")
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

    $containerName = "peopleops-check-$([guid]::NewGuid().ToString('N'))"
    try {
        Invoke-NativeCommand -FilePath "docker" -Arguments @(
            "run", "--detach", "--name", $containerName,
            "--publish", "127.0.0.1::8000",
            "--env", "APP_RELEASE_SHA=local-check",
            "--env", "MCP_SERVER_URL=http://127.0.0.1:8000/mcp",
            "--env", "LLM_PROVIDER=deterministic",
            "--env", "LLM_MODEL=deterministic-grounded-v1",
            "peopleops-assistant:local"
        )
        $portLine = & docker port $containerName "8000/tcp"
        if ($LASTEXITCODE -ne 0 -or -not $portLine) {
            throw "Unable to discover the local smoke-test port."
        }
        $publishedPort = ($portLine | Select-Object -First 1).Split(":")[-1]
        Invoke-NativeCommand -FilePath $python -Arguments @(
            "scripts/smoke_deployment.py",
            "--base-url", "http://127.0.0.1:$publishedPort",
            "--expected-environment", "production",
            "--expected-release-sha", "local-check",
            "--expected-llm-provider", "deterministic",
            "--deadline-seconds", "90",
            "--output", "artifacts/local-container-smoke.json"
        )
    }
    catch {
        & docker logs $containerName
        throw
    }
    finally {
        & docker rm --force $containerName | Out-Null
    }
}
