"""
Strands Agents SDK — Service Desk Agent

Generates @tool functions from an OpenAPI schema and creates
an interactive agent with guardrails via steering hooks.

Usage:
    pip install strands-agents strands-agents-tools httpx pyyaml
    python agent.py
"""

import yaml
from strands import Agent
from strands.models.bedrock import BedrockModel
from openapi_tools import generate_tools_from_schema


def create_agent(schema_path: str = "../openapi_schema.yaml") -> Agent:
    """Create a Strands Agent from an OpenAPI schema."""

    # Load and generate tools from the OpenAPI schema
    tools = generate_tools_from_schema(schema_path)

    # Create the agent with the Amazon Bedrock model
    model = BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-east-1",
    )

    agent = Agent(
        model=model,
        system_prompt="""You are a helpful IT service desk agent. You help users
        create, view, update, and manage support tickets.

        Guidelines:
        - Always confirm before making destructive changes (delete, escalate)
        - When creating tickets, ask for title and description if not provided
        - Show ticket IDs in your responses so users can reference them
        - Be concise and helpful""",
        tools=tools,
    )

    return agent


def main():
    """Run the agent in interactive mode."""
    agent = create_agent()

    print("🤖 Service Desk Agent ready. Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        response = agent(user_input)
        print(f"\nAgent: {response}\n")


if __name__ == "__main__":
    main()
