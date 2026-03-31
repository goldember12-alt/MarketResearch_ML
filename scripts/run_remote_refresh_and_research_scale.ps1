Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:RepoRoot = Split-Path -Parent $PSScriptRoot
$script:PythonExe = Join-Path $script:RepoRoot ".venv\Scripts\python.exe"
$script:ImportEnvScript = Join-Path $script:RepoRoot "scripts\import_remote_provider_env.ps1"
$script:LocalCredentialPath = Join-Path $script:RepoRoot "config\remote_provider_env.local.ps1"
$script:LogDir = Join-Path $script:RepoRoot ".cache\logs"
$timestamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$script:LogPath = Join-Path $script:LogDir "remote_refresh_research_scale_$timestamp.log"

New-Item -ItemType Directory -Path $script:LogDir -Force | Out-Null

function Write-LogLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $line = "[{0}] {1}" -f ([DateTime]::UtcNow.ToString("u")), $Message
    $line | Tee-Object -FilePath $script:LogPath -Append
}

function Write-ErrorBlock {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Context,

        [Parameter()]
        [System.Management.Automation.ErrorRecord]$ErrorRecord,

        [Parameter()]
        [string]$FallbackMessage = ""
    )

    Write-LogLine "ERROR BLOCK START [$Context]"
    if ($null -ne $ErrorRecord) {
        $exceptionType = if ($null -ne $ErrorRecord.Exception) {
            $ErrorRecord.Exception.GetType().FullName
        }
        else {
            "<no exception type>"
        }
        $message = if ($null -ne $ErrorRecord.Exception) {
            $ErrorRecord.Exception.Message
        }
        else {
            $ErrorRecord.ToString()
        }
        Write-LogLine "Exception type: $exceptionType"
        Write-LogLine "Exception message: $message"
        if (-not [string]::IsNullOrWhiteSpace($ErrorRecord.ScriptStackTrace)) {
            Write-LogLine "Script stack trace: $($ErrorRecord.ScriptStackTrace)"
        }
        if ($null -ne $ErrorRecord.InvocationInfo -and -not [string]::IsNullOrWhiteSpace($ErrorRecord.InvocationInfo.PositionMessage)) {
            Write-LogLine "Invocation position: $($ErrorRecord.InvocationInfo.PositionMessage)"
        }
        if ($null -ne $ErrorRecord.CategoryInfo) {
            Write-LogLine "Category info: $($ErrorRecord.CategoryInfo)"
        }
    }
    elseif (-not [string]::IsNullOrWhiteSpace($FallbackMessage)) {
        Write-LogLine "Exception message: $FallbackMessage"
    }
    Write-LogLine "ERROR BLOCK END [$Context]"
}

function Invoke-LoggedPythonModule {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ModuleName,

        [Parameter()]
        [string[]]$Arguments = @()
    )

    $renderedArgs = if ($Arguments.Count -gt 0) {
        $Arguments -join " "
    } else {
        ""
    }
    $renderedCommand = "python -m $ModuleName"
    if (-not [string]::IsNullOrWhiteSpace($renderedArgs)) {
        $renderedCommand = "$renderedCommand $renderedArgs"
    }
    Write-LogLine "Running: $script:PythonExe -m $ModuleName $renderedArgs".TrimEnd()
    & $script:PythonExe -m $ModuleName @Arguments 2>&1 | Tee-Object -FilePath $script:LogPath -Append
    $childExitCode = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    Write-LogLine "Child exit code for ${ModuleName}: $childExitCode"
    if ($childExitCode -ne 0) {
        Write-LogLine "Child command failed: $renderedCommand"
        throw "Command failed with exit code ${childExitCode}: $renderedCommand"
    }
    Write-LogLine "Completed: $ModuleName"
}

$originalDontWriteBytecode = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONDONTWRITEBYTECODE = "1"

try {
    Write-LogLine "Repo root: $script:RepoRoot"
    Write-LogLine "Log file: $script:LogPath"
    Write-LogLine "Execution mode: research_scale"
    if (Test-Path $script:ImportEnvScript) {
        . $script:ImportEnvScript
        Write-LogLine "Loaded repo-local provider environment script: $script:ImportEnvScript"
    }
    else {
        Write-LogLine "Repo-local provider environment script not found: $script:ImportEnvScript"
    }
    Write-LogLine "Expected local credential file: $script:LocalCredentialPath"
    Write-LogLine "Environment presence: ALPHAVANTAGE_API_KEY=$(-not [string]::IsNullOrWhiteSpace($env:ALPHAVANTAGE_API_KEY)); SEC_USER_AGENT=$(-not [string]::IsNullOrWhiteSpace($env:SEC_USER_AGENT)); SEC_CONTACT_EMAIL=$(-not [string]::IsNullOrWhiteSpace($env:SEC_CONTACT_EMAIL))"
    Write-LogLine "Using PYTHONDONTWRITEBYTECODE=1 for this run to avoid fresh __pycache__ creation."

    if (-not (Test-Path $script:PythonExe)) {
        throw "Repo-local interpreter not found at $script:PythonExe"
    }

    if ([string]::IsNullOrWhiteSpace($env:ALPHAVANTAGE_API_KEY)) {
        throw "ALPHAVANTAGE_API_KEY must be set before running this script."
    }

    if (
        [string]::IsNullOrWhiteSpace($env:SEC_USER_AGENT) -and
        [string]::IsNullOrWhiteSpace($env:SEC_CONTACT_EMAIL)
    ) {
        throw "Set SEC_USER_AGENT or SEC_CONTACT_EMAIL before running this script."
    }

    Invoke-LoggedPythonModule -ModuleName "src.run_fetch_remote_raw" -Arguments @(
        "--provider", "alphavantage_sec",
        "--execution-mode", "research_scale"
    )
    Invoke-LoggedPythonModule -ModuleName "src.run_data_ingestion" -Arguments @("--execution-mode", "research_scale")
    Invoke-LoggedPythonModule -ModuleName "src.run_panel_assembly" -Arguments @("--execution-mode", "research_scale")
    Invoke-LoggedPythonModule -ModuleName "src.run_feature_generation" -Arguments @("--execution-mode", "research_scale")
    Invoke-LoggedPythonModule -ModuleName "src.run_signal_generation" -Arguments @("--execution-mode", "research_scale")
    Invoke-LoggedPythonModule -ModuleName "src.run_backtest" -Arguments @("--execution-mode", "research_scale")
    Invoke-LoggedPythonModule -ModuleName "src.run_evaluation_report" -Arguments @("--execution-mode", "research_scale")
    Invoke-LoggedPythonModule -ModuleName "src.run_modeling_baselines" -Arguments @("--execution-mode", "research_scale")
    Invoke-LoggedPythonModule -ModuleName "src.run_model_backtest" -Arguments @("--execution-mode", "research_scale")
    Invoke-LoggedPythonModule -ModuleName "src.run_model_evaluation_report" -Arguments @("--execution-mode", "research_scale")

    Write-LogLine "All remote-refresh and downstream research_scale steps completed successfully."
    Write-Host "Log written to $script:LogPath"
}
catch {
    Write-ErrorBlock -Context "remote_refresh_and_research_scale" -ErrorRecord $_
    Write-Host "Log written to $script:LogPath"
    exit 1
}
finally {
    if ($null -eq $originalDontWriteBytecode) {
        Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONDONTWRITEBYTECODE = $originalDontWriteBytecode
    }
}
