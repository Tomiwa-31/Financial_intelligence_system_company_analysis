"""
gates/existence_gate.py
-----------------------
Level 2: Gate 1 — the first enforcement point in the pipeline.

The gate receives the web agent's raw output and makes a hard
binary decision: PASS or BLOCK.  The coordinator never advances
past this point without a verified company identity.

Sub-topic 1.4 — precondition enforcement.
The gate is intentionally dumb: it applies rules, it doesn't reason.
Reasoning lives in the agent.  Enforcement lives in the gate.
"""


class ExistenceGate:
    """
    Gate 1: Company existence check.

    Rules (all must pass):
      1. verified == True
      2. ticker is present and non-empty
      3. exchange is present and non-empty
      4. full_name is present and non-empty

    If any rule fails, the gate returns a BLOCK result with a reason
    the coordinator can log to the session and surface to the user.
    """

    REQUIRED_FIELDS = ["ticker", "exchange", "full_name"]

    def evaluate(self, agent_result: dict) -> dict:
        """
        Evaluate the web agent result.

        Returns:
            {
                "passed": bool,
                "reason": str | None,      # populated on failure
                "identity": dict | None    # populated on success
            }
        """
        print(f"[GATE 1] Evaluating existence check...")

        # Rule 1: agent must have set verified=True
        if not agent_result.get("verified", False):
            reason = agent_result.get("reason") or "Company could not be verified"
            print(f"[GATE 1] BLOCKED — {reason}")
            return {"passed": False, "reason": reason, "identity": None}

        # Rules 2-4: required fields must be present and non-empty
        missing = [
            f for f in self.REQUIRED_FIELDS
            if not agent_result.get(f)
        ]
        if missing:
            reason = f"Agent response missing required fields: {missing}"
            print(f"[GATE 1] BLOCKED — {reason}")
            return {"passed": False, "reason": reason, "identity": None}

        # All rules passed
        identity = {
            "ticker":    agent_result["ticker"].upper().strip(),
            "exchange":  agent_result["exchange"].upper().strip(),
            "full_name": agent_result["full_name"].strip(),
        }
        print(f"[GATE 1] PASSED — {identity['full_name']} "
              f"({identity['ticker']} / {identity['exchange']})")

        return {"passed": True, "reason": None, "identity": identity}