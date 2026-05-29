# Security Policy

## Disclaimer

This project is provided as sample code accompanying the AWS Prescriptive Guidance pattern
*Design agent-ready APIs by using OpenAPI Specification with Amazon Bedrock and Strands Agents SDK*.
It is **not** intended for production use without additional security hardening. See
"Production Hardening Recommendations" below.

The architecture diagram for this sample lives in the published APG pattern, not in this repository.

## Reporting Vulnerabilities

If you discover a security vulnerability in this project, please report it by emailing
aws-security@amazon.com. Do not report security vulnerabilities through public GitHub issues.

## AWS Services Used

- **Amazon Bedrock** — foundation-model inference for both the Bedrock Agent (Approach A) and the Strands Agent (Approach B). The samples target `anthropic.claude-3-5-sonnet-20241022-v2:0`.
- **Amazon Bedrock Agents** — orchestrates the agent in Approach A via an Action Group.
- **AWS Lambda** — Action Group executor (`bedrock_agent/lambda_handler.py`).
- **Amazon S3** — stores the OpenAPI schema that the Bedrock Agent reads at runtime.
- **AWS Identity and Access Management (IAM)** — agent execution role + Lambda execution role. Example policies in `iam/`.

## Third-party dependencies

| Dependency | Where | Notes |
|------------|-------|-------|
| `pyyaml` | `schema_validator.py`, `strands_agent/openapi_tools.py` | Trusted YAML parser. The code uses `yaml.safe_load` only. |
| `httpx` | `strands_agent/openapi_tools.py` | HTTP client used by the Strands path. Verifies TLS by default. |
| `boto3` | `bedrock_agent/setup_agent.py` | AWS SDK. |
| `strands-agents`, `strands-agents-tools` | `strands_agent/agent.py` | Strands Agents SDK. Confirm the version pinned in `requirements.txt` is currently approved for use in your organization. |

## Prerequisites and Permissions

To deploy this solution, you need:

- An AWS account with permissions to create Bedrock Agents, AWS Lambda functions, IAM roles, and Amazon S3 objects.
- Amazon Bedrock model access enabled for `anthropic.claude-3-5-sonnet-20241022-v2:0` (or substitute Nova Pro).
- Python 3.11+, AWS CLI configured (`aws configure`).
- The least-privilege IAM policies provided in `iam/agent-role.json` and `iam/lambda-execution-role.json`.

## Known Security Considerations

This sample explicitly accepts the following trade-offs to remain readable as an APG companion. Each is something to harden before production use.

| Item | Category | Rationale |
|------|----------|-----------|
| Lambda 500 responses contain raw `str(e)` | Sample-grade error handling | The Action Group response includes the exception string for debuggability. In production, map exceptions to a structured `errorType` and avoid leaking stack-frame detail to the agent. |
| `API_BASE_URL` in a plain Lambda env var | Configuration only — not a secret | URLs are configuration. **However**, if you add a bearer token under the `bearerAuth` scheme defined in `openapi_schema.yaml`, that token must be retrieved from AWS Secrets Manager or AWS Systems Manager Parameter Store at runtime — not stored as a Lambda env var. |
| Lambda env vars use AWS-managed encryption | Default behavior | A customer-managed AWS KMS key is recommended for production workloads with regulatory or auditability requirements. |
| Architecture diagram lives in the APG guide, not this repo | Authoring choice | Reference the APG pattern for the architecture overview. |

## Production Hardening Recommendations

Before deploying this code in a production environment:

- **IAM**: Tighten the example policies in `iam/` further. Scope `bedrock:InvokeModel` to the specific foundation-model ARN, scope `lambda:InvokeFunction` to the specific Action Group Lambda ARN, and scope `s3:GetObject` to the specific schema object.
- **Encryption**:
  - Enable an AWS KMS customer-managed key for the Lambda function's environment variables.
  - Enable server-side encryption with AWS KMS on the S3 bucket that hosts the OpenAPI schema, plus a `DenyInsecureTransport` bucket policy that requires TLS.
  - Enable Amazon CloudWatch Logs encryption with AWS KMS for the Lambda function's log group.
- **Networking**: Run the Lambda inside a VPC if it must reach a private backend. Egress should be restricted via a VPC endpoint (Interface) for Amazon Bedrock and Amazon S3.
- **Logging**: Enable AWS CloudTrail (management + data events for the schema bucket), Amazon S3 server access logging on the schema bucket, and Amazon CloudWatch Logs subscriptions.
- **Secrets**: If the bearer token defined in `openapi_schema.yaml` is used, store it in AWS Secrets Manager and grant the Lambda role `secretsmanager:GetSecretValue` for the specific secret ARN.
- **URL scheme validation**: Ensure `make_request` in `bedrock_agent/lambda_handler.py` rejects any URL scheme other than `https`.
- **OpenAPI hardening**: Set realistic `maxItems` on every array response, define explicit error responses for 4xx and 5xx, and complete the `securitySchemes` block with the auth mechanism your backend actually uses.

## Resource Cleanup

See the `## Cleanup` section in `README.md` for the exact teardown commands.

## Generative AI considerations

- **Use case**: IT service desk agent. Not a high-risk or prohibited use case.
- **Model selection**: Anthropic Claude 3.5 Sonnet via Amazon Bedrock — pre-approved AWS-served foundation model.
- **Confirmation gates**: Destructive operations (`updateTicket`, `deleteTicket`, `escalateTicket`) require user confirmation via `x-requireConfirmation` (Bedrock Agents) or `ConfirmationHook` (Strands).
- **Rate limiting**: `RateLimitHook` available on the Strands consumer side to bound agent loops.
- **Prompt injection considerations**: The `apiPath` allowlist and per-parameter sanitization in both `lambda_handler.py` and `openapi_tools.py` neutralize the most common SSRF / path-traversal injection vectors that arrive via tool arguments.