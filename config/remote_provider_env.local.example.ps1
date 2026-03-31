# Repo-local provider credentials for remote fetch runs.
# Copy this file to `config\remote_provider_env.local.ps1` and fill in your values.
# This local file is gitignored and is dot-sourced by `scripts\import_remote_provider_env.ps1`.

$env:ALPHAVANTAGE_API_KEY = ""
$env:SEC_CONTACT_EMAIL = ""

# Optional override. If left unset, the SEC fetcher will derive a compliant
# user agent from `SEC_CONTACT_EMAIL` as `MarketResearch_ML (<email>)`.
# $env:SEC_USER_AGENT = "MarketResearch_ML (your_email@example.com)"
