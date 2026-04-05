"""T005: Contract test for static site availability (US1).

Verifies that the CloudFront-backed static site responds with HTTP 200
and serves HTML content. Requires FRONTEND_URL env var to be set.
"""
import os
import pytest
import urllib.request
import urllib.error


def test_static_site_returns_200_html():
    """Spec acceptance scenario 1: page loads for visitor with valid URL."""
    frontend_url = os.environ.get("FRONTEND_URL")
    if not frontend_url:
        pytest.skip("FRONTEND_URL env var not set — skipping live site test")

    req = urllib.request.Request(frontend_url, method="GET")
    with urllib.request.urlopen(req) as response:
        assert response.status == 200
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type, f"Expected text/html, got: {content_type}"
