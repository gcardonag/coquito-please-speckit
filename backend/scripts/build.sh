#!/usr/bin/env bash
# Build Lambda artefacts for deployment.
#
# Outputs (both relative to backend/):
#   layer.zip   — Python dependencies, arm64 Amazon Linux 2023
#   lambda.zip  — Source code only (architecture-agnostic)
#
# Requirements: Docker (with linux/arm64 emulation or native arm64 host)
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Building dependency layer (arm64, Amazon Linux 2023)..."
docker run --rm \
  --platform linux/arm64 \
  --entrypoint /bin/bash \
  -v "$BACKEND_DIR":/workspace \
  -w /workspace \
  public.ecr.aws/lambda/python:3.12 \
  -c "
    dnf install -y zip > /dev/null &&
    pip install -r requirements.txt -t /tmp/python --quiet &&
    cd /tmp &&
    zip -r /workspace/layer.zip python/ -x '*.pyc' -x '*/__pycache__/*'
  "

echo "==> Building function zip (source only)..."
cd "$BACKEND_DIR"
rm -f lambda.zip
zip -r lambda.zip src/ -x '*.pyc' -x '*/__pycache__/*'

echo ""
echo "Done."
echo "  layer.zip:  $BACKEND_DIR/layer.zip"
echo "  lambda.zip: $BACKEND_DIR/lambda.zip"
