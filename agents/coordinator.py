"""
coordinator.py
--------------
The coordinator is the brain of the system.  It:
  - Owns and mutates the SessionState (1.7)
  - Runs the agentic loop that drives each pipeline stage (1.1)
  - Will spawn subagents in Levels 2–6 (1.2, 1.3)
  - Enforces gates before advancing (1.4)

Level 2 additions:
  - WebAgent spawned for company verification (1.2)
  - Context slice passed to WebAgent — not the full session (1.3)
  - ExistenceGate evaluates the result and hard-blocks on failure (1.4)
  - Stub _stub_verify_company replaced with real agent + gate
"""

import uuid
import json
from utils.session_state import SessionState, CompanyIdentity
from agents.web_agent import WebAgent
from gates.existence_gate import ExistenceGate


# ── Pipeline stage constants ─────────────────────────────────────────────────

STAGE_INIT               = "INIT"
STAGE_IDENTITY_VERIFIED  = "IDENTITY_VERIFIED"
STAGE_RETRIEVAL_COMPLETE = "RETRIEVAL_COMPLETE"
STAGE_NORMALIZED         = "NORMALIZED"
STAGE_ANALYSIS_COMPLETE  = "ANALYSIS_COMPLETE"
STAGE_REPORT_READY       = "REPORT_READY"
STAGE_ESCALATED          = "ESCALATED"


class CoordinatorAgent:
    """
    The coordinator runs a sequential pipeline loop.
    Each stage either completes (advancing state) or fails (halting
    with escalation or a blocked-gate message).

    The loop is the agentic loop (sub-topic 1.1):
      while not terminal:
          run current stage
          check gate
          advance or escalate
    """

    def __init__(self, company_input: str):
        self.session = SessionState(
            session_id=str(uuid.uuid4()),
            company=CompanyIdentity(raw_input=company_input),
        )
        print(f"\n{'='*60}")
        print(f"[COORDINATOR] Session started: {self.session.session_id}")
        print(f"[COORDINATOR] Company input  : '{company_input}'")
        print(f"{'='*60}\n")

    # ── Main agentic loop ────────────────────────────────────────────────────

    def run(self) -> dict:
        """
        Drive the full pipeline.  Each call to _run_stage advances the
        session by exactly one stage.  The loop halts when we reach a
        terminal state (REPORT_READY or ESCALATED).

        Sub-topic 1.1: this while-loop *is* the agentic loop.
        The coordinator doesn't know in advance how many iterations it
        will take — each stage can succeed, retry, or escalate.
        """
        terminal_stages = {STAGE_REPORT_READY, STAGE_ESCALATED}

        while self.session.stage not in terminal_stages:
            self._run_stage(self.session.stage)

        return self._finalize()

    def _run_stage(self, stage: str):
        """Dispatch to the handler for the current stage."""
        print(f"\n[COORDINATOR] ── Running stage: {stage} ──")

        dispatch = {
            STAGE_INIT:               self._stage_init,
            STAGE_IDENTITY_VERIFIED:  self._stage_retrieval,
            STAGE_RETRIEVAL_COMPLETE: self._stage_normalize,
            STAGE_NORMALIZED:         self._stage_analysis,
            STAGE_ANALYSIS_COMPLETE:  self._stage_report,
        }

        handler = dispatch.get(stage)
        if handler is None:
            raise RuntimeError(f"No handler for stage: {stage}")
        handler()

    # ── Stage handlers ───────────────────────────────────────────────────────

    def _stage_init(self):
        """
        Stage 1 — Gate 1: verify the company exists.
        Level 1: placeholder (auto-passes).
        Level 2: real web agent spawned here.

        Sub-topic 1.4 (gate) lives here — nothing advances without
        a verified company identity.
        """
        print("[COORDINATOR] Gate 1: checking company identity...")

        # ── LEVEL 2: real web agent + existence gate ─────────────────────────
        # 1.3 — coordinator builds a context slice; the agent receives ONLY
        #        what it needs, not the full session object
        context = {"raw_input": self.session.company.raw_input}

        # 1.2 — coordinator spawns the web agent as a subagent
        web_agent = WebAgent()
        agent_result = web_agent.verify_company(context)

        # 1.4 — existence gate makes the hard pass/fail decision
        gate = ExistenceGate()
        gate_result = gate.evaluate(agent_result)
        verified_identity = {
            "verified": gate_result["passed"],
            "reason":   gate_result["reason"],
            **(gate_result["identity"] or {}),
        }
        # ─────────────────────────────────────────────────────────────────────

        if not verified_identity["verified"]:
            # Gate 1 BLOCKS — pipeline halts here
            self.session.escalate(
                f"Company not found: {verified_identity['reason']}"
            )
            return

        # Populate company identity in session state
        self.session.company.verified  = True
        self.session.company.ticker    = verified_identity["ticker"]
        self.session.company.exchange  = verified_identity["exchange"]
        self.session.company.full_name = verified_identity["full_name"]

        self.session.transition(
            STAGE_IDENTITY_VERIFIED,
            f"Verified as {verified_identity['ticker']} on {verified_identity['exchange']}"
        )

    def _stage_retrieval(self):
        """
        Stage 2 — Parallel subagent spawn: web agent + doc extraction.
        Level 1: placeholder stubs.
        Level 3: real parallel spawning with context injection (1.2, 1.3, 1.6).
        """
        print("[COORDINATOR] Spawning retrieval subagents (stub)...")

        # Context slice — only what the retrieval agents need (1.3 preview)
        retrieval_context = self.session.context_slice(
            ["ticker", "exchange", "full_name"]
        )
        print(f"[COORDINATOR] Context slice passed to agents: {retrieval_context}")

        # ── LEVEL 3 PLACEHOLDER ─────────────────────────────────────────────
        self.session.retrieval.web_raw = self._stub_web_retrieval(retrieval_context)
        self.session.retrieval.doc_raw = self._stub_doc_retrieval(retrieval_context)
        # ────────────────────────────────────────────────────────────────────

        self.session.transition(
            STAGE_RETRIEVAL_COMPLETE,
            "Web and doc data retrieved (stubbed)"
        )

    def _stage_normalize(self):
        """
        Stage 3 — PostToolUse hook normalizes raw financial figures.
        Level 1: placeholder.
        Level 4: real hook layer (1.5).
        """
        print("[COORDINATOR] Running normalization hook (stub)...")

        # ── LEVEL 4 PLACEHOLDER ─────────────────────────────────────────────
        self.session.retrieval.normalized_financials = {
            "revenue_usd_millions": 394328,
            "net_income_usd_millions": 99803,
            "fiscal_year": "FY2023",
            "source": "stub",
        }
        self.session.retrieval.normalized = True
        # ────────────────────────────────────────────────────────────────────

        self.session.transition(
            STAGE_NORMALIZED,
            "Financials normalized (stubbed)"
        )

    def _stage_analysis(self):
        """
        Stage 4 — Gate 2 then financial agent (with fork in Level 6).
        Level 1: placeholder.
        Level 5: real gate + financial agent.
        Level 6: fork_session added.
        """
        print("[COORDINATOR] Gate 2: checking data quality before analysis...")

        if not self.session.retrieval.normalized:
            self.session.escalate("Data not normalized — analysis blocked")
            return

        print("[COORDINATOR] Gate 2 passed. Running analysis (stub)...")

        # ── LEVEL 5/6 PLACEHOLDER ───────────────────────────────────────────
        self.session.analysis.fork_a = {"lens": "growth", "summary": "stub result"}
        self.session.analysis.fork_b = {"lens": "risk",   "summary": "stub result"}
        self.session.analysis.selected = "fork_a"
        # ────────────────────────────────────────────────────────────────────

        self.session.transition(
            STAGE_ANALYSIS_COMPLETE,
            "Analysis complete (stubbed, fork_a selected)"
        )

    def _stage_report(self):
        """
        Stage 5 — Conflict check + report generation.
        Level 1: placeholder.
        Level 7: full conflict detection + structured report.
        """
        print("[COORDINATOR] Generating report (stub)...")

        selected = self.session.analysis.selected
        chosen   = (self.session.analysis.fork_a
                    if selected == "fork_a"
                    else self.session.analysis.fork_b)

        self.session.analysis.final_report = {
            "company": self.session.company.full_name,
            "ticker":  self.session.company.ticker,
            "financials": self.session.retrieval.normalized_financials,
            "analysis": chosen,
            "generated_at": self.session.snapshot()["history"][-1]["at"],
        }

        self.session.transition(STAGE_REPORT_READY, "Report assembled")

    # ── Finalize ─────────────────────────────────────────────────────────────

    def _finalize(self) -> dict:
        snap = self.session.snapshot()
        print(f"\n{'='*60}")
        if self.session.stage == STAGE_ESCALATED:
            print(f"[COORDINATOR] ⚠  Pipeline ESCALATED")
            print(f"[COORDINATOR]    Reason: {self.session.escalation_reason}")
        else:
            print(f"[COORDINATOR] ✓  Pipeline COMPLETE")
            print(f"[COORDINATOR]    Report ready for: "
                  f"{self.session.company.full_name} ({self.session.company.ticker})")
        print(f"{'='*60}\n")
        print("[SESSION SNAPSHOT]")
        print(json.dumps(snap, indent=2))
        return snap

    # ── Stubs (replaced level by level) ──────────────────────────────────────

    def _stub_verify_company(self, raw_input: str) -> dict:
        """
        Stub for Gate 1 company verification.
        Returns a hardcoded result so Level 1 runs end-to-end.
        Replaced in Level 2 by a real web agent call.
        """
        # Simulate: if input looks like nonsense, fail the gate
        if len(raw_input.strip()) < 2 or raw_input.strip().lower() in {"test", "xxx", "fake"}:
            return {
                "verified": False,
                "reason": f"'{raw_input}' not found in any exchange",
            }
        return {
            "verified": True,
            "ticker":    "AAPL",
            "exchange":  "NASDAQ",
            "full_name": "Apple Inc.",
            "reason":    None,
        }

    def _stub_web_retrieval(self, context: dict) -> dict:
        return {"ticker": context["ticker"], "price": 189.50, "source": "stub"}

    def _stub_doc_retrieval(self, context: dict) -> dict:
        return {"ticker": context["ticker"], "filing": "10-K 2023", "source": "stub"}