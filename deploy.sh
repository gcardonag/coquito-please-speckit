#!/usr/bin/env bash
# deploy.sh — Build and deploy the full stack (backend → frontend → infra → S3 sync)
#
# Usage:
#   ./deploy.sh                  # full deploy (all steps)
#   ./deploy.sh --backend-only   # build & package Lambda artifacts only
#   ./deploy.sh --frontend-only  # build frontend, sync to S3, invalidate CloudFront
#   ./deploy.sh --infra-only     # terraform apply only (uses existing build artifacts)
#   ./deploy.sh --skip-build     # skip builds; run terraform + S3 sync with existing artifacts
#
# Requirements:
#   - Docker (for arm64 Lambda layer build)
#   - pnpm (for frontend build)
#   - terraform (for infrastructure)
#   - aws CLI, authenticated with sufficient permissions
#   - infra/terraform/prod.tfvars (copy from prod.tfvars.example and fill in values)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
INFRA_DIR="$REPO_ROOT/infra/terraform"
TFVARS="$INFRA_DIR/prod.tfvars"

# ---- Colour helpers ----
bold='\033[1m'
green='\033[0;32m'
yellow='\033[0;33m'
red='\033[0;31m'
reset='\033[0m'

step()  { echo -e "\n${bold}==> $*${reset}"; }
ok()    { echo -e "${green}    ✓ $*${reset}"; }
warn()  { echo -e "${yellow}    ⚠ $*${reset}"; }
die()   { echo -e "${red}ERROR: $*${reset}" >&2; exit 1; }

# ---- Parse flags ----
DO_BACKEND=true
DO_FRONTEND=true
DO_INFRA=true
DO_SYNC=true

for arg in "$@"; do
  case "$arg" in
    --backend-only)  DO_FRONTEND=false; DO_INFRA=false; DO_SYNC=false ;;
    --frontend-only) DO_BACKEND=false;  DO_INFRA=false ;;
    --infra-only)    DO_BACKEND=false;  DO_FRONTEND=false; DO_SYNC=false ;;
    --skip-build)    DO_BACKEND=false;  DO_FRONTEND=false ;;
    --help|-h)
      sed -n '3,15p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *) die "Unknown argument: $arg" ;;
  esac
done

# ---- Preflight checks ----
step "Preflight checks"

[[ "$DO_BACKEND" == true ]] && command -v docker &>/dev/null || { [[ "$DO_BACKEND" == false ]] || die "docker not found"; }
[[ "$DO_FRONTEND" == true ]] && command -v pnpm &>/dev/null || { [[ "$DO_FRONTEND" == false ]] || die "pnpm not found"; }
[[ "$DO_INFRA" == true || "$DO_SYNC" == true ]] && command -v terraform &>/dev/null || { [[ "$DO_INFRA" == false && "$DO_SYNC" == false ]] || die "terraform not found"; }
[[ "$DO_INFRA" == true || "$DO_SYNC" == true ]] && command -v aws &>/dev/null || { [[ "$DO_INFRA" == false && "$DO_SYNC" == false ]] || die "aws CLI not found"; }

if [[ "$DO_INFRA" == true ]]; then
  [[ -f "$TFVARS" ]] || die "Missing $TFVARS — copy prod.tfvars.example and fill in values"
fi

if [[ "$DO_BACKEND" == true ]]; then
  [[ -f "$BACKEND_DIR/requirements.txt" ]] || die "Missing backend/requirements.txt"
fi

ok "All preflight checks passed"

# ---- Step 1: Build backend ----
if [[ "$DO_BACKEND" == true ]]; then
  step "Building backend Lambda artifacts"
  bash "$BACKEND_DIR/scripts/build.sh"
  [[ -f "$BACKEND_DIR/lambda.zip" ]] || die "lambda.zip not produced"
  [[ -f "$BACKEND_DIR/layer.zip" ]]  || die "layer.zip not produced"
  ok "lambda.zip and layer.zip ready"
fi

# ---- Step 2: Build frontend ----
if [[ "$DO_FRONTEND" == true ]]; then
  step "Building frontend"
  (cd "$FRONTEND_DIR" && pnpm install --frozen-lockfile && pnpm build)
  [[ -d "$FRONTEND_DIR/dist" ]] || die "frontend/dist not produced"
  ok "frontend/dist ready ($(find "$FRONTEND_DIR/dist" -type f | wc -l | tr -d ' ') files)"
fi

# ---- Step 3: Terraform apply ----
if [[ "$DO_INFRA" == true ]]; then
  step "Running terraform init"
  (cd "$INFRA_DIR" && terraform init -upgrade -input=false)

  step "Running terraform apply"
  (cd "$INFRA_DIR" && terraform apply -var-file="prod.tfvars" -input=false -auto-approve)
  ok "Terraform apply complete"
fi

# ---- Gather Terraform outputs (needed for S3 sync + CloudFront invalidation) ----
if [[ "$DO_SYNC" == true || "$DO_FRONTEND" == true ]]; then
  step "Reading Terraform outputs"
  BUCKET_NAME=$(cd "$INFRA_DIR" && terraform output -raw s3_bucket_name 2>/dev/null) \
    || die "Could not read s3_bucket_name from Terraform outputs — has terraform apply been run?"
  CF_DIST_ID=$(cd "$INFRA_DIR" && terraform output -raw cloudfront_distribution_id 2>/dev/null) \
    || die "Could not read cloudfront_distribution_id from Terraform outputs"
  ok "S3 bucket:  $BUCKET_NAME"
  ok "CloudFront: $CF_DIST_ID"
fi

# ---- Step 4: Sync frontend to S3 ----
if [[ "$DO_SYNC" == true ]]; then
  [[ -d "$FRONTEND_DIR/dist" ]] || die "frontend/dist not found — run without --skip-build or --infra-only first"

  step "Syncing frontend to S3 (s3://$BUCKET_NAME)"
  aws s3 sync "$FRONTEND_DIR/dist/" "s3://$BUCKET_NAME/" \
    --delete \
    --cache-control "public,max-age=31536000,immutable" \
    --exclude "index.html"

  # index.html must not be cached so browsers always get the latest entry point
  aws s3 cp "$FRONTEND_DIR/dist/index.html" "s3://$BUCKET_NAME/index.html" \
    --cache-control "no-cache,no-store,must-revalidate" \
    --content-type "text/html"

  ok "S3 sync complete"

  step "Invalidating CloudFront cache ($CF_DIST_ID)"
  INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$CF_DIST_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)
  ok "Invalidation created: $INVALIDATION_ID"
fi

# ---- Done ----
echo ""
echo -e "${bold}${green}Deploy complete.${reset}"
if [[ "$DO_INFRA" == true ]]; then
  (cd "$INFRA_DIR" && terraform output frontend_url 2>/dev/null | xargs -I{} echo -e "  Frontend: {}" || true)
fi
