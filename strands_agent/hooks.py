"""
Steering Hooks for Strands Agent

Reusable guardrails that intercept tool calls before execution.
Attach these to your agent for production safety.
"""

import time
from collections import defaultdict


class ConfirmationHook:
    """
    Requires user confirmation before executing destructive operations.

    Usage:
        hook = ConfirmationHook(operations=["deleteTicket", "escalateTicket", "updateTicket"])
    """

    def __init__(self, operations: list[str]):
        self.operations = set(operations)

    def __call__(self, tool_name: str, tool_input: dict, **kwargs) -> dict | None:
        """Return None to proceed, or a dict to block with a message."""
        if tool_name in self.operations:
            print(f"\n⚠️  Confirmation required for: {tool_name}")
            print(f"   Parameters: {tool_input}")
            response = input("   Proceed? (yes/no): ").strip().lower()
            if response not in ("yes", "y"):
                return {"blocked": True, "reason": "User declined confirmation"}
        return None


class RateLimitHook:
    """
    Rate limits tool calls to prevent runaway agent loops.

    Usage:
        hook = RateLimitHook(max_calls_per_minute=30)
    """

    def __init__(self, max_calls_per_minute: int = 30):
        self.max_calls = max_calls_per_minute
        self.call_times: list[float] = []

    def __call__(self, tool_name: str, tool_input: dict, **kwargs) -> dict | None:
        now = time.time()
        # Remove calls older than 60 seconds
        self.call_times = [t for t in self.call_times if now - t < 60]

        if len(self.call_times) >= self.max_calls:
            return {
                "blocked": True,
                "reason": f"Rate limit exceeded ({self.max_calls} calls/minute)",
            }

        self.call_times.append(now)
        return None


class LoggingHook:
    """
    Logs all tool calls for observability.

    Usage:
        hook = LoggingHook()
    """

    def __init__(self):
        self.log: list[dict] = []

    def __call__(self, tool_name: str, tool_input: dict, **kwargs) -> dict | None:
        entry = {
            "timestamp": time.time(),
            "tool": tool_name,
            "input": tool_input,
        }
        self.log.append(entry)
        print(f"📝 [{tool_name}] called with: {tool_input}")
        return None

    def get_log(self) -> list[dict]:
        return self.log
