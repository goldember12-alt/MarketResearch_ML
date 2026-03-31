Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:RepoRoot = Split-Path -Parent $PSScriptRoot
$script:LocalCredentialPath = Join-Path $script:RepoRoot "config\remote_provider_env.local.ps1"

if (Test-Path $script:LocalCredentialPath) {
    . $script:LocalCredentialPath
}
