"""
Setup script to create an Amazon Bedrock Agent with an Action Group.

Prerequisites:
  - OpenAPI schema uploaded to S3
  - Lambda function deployed (lambda_handler.py)
  - IAM roles created (see README)

Usage:
  python setup_agent.py \
    --schema-s3-uri s3://my-bucket/openapi_schema.yaml \
    --lambda-arn arn:aws:lambda:us-east-1:123456789:function:my-handler \
    --agent-role-arn arn:aws:iam::123456789:role/BedrockAgentRole
"""

import argparse
import json
import time
import boto3


def create_agent(agent_name, role_arn, model_id, instruction):
    """Create Amazon Bedrock Agent."""
    client = boto3.client("bedrock-agent")

    response = client.create_agent(
        agentName=agent_name,
        agentResourceRoleArn=role_arn,
        foundationModel=model_id,
        instruction=instruction,
    )

    agent_id = response["agent"]["agentId"]
    print(f"✅ Agent created: {agent_id}")
    return agent_id


def add_action_group(agent_id, schema_s3_uri, lambda_arn):
    """Attach an Action Group to the agent."""
    client = boto3.client("bedrock-agent")

    response = client.create_agent_action_group(
        agentId=agent_id,
        agentVersion="DRAFT",
        actionGroupName="ServiceDeskActions",
        actionGroupExecutor={"lambda": lambda_arn},
        apiSchema={"s3": {"s3BucketName": extract_bucket(schema_s3_uri),
                          "s3ObjectKey": extract_key(schema_s3_uri)}},
        description="Service desk operations: create, list, update, escalate tickets",
    )

    print(f"✅ Action Group created: {response['agentActionGroup']['actionGroupId']}")


def prepare_agent(agent_id):
    """Prepare the agent for testing."""
    client = boto3.client("bedrock-agent")
    client.prepare_agent(agentId=agent_id)
    print(f"✅ Agent prepared. Ready for testing.")


def extract_bucket(s3_uri):
    """Extract bucket name from s3://bucket/key."""
    return s3_uri.replace("s3://", "").split("/")[0]


def extract_key(s3_uri):
    """Extract object key from s3://bucket/key."""
    return "/".join(s3_uri.replace("s3://", "").split("/")[1:])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Amazon Bedrock Agent")
    parser.add_argument("--schema-s3-uri", required=True, help="S3 URI of OpenAPI schema")
    parser.add_argument("--lambda-arn", required=True, help="Lambda function ARN")
    parser.add_argument("--agent-role-arn", required=True, help="IAM role ARN for the agent")
    parser.add_argument("--model-id", default="us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    parser.add_argument("--agent-name", default="ServiceDeskAgent")
    args = parser.parse_args()

    instruction = """You are a helpful IT service desk agent. You help users create,
    view, update, and manage support tickets. Always confirm before making
    destructive changes. Be concise and helpful."""

    agent_id = create_agent(args.agent_name, args.agent_role_arn, args.model_id, instruction)
    add_action_group(agent_id, args.schema_s3_uri, args.lambda_arn)
    prepare_agent(agent_id)
