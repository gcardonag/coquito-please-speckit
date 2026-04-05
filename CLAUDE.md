## Claude's Role
Read `.specify/memory/constitution.md` first. It is the authoritative source of truth for this project.
Everything in it is non-negotiable.

## SpecKit Commands
- `/speckit.specify` — generate spec
- `/speckit.plan` — generate plan
- `/speckit.tasks` — generate task list
- `/speckit.implement` — execute plan

## On Ambiguity
If a spec is missing, incomplete, or conflicts with the constitution — stop and ask
Do not infer. Do not proceed.

## Active Technologies
- TypeScript 5.x (frontend), Python 3.12 (backend Lambda) + Vite 5.x, pnpm 9.x, Prettier 3.x (frontend); boto3, AWS Lambda Powertools (backend) (001-coquito-request-app)
- DynamoDB (requests, batches, varieties); S3 (static assets — images, icons) (001-coquito-request-app)
- Python 3.12 (backend Lambda), TypeScript 5.x (frontend) + boto3, AWS Lambda Powertools (backend); Vite 5.x, pnpm 9.x, Prettier 3.x (frontend); Terraform hashicorp/aws v6.39.0 (infra) (002-aws-deploy-auth)
- DynamoDB (existing tables, unchanged); Cognito User Pool (new, user identity) (002-aws-deploy-auth)
- uv (Python package management)
- Python 3.12 (backend Lambda), TypeScript 5.x (frontend), HCL (Terraform) + boto3 (DynamoDB access), AWS Lambda Powertools (logging), hashicorp/aws ~> 6.39 (003-aws-website-storage)
- DynamoDB (PAY_PER_REQUEST, AWS owned key SSE), S3 (existing frontend bucket for media assets) (003-aws-website-storage)

## Recent Changes
- 001-coquito-request-app: Added TypeScript 5.x (frontend), Python 3.12 (backend Lambda) + Vite 5.x, pnpm 9.x, Prettier 3.x (frontend); boto3, AWS Lambda Powertools (backend)
