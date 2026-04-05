"""T006: Contract test for DynamoDB table schema (US2).

Verifies that the three DynamoDB tables exist in AWS with the correct
configuration: hash key, billing mode PAY_PER_REQUEST, SSE enabled.

Requires AWS_INTEGRATION=1 and real AWS credentials. ENVIRONMENT defaults to "prod".
"""
import os
import pytest
import boto3


def _skip_if_no_integration():
    if not os.environ.get("AWS_INTEGRATION"):
        pytest.skip("AWS_INTEGRATION env var not set — skipping real AWS test")


@pytest.fixture(scope="module")
def dynamodb_client():
    _skip_if_no_integration()
    return boto3.client("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))


@pytest.fixture(scope="module")
def environment():
    return os.environ.get("ENVIRONMENT", "prod")


def _describe_table(client, table_name):
    response = client.describe_table(TableName=table_name)
    return response["Table"]


class TestDynamoDBTableSchema:
    def test_varieties_table_exists_with_correct_hash_key(self, dynamodb_client, environment):
        table = _describe_table(dynamodb_client, f"coquito-varieties-{environment}")
        key_schema = {k["AttributeName"]: k["KeyType"] for k in table["KeySchema"]}
        assert key_schema.get("varietyId") == "HASH", f"Expected varietyId HASH key, got: {key_schema}"

    def test_batches_table_exists_with_correct_hash_key(self, dynamodb_client, environment):
        table = _describe_table(dynamodb_client, f"coquito-batches-{environment}")
        key_schema = {k["AttributeName"]: k["KeyType"] for k in table["KeySchema"]}
        assert key_schema.get("batchId") == "HASH", f"Expected batchId HASH key, got: {key_schema}"

    def test_requests_table_exists_with_correct_hash_key(self, dynamodb_client, environment):
        table = _describe_table(dynamodb_client, f"coquito-requests-{environment}")
        key_schema = {k["AttributeName"]: k["KeyType"] for k in table["KeySchema"]}
        assert key_schema.get("requestId") == "HASH", f"Expected requestId HASH key, got: {key_schema}"

    def test_all_tables_use_pay_per_request_billing(self, dynamodb_client, environment):
        for table_name in [
            f"coquito-varieties-{environment}",
            f"coquito-batches-{environment}",
            f"coquito-requests-{environment}",
        ]:
            table = _describe_table(dynamodb_client, table_name)
            billing = table.get("BillingModeSummary", {}).get("BillingMode")
            assert billing == "PAY_PER_REQUEST", f"{table_name}: expected PAY_PER_REQUEST, got: {billing}"

    def test_all_tables_have_sse_enabled(self, dynamodb_client, environment):
        for table_name in [
            f"coquito-varieties-{environment}",
            f"coquito-batches-{environment}",
            f"coquito-requests-{environment}",
        ]:
            table = _describe_table(dynamodb_client, table_name)
            sse_status = table.get("SSEDescription", {}).get("Status")
            assert sse_status == "ENABLED", f"{table_name}: expected SSE ENABLED, got: {sse_status}"
