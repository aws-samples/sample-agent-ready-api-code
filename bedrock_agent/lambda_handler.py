"""
Amazon Bedrock Agent Action Group Lambda Handler

Routes requests from Amazon Bedrock Agents to your backend REST API.
The agent reads the OpenAPI schema, decides which operation to call,
extracts parameters, and invokes this Lambda with the operation details.
"""

import json
import os
import re
import urllib.request
import urllib.error
from urllib.parse import urlparse

# Your backend API base URL (set via environment variable)
API_BASE_URL = os.environ.get("API_BASE_URL", "https://your-api.example.com")


# Allowed path pattern — only alphanumeric, hyphens, underscores, slashes, and braces
SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9\-_/{}]+$")


def lambda_handler(event, context):
    """
    Entry point for Amazon Bedrock Agent Action Group invocations.

    Event structure:
    {
        "actionGroup": "ServiceDeskActions",
        "apiPath": "/tickets/{ticketId}",
        "httpMethod": "GET",
        "parameters": [{"name": "ticketId", "type": "string", "value": "TKT-1234"}],
        "requestBody": {"content": {"application/json": {"properties": [...]}}}
    }
    """
    api_path = event.get("apiPath", "")
    http_method = event.get("httpMethod", "GET")
    parameters = event.get("parameters", [])
    request_body = event.get("requestBody", {})

    # Validate apiPath to prevent SSRF
    if not api_path or not SAFE_PATH_PATTERN.match(api_path):
        return format_response(event, 400, {"error": f"Invalid apiPath: {api_path}"})

    # Ensure path doesn't contain traversal sequences
    if ".." in api_path or "//" in api_path:
        return format_response(event, 400, {"error": "Path traversal not allowed"})

    # Build the URL by substituting path parameters
    url = API_BASE_URL + api_path
    query_params = []

    for param in parameters:
        name = param["name"]
        value = param["value"]
        if f"{{{name}}}" in url:
            # Sanitize path parameter values
            if ".." in str(value) or "/" in str(value):
                return format_response(event, 400, {"error": f"Invalid parameter value: {name}"})
            # Path parameter — substitute in URL
            url = url.replace(f"{{{name}}}", value)
        else:
            # Query parameter
            query_params.append(f"{name}={value}")

    if query_params:
        url += "?" + "&".join(query_params)

    # Extract request body if present
    body = None
    if request_body and "content" in request_body:
        body_props = (
            request_body.get("content", {})
            .get("application/json", {})
            .get("properties", [])
        )
        body = {prop["name"]: prop["value"] for prop in body_props}

    # Make the HTTP request to your backend API
    try:
        response = make_request(url, http_method, body)
        return format_response(event, 200, response)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.read else str(e)
        return format_response(event, e.code, error_body)
    except Exception as e:
        return format_response(event, 500, {"error": str(e)})


ALLOWED_SCHEMES = {"https"}  # add "http" only if your backend genuinely needs it


def make_request(url, method, body=None):
    """Make an HTTP request to the backend API."""
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Disallowed URL scheme: {parsed.scheme!r}")

    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body else None

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 - scheme validated above
        return json.loads(resp.read().decode("utf-8"))


def format_response(event, status_code, body):
    """Format the response in the structure Amazon Bedrock Agents expects."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "apiPath": event.get("apiPath", ""),
            "httpMethod": event.get("httpMethod", ""),
            "httpStatusCode": status_code,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(body) if isinstance(body, dict) else body
                }
            },
        },
    }
