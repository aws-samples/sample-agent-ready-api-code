# Agent-Ready API Code

Companion code for the APG guide: **Design agent-ready APIs by using OpenAPI Specification with Amazon Bedrock and Strands Agents SDK**

## Structure

```
agent-ready-api-code/
├── README.md                      # This file
├── openapi_schema.yaml            # Sample agent-ready OpenAPI schema (Service Desk API)
├── schema_validator.py            # Validates schema against 7 agent-readiness principles
├── requirements.txt               # Python dependencies
├── iam/                           # Least-privilege IAM policies
│   ├── agent-role.json            # Bedrock Agent execution role policy
│   └── lambda-execution-role.json # Lambda execution role policy
├── bedrock_agent/                 # Approach A: Amazon Bedrock Agents
│   ├── lambda_handler.py          # Action Group Lambda handler
│   └── setup_agent.py            # Script to create Amazon Bedrock Agent + Action Group
└── strands_agent/                 # Approach B: Strands Agents SDK
    ├── agent.py                   # Interactive Strands Agent
    ├── openapi_tools.py           # OpenAPI schema → @tool function generator
    └── hooks.py                   # Steering hooks (confirmation, rate limit, logging)
```

## Quick Start

### 1. Validate your schema

```bash
pip install pyyaml
python schema_validator.py openapi_schema.yaml
```

### 2. Approach A — Amazon Bedrock Agent

```bash
# 1. Create IAM roles using the example policies in iam/
#    - Agent role:  iam/agent-role.json  (BedrockAgentRole)
#    - Lambda role: iam/lambda-execution-role.json  (LambdaExecutionRole)
#    These are sample policies for demonstration purposes only.
#    Update them to match your environment and access requirements.
#    Replace REGION, 123456789012, and MODEL_ID with your actual values.
#    For MODEL_ID, use the foundation model you enabled in Amazon Bedrock
#    (e.g., anthropic.claude-3-5-sonnet-20241022-v2:0 or amazon.nova-pro-v1:0).

# 2. Deploy the Lambda function (lambda_handler.py) with the Lambda execution role
# 3. Upload openapi_schema.yaml to S3
# 4. Create the agent:
python bedrock_agent/setup_agent.py \
  --schema-s3-uri s3://my-bucket/openapi_schema.yaml \
  --lambda-arn arn:aws:lambda:us-east-1:123456789012:function:ServiceDeskHandler \
  --agent-role-arn arn:aws:iam::123456789012:role/BedrockAgentRole
```

### 3. Approach B — Strands Agent

```bash
pip install -r requirements.txt

# Run interactively
cd strands_agent
python agent.py
```

Then try:
```
You: Show me all open tickets
You: Create a ticket for "VPN not connecting" with high severity
You: Escalate TKT-1234 because it's been open for a week
```

## Prerequisites

- Python 3.11+
- AWS credentials configured (`aws configure`)
- Amazon Bedrock model access enabled (Claude 3.5 Sonnet or Nova Pro)
- A running backend API (or mock the responses for testing)

## Customizing for your API

1. Replace `openapi_schema.yaml` with your own OpenAPI 3.0 schema
2. Update `API_BASE_URL` in:
   - `bedrock_agent/lambda_handler.py`
   - `strands_agent/openapi_tools.py`
3. Run `python schema_validator.py your_schema.yaml` to check agent-readiness
4. Test with sample queries and iterate on descriptions

## Cleanup

To remove all resources deployed by following this guide:

1. Delete the Amazon Bedrock Agent and its Action Groups:
   ```bash
   aws bedrock-agent delete-agent --agent-id <AGENT_ID> --skip-resource-in-use-check
   ```
2. Delete the Lambda function:
   ```bash
   aws lambda delete-function --function-name ServiceDeskHandler
   ```
3. Delete the IAM roles created for the agent and Lambda execution.
4. Delete the OpenAPI schema object from S3 (and the bucket if it was created solely for this sample).