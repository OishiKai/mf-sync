# Security policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's
private vulnerability reporting feature on the repository Security page and
include reproduction steps, affected versions, and the expected impact.

You should receive an initial response within seven days. Please allow time for
a fix and coordinated disclosure before publishing details.

## Sensitive data

Never include Money Forward credentials, TOTP seeds, API keys, Terraform state,
database snapshots, account names, holdings, balances, or production logs in an
issue, pull request, or test fixture. Revoke and rotate any credential that was
accidentally disclosed.
