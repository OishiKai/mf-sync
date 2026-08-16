# GCP infrastructure

This directory manages the production Money Forward infrastructure with Terraform.
Tracked files contain no project IDs, account addresses, credentials, secret values, or
Terraform state.

## Bootstrap

Create a dedicated Google Cloud project and an empty, private GCS state bucket first. Then
copy the local configuration templates:

```bash
cp infra/backend.hcl.example infra/backend.hcl
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

Fill both ignored files. Container image variables must use immutable `@sha256:` digests.
Set `terraform_operator` to the user, group, or service account that will operate Terraform.

Initialize the partial backend and validate the configuration:

```bash
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" \
  terraform -chdir=infra init -reconfigure -backend-config=backend.hcl
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
```

Use `import_existing = true` only when adopting the specifically named pre-existing resources
defined in `imports.tf`. Set it back to `false` after the first successful apply.

## Plan and apply

Use a short-lived access token and always review a saved plan before applying it:

```bash
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" \
  terraform -chdir=infra plan -out=reviewed.tfplan
terraform -chdir=infra show reviewed.tfplan
GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)" \
  terraform -chdir=infra apply reviewed.tfplan
```

Do not apply a plan that unexpectedly replaces or destroys the Cloud Run service, crawler job,
buckets, secrets, or service accounts.

## Managed resources and controls

- required Google Cloud APIs and continuous Artifact Registry scanning
- dedicated build, API, crawler, and scheduler service accounts
- removal of the basic Editor grant and disabling of default service accounts
- object-scoped data bucket access for the API and crawler
- private data and state buckets with uniform access, public access prevention, versioning,
  soft delete, and destroy protection
- a bucket-scoped Terraform operator role and state-object access
- Secret Manager containers and per-secret runtime accessors
- Cloud Run service `mf-sync`, Cloud Run job `mf-crawler`, and weekday JST scheduler
- Secret Manager and Cloud Storage Data Access audit logs
- API authentication/5xx and crawler-failure log metrics and alert policies

Secret values and secret versions are intentionally not managed by Terraform. Add values with
Secret Manager after applying the secret containers. A standalone project cannot enforce
organization policies such as service-account-key creation constraints; apply those policies at
the Google Cloud organization level when an organization is available.
