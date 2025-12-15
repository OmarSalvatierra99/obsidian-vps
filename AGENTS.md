# Repository Guidelines

## Project Structure & Module Organization
- `scripts/` stores operational scripts for provisioning, backups, and maintenance; prefer action-based names (`provision-vps.sh`, `backup-vault.sh`).
- `infra/` holds IaC (Terraform/Ansible) for the VPS; keep environment-specific vars in `infra/env/<env>.tfvars` or `infra/inventory/<env>.yml`.
- `docs/` collects runbooks and architecture notes; add short, reproducible steps for any change that requires operator action.
- `tests/` mirrors the code layout (`tests/scripts/`, `tests/infra/`) and keeps fast, deterministic checks close to the related module.
- `.github/workflows/` is for CI once added; avoid embedding secrets—use repository/organization secrets instead.

## Build, Test, and Development Commands
- `make bootstrap` installs local tooling (shellcheck, ansible-lint, terraform, bats); run after cloning or when dependencies change.
- `make lint` runs format and static checks for shell and YAML/JSON; keep new linters wired into this target.
- `make test` executes automated tests under `tests/`; keep tests headless and idempotent.
- `make plan ENV=staging` shows proposed infra changes; always review before `make apply ENV=staging|prod`.
- If a Makefile is missing, add these targets or expose equivalent helpers in `scripts/` to keep the interface stable.

## Coding Style & Naming Conventions
- Shell: bash with `set -euo pipefail`, 2-space indents, functions in `lower_snake_case`, files in `kebab-case.sh`; guard destructive commands with prompts or `DRY_RUN`.
- YAML (Ansible/Terraform variables): 2-space indents, sorted keys where practical, no tabs; favor descriptive module/role names over abbreviations.
- Keep config samples as `.example` files; never commit real secrets.
- Run `shellcheck`/`ansible-lint` locally before opening a PR.

## Testing Guidelines
- Add a unit-style check for every new script (e.g., `bats` cases in `tests/scripts/`) and converge tests for roles/modules (e.g., `molecule` or `terraform plan` diffs) under `tests/infra/`.
- Name tests after the behavior under test (`backup_creates_archive.bats`, `provision_applies_base_packages.py`).
- For infra changes, capture a `make plan` snippet in the PR description and ensure plans are clean (no unintended drift).

## Commit & Pull Request Guidelines
- Git history is empty; start with Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`) in imperative mood and ≤72-char summaries.
- Squash noisy WIP commits before review. Reference issues when applicable (`#123`).
- PRs should describe intent, scope, test results (`make lint`, `make test`, `make plan`), and any rollout/backout notes; include screenshots or logs only when they clarify operator steps.

## Security & Configuration Tips
- Keep secrets out of the repo; store them in environment-specific secret managers or `.env` files listed in `.gitignore`.
- Use SSH keys with passphrases for VPS access; avoid embedding tokens in scripts. Rotate keys when team membership changes.
- Validate downloads and container images with checksums or digests, and pin tool versions in `Makefile`/`scripts/` to ensure reproducible runs.
