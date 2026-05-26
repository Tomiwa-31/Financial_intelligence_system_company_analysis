"""
web_agent.py
------------
Level 2: First real subagent. Receives a context slice from the
coordinator, makes a real Anthropic API call with a tool definition,
and returns a structured company identity result.

The agent is given one tool — company_lookup — which it must call
to return structured data.  We force tool use so the response is
always machine-readable, never free text.

Sub-topics demonstrated:
  1.2 — this class IS the subagent; coordinator spawns it
  1.3 — it receives only a context slice (ticker hint + raw name),
         not the full session object
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()


# ── Tool definition ───────────────────────────────────────────────────────────
# We give the agent exactly one tool.  Forcing tool_choice={"type": "any"}
# means the model MUST call it — no free-text escape hatch.

COMPANY_LOOKUP_TOOL = {
    "name": "company_lookup",
    "description": (
        "Look up whether a company exists on a major stock exchange. "
        "Return the canonical ticker symbol, exchange, and full legal name. "
        "If the company cannot be verified as a publicly listed entity, "
        "set verified=false and explain why in the reason field."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verified": {
                "type": "boolean",
                "description": "True if the company is a verified listed entity"
            },
            "ticker": {
                "type": "string",
                "description": "Canonical ticker symbol e.g. AAPL, MSFT, TSLA"
            },
            "exchange": {
                "type": "string",
                "description": "Exchange where the company is listed e.g. NASDAQ, NYSE, LSE"
            },
            "full_name": {
                "type": "string",
                "description": "Full legal company name e.g. Apple Inc."
            },
            "reason": {
                "type": "string",
                "description": "If verified=false, explain why. Otherwise null."
            }
        },
        "required": ["verified", "reason"]
    }
}


class WebAgent:
    """
    Subagent responsible for company identity verification.

    Receives:  context slice {"raw_input": str}
    Returns:   dict with verified, ticker, exchange, full_name, reason

    The coordinator spawns this agent and reads its output through
    the existence gate — it never touches the raw API response.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-haiku-4-5-20251001"

    def verify_company(self, context: dict) -> dict:
        """
        Main entry point called by the coordinator.

        context = {"raw_input": "Apple"} — only what the agent needs.
        Returns a clean dict the existence gate can evaluate.
        """
        raw_input = context.get("raw_input", "").strip()
        print(f"[WEB AGENT] Verifying company: '{raw_input}'")## a model training memory and not the live internet

        prompt = (
            f"A user wants financial analysis on: '{raw_input}'\n\n"
            f"Use the company_lookup tool to determine if this is a real, "
            f"publicly listed company on a major stock exchange.\n"
            f"Use your knowledge of global stock markets to verify.\n"
            f"If it's a well-known company, confirm it. "
            f"If it's ambiguous, pick the most likely publicly listed entity. "
            f"If it clearly doesn't exist or isn't publicly listed, set verified=false."
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            tools=[COMPANY_LOOKUP_TOOL],
            tool_choice={"type": "any"},   # force tool call — no free text
            messages=[{"role": "user", "content": prompt}]
        )

        return self._extract_tool_result(response)

    def _extract_tool_result(self, response) -> dict:
        """
        Pull the tool_use block out of the response.
        Since we forced tool_choice=any, there will always be one.
        """
        for block in response.content:
            if block.type == "tool_use" and block.name == "company_lookup":
                result = block.input
                print(f"[WEB AGENT] Result: verified={result.get('verified')} "
                      f"ticker={result.get('ticker')} "
                      f"exchange={result.get('exchange')}")
                return result

        # Fallback — should never happen with tool_choice=any
        print("[WEB AGENT] WARNING: No tool call found in response")
        return {
            "verified": False,
            "reason": "Agent did not return a tool call",
            "ticker": None,
            "exchange": None,
            "full_name": None,
        }