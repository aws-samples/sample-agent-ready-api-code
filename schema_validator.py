"""
Schema Validator — Checks agent-readiness of an OpenAPI schema

Validates your OpenAPI 3.0 schema against the 7 design principles
from the APG guide. Run this before deploying to an agent.

Usage:
    python schema_validator.py openapi_schema.yaml
"""

import sys
import yaml


def validate_schema(schema_path: str) -> list[dict]:
    """Validate an OpenAPI schema for agent-readiness."""
    with open(schema_path, "r") as f:
        schema = yaml.safe_load(f)

    issues = []

    # Check OpenAPI version
    version = schema.get("openapi", "")
    if not version.startswith("3.0"):
        issues.append({
            "severity": "ERROR",
            "rule": "OpenAPI Version",
            "message": f"Must be 3.0.x for Amazon Bedrock Agents. Found: {version}",
        })

    paths = schema.get("paths", {})
    operation_ids = []

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue

            location = f"{method.upper()} {path}"

            # Principle 2: operationId
            op_id = operation.get("operationId")
            if not op_id:
                issues.append({
                    "severity": "ERROR",
                    "rule": "Principle 2: operationId",
                    "message": f"{location} — missing operationId",
                })
            else:
                operation_ids.append(op_id)

            # Principle 1: description
            desc = operation.get("description", "")
            if not desc:
                issues.append({
                    "severity": "ERROR",
                    "rule": "Principle 1: Description",
                    "message": f"{location} — missing description",
                })
            elif len(desc) < 50:
                issues.append({
                    "severity": "WARNING",
                    "rule": "Principle 1: Description quality",
                    "message": f"{location} — description too short ({len(desc)} chars). Add when/when-not/requires/returns.",
                })

            # Principle 3: parameters
            for param in operation.get("parameters", []):
                if not param.get("description"):
                    issues.append({
                        "severity": "WARNING",
                        "rule": "Principle 3: Parameter description",
                        "message": f"{location} — parameter '{param['name']}' has no description",
                    })

            # Principle 5: confirmation for destructive ops
            if method in ("delete", "patch", "put"):
                has_confirm = operation.get("x-requireConfirmation")
                if method == "delete" and not has_confirm:
                    issues.append({
                        "severity": "WARNING",
                        "rule": "Principle 5: Confirmation",
                        "message": f"{location} — DELETE without x-requireConfirmation",
                    })

            # Principle 6: error responses
            responses = operation.get("responses", {})
            if "400" not in responses and "404" not in responses:
                issues.append({
                    "severity": "INFO",
                    "rule": "Principle 6: Error responses",
                    "message": f"{location} — no error responses defined (400/404)",
                })

    # Check for duplicate operationIds
    seen = set()
    for op_id in operation_ids:
        if op_id in seen:
            issues.append({
                "severity": "ERROR",
                "rule": "Principle 2: Unique operationId",
                "message": f"Duplicate operationId: {op_id}",
            })
        seen.add(op_id)

    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python schema_validator.py <schema.yaml>")
        sys.exit(1)

    schema_path = sys.argv[1]
    print(f"🔍 Validating: {schema_path}\n")

    issues = validate_schema(schema_path)

    if not issues:
        print("✅ Schema passes all agent-readiness checks!")
        return

    # Group by severity
    errors = [i for i in issues if i["severity"] == "ERROR"]
    warnings = [i for i in issues if i["severity"] == "WARNING"]
    infos = [i for i in issues if i["severity"] == "INFO"]

    for issue in errors:
        print(f"  ❌ [{issue['rule']}] {issue['message']}")
    for issue in warnings:
        print(f"  ⚠️  [{issue['rule']}] {issue['message']}")
    for issue in infos:
        print(f"  ℹ️  [{issue['rule']}] {issue['message']}")

    print(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")

    if errors:
        print("\n❌ Schema has errors — fix before deploying to an agent.")
        sys.exit(1)
    else:
        print("\n✅ No blocking errors. Review warnings for better agent behavior.")


if __name__ == "__main__":
    main()
