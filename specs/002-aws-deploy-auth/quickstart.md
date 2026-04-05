# Quickstart: AWS Deployment with Role-Based Authentication

**Branch**: `002-aws-deploy-auth`

---

## Prerequisites

- AWS CLI configured with credentials for the target account
- Terraform >= 1.6.0 installed
- pnpm >= 9.x installed
- Python 3.12 installed
- An existing Route53 hosted zone for `coquito.gcardona.me` (hosted zone ID needed)
- A valid email address to seed the first Chef account

---

## 1. Configure Variables

```bash
# Copy the example vars file
cp infra/terraform/prod.tfvars.example infra/terraform/prod.tfvars

# Edit required values:
#   hosted_zone_id = "Z1234567890ABCDEF"  ← your Route53 hosted zone ID
#   domain         = "coquito.gcardona.me"
#   region         = "us-east-1"
#   chef_seed_email = "chef@example.com"
vi infra/terraform/prod.tfvars
```

---

## 2. Initialize and Apply Terraform

```bash
cd infra/terraform
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars
```

> **Note**: First apply creates the ACM certificate and waits for DNS validation (may take 2–5 minutes). Terraform handles the validation CNAME records automatically.

After `apply` completes, capture the outputs:
```bash
terraform output -json > /tmp/coquito-infra-outputs.json
```

---

## 3. Build and Deploy the Frontend

```bash
cd frontend

# Set API URL from Terraform output
export VITE_API_URL=$(cat /tmp/coquito-infra-outputs.json | jq -r '.api_url.value')
export VITE_AUTH_URL=$(cat /tmp/coquito-infra-outputs.json | jq -r '.auth_url.value')
export VITE_COGNITO_CLIENT_ID=$(cat /tmp/coquito-infra-outputs.json | jq -r '.cognito_client_id.value')

pnpm install
pnpm build

# Deploy to S3
BUCKET=$(cat /tmp/coquito-infra-outputs.json | jq -r '.s3_bucket_name.value')
aws s3 sync dist/ s3://$BUCKET --delete --cache-control "max-age=31536000,public" \
  --exclude "index.html"
aws s3 cp dist/index.html s3://$BUCKET/index.html \
  --cache-control "no-cache,no-store,must-revalidate"

# Invalidate CloudFront cache
CF_ID=$(cat /tmp/coquito-infra-outputs.json | jq -r '.cloudfront_distribution_id.value')
aws cloudfront create-invalidation --distribution-id $CF_ID --paths "/*"
```

---

## 4. Deploy Backend Lambdas

```bash
cd backend

# Package each Lambda (Terraform creates the function; CI updates the code)
pip install -r requirements.txt -t dist/
cp -r src dist/
cd dist && zip -r ../lambda.zip . && cd ..

# The Lambda ARNs are available in Terraform outputs
# Terraform manages function creation; use AWS CLI for code updates:
FUNCTION_PREFIX="coquito"
for fn in auth-token-exchange auth-logout auth-authorizer; do
  aws lambda update-function-code \
    --function-name "${FUNCTION_PREFIX}-${fn}" \
    --zip-file fileb://lambda.zip
done
```

---

## 5. Seed the First Chef Account

```bash
POOL_ID=$(cat /tmp/coquito-infra-outputs.json | jq -r '.cognito_user_pool_id.value')
CHEF_EMAIL="chef@example.com"

# Create the user (passwordless; user will receive OTP on first login)
aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username $CHEF_EMAIL \
  --user-attributes Name=email,Value=$CHEF_EMAIL Name=email_verified,Value=true \
  --message-action SUPPRESS

# Add to chef group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $POOL_ID \
  --username $CHEF_EMAIL \
  --group-name chef
```

---

## 6. Verify Deployment

```bash
# Health check
curl -s https://api.coquito.gcardona.me/health | jq .
# Expected: { "status": "ok", "service": "coquito-api" }

# Frontend loads
curl -s -o /dev/null -w "%{http_code}" https://coquito.gcardona.me/
# Expected: 200

# Unauthenticated API call returns 401
curl -s -o /dev/null -w "%{http_code}" https://api.coquito.gcardona.me/api/v1/varieties
# Expected: 401
```

---

## 7. Provision an Authorized User (Chef Action)

Once the Chef is logged in:
1. Navigate to the user management section of the Chef dashboard.
2. Enter the customer's email address.
3. The system calls `POST /api/v1/users` (Chef-only) which creates the Cognito user and adds them to the `authorized-user` group.
4. The customer receives an email invitation and can log in via the public URL.

Alternatively, the Chef can use the AWS Console or CLI:
```bash
aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username customer@example.com \
  --user-attributes Name=email,Value=customer@example.com Name=email_verified,Value=true \
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $POOL_ID \
  --username customer@example.com \
  --group-name authorized-user
```

---

## Teardown

```bash
cd infra/terraform
# Empty S3 bucket first (Terraform cannot delete non-empty buckets)
BUCKET=$(terraform output -raw s3_bucket_name)
aws s3 rm s3://$BUCKET --recursive
terraform destroy -var-file=prod.tfvars
```
