"""
OpenAPI Schema to Strands @tool Function Generator

Reads an OpenAPI 3.0 schema and generates callable tool functions
that the Strands Agent can use to invoke API operations.
"""

import json
import re
from typing import Any
import yaml
import httpx
from strands import tool


# Your backend API base URL
API_BASE_URL = "https://your-api.example.com"

# Pattern for safe parameter values (no path traversal)
SAFE_PARAM_PATTERN = re.compile(r"^[a-zA-Z0-9\-_.:@]+$")


def _sanitize_path_param(name: str, value: str) -> str:
    """Validate and sanitize a path parameter value."""
    value = str(value).strip()
    if ".." in value or "/" in value or not SAFE_PARAM_PATTERN.match(value):
        raise ValueError(f"Invalid path parameter '{name}': contains unsafe characters")
    return value


def generate_tools_from_schema(schema_path: str) -> list:
    """
    Parse an OpenAPI 3.0 schema and generate @tool-decorated functions.

    Args:
        schema_path: Path to the OpenAPI YAML file

    Returns:
        List of tool functions ready for Strands Agent
    """
    with open(schema_path, "r") as f:
        schema = yaml.safe_load(f)

    tools = []
    paths = schema.get("paths", {})

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                tool_fn = _create_tool_function(path, method, operation)
                tools.append(tool_fn)

    return tools


def _create_tool_function(path: str, method: str, operation: dict):
    """Create a single @tool function from an OpenAPI operation."""
    operation_id = operation.get("operationId", f"{method}_{path}")
    description = operation.get("description", operation.get("summary", ""))
    parameters = operation.get("parameters", [])
    has_body = "requestBody" in operation

    # Build parameter descriptions for the docstring
    param_docs = []
    for p in parameters:
        required = "required" if p.get("required") else "optional"
        param_docs.append(f"  {p['name']} ({required}): {p.get('description', '')}")

    if has_body:
        body_schema = (
            operation.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        body_props = body_schema.get("properties", {})
        required_fields = body_schema.get("required", [])
        for name, prop in body_props.items():
            req = "required" if name in required_fields else "optional"
            param_docs.append(f"  {name} ({req}): {prop.get('description', '')}")

    docstring = f"{description}\n\nParameters:\n" + "\n".join(param_docs)

    # Create the tool function dynamically
    @tool(name=operation_id, description=description)
    def api_tool(**kwargs) -> dict:
        """Dynamically generated API tool."""
        url = API_BASE_URL + path

        # Substitute path parameters
        for p in parameters:
            if p.get("in") == "path" and p["name"] in kwargs:
                safe_value = _sanitize_path_param(p["name"], kwargs.pop(p["name"]))
                url = url.replace(f"{{{p['name']}}}", safe_value)

        # Separate query params from body
        query_params = {}
        body = {}
        for p in parameters:
            if p.get("in") == "query" and p["name"] in kwargs:
                query_params[p["name"]] = kwargs.pop(p["name"])

        # Remaining kwargs go to request body
        if has_body:
            body = kwargs

        # Make the HTTP request
        with httpx.Client(timeout=30) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                params=query_params if query_params else None,
                json=body if body else None,
            )

        if response.status_code >= 400:
            return {"error": response.text, "status_code": response.status_code}

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"status_code": response.status_code, "body": response.text}

    # Override the docstring
    api_tool.__doc__ = docstring
    api_tool.__name__ = operation_id

    return api_tool
