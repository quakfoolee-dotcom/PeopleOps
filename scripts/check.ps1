$ErrorActionPreference = "Stop"

$python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

& $python -m ruff check .
& $python -m pytest --cov=app --cov=peopleops_mcp --cov-report=term-missing --cov-fail-under=85

Push-Location ui
try {
    $env:NODE_USE_SYSTEM_CA = "1"
    npm ci
    npm run test
    npm run build
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
    & docker @dockerArguments
}
