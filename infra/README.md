# GCP infrastructure

This directory manages the production Money Forward infrastructure in
`moneyforward-sync-20260815` with Terraform.

## Authentication

The configuration does not store credentials. From the repository root, pass a
short-lived `gcloud` access token only to the current command:

```bash
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" terraform -chdir=infra init
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" terraform -chdir=infra plan
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" terraform -chdir=infra apply
```

The remote state is stored in `gs://moneyforward-sync-20260815-tfstate/mf-sync/`.
The state bucket has uniform bucket-level access, public access prevention, versioning,
soft delete, and Terraform destroy protection.

## Managed resources

- required Google Cloud APIs
- application service accounts and least-privilege IAM grants
- data and Terraform state buckets
- active Secret Manager secret containers and their accessors
- Cloud Run service `mf-sync`
- Cloud Run job `mf-crawler`
- Cloud Scheduler job `mf-crawler-daily`
- Artifact Registry repository used by Cloud Run source deployments

Secret values and secret versions are intentionally not managed by Terraform. The unused
legacy `mf-op-*` Secret Manager secrets are also intentionally outside this configuration.

Run `terraform plan` before every apply. A plan must never replace or destroy the Cloud Run
service, crawler job, buckets, secrets, or service accounts.
