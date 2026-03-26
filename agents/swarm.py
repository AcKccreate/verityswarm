"""
VeritySwarm v2 — Truth Verification Swarm Engine
─────────────────────────────────────────────────
6 specialized agents · 2-round cross-pollinating iteration · Grok-primary synthesis
PDF export (reportlab) · Timestamped report history · Transparent reasoning chain

Agent pipeline:
  Round 1 (independent):   Researcher → Skeptic → BiasDetector
                           → SourceCrossChecker → ContextHistorian
  Round 2 (peer-informed): all 5 agents re-analyze with full peer context
  Synthesis:               FinalSynthesizer  [Grok → Gemini → Claude]

JSON contract per agent: { analysis, confidence (0-100), sources[], red_flags[], key_insights[] }
"""

import os
import re
import sys
import json
import textwrap
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# UTF-8 stdout/stderr — required on Windows for emoji output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Must be before any google import or the FutureWarning fires first
warnings.filterwarnings("ignore", category=FutureWarning)

# ─── .env loader — searches cwd + up to 3 parent directories ─────────────────
def _load_env() -> Path | None:
    """Load the nearest .env file, preferring python-dotenv if available."""
    try:
        from dotenv import load_dotenv, find_dotenv
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path, override=False)
        # Always also load the AnchorWithin central .env as supplemental
        # (fills keys missing from the local .env, e.g. XAI_API_KEY)
        central = Path(r"C:\Users\acase\AnchorWithin\.env")
        if central.exists() and str(central) != env_path:
            load_dotenv(str(central), override=False)
        if env_path:
            return Path(env_path)
        if central.exists():
            return central
    except ImportError:
        pass
    # Fallback: manual search without python-dotenv
    search = Path.cwd()
    for _ in range(4):  # cwd + up to 3 parents
        candidate = search / ".env"
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    if k not in os.environ:  # never overwrite real env vars
                        os.environ[k] = v.strip().strip('"').strip("'")
            return candidate
        search = search.parent
    # Last resort: try the AnchorWithin central .env directly
    central = Path(r"C:\Users\acase\AnchorWithin\.env")
    if central.exists():
        for line in central.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                if k not in os.environ:
                    os.environ[k] = v.strip().strip('"').strip("'")
        return central
    return None

_ENV_FILE = _load_env()
# ─────────────────────────────────────────────────────────────────────────────

import anthropic
from openai import OpenAI

try:
    import google.generativeai as genai
    _GEMINI_OK = True
except ImportError:
    _GEMINI_OK = False


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentOutput:
    agent_name:   str
    role:         str
    round:        int           # 1 = independent, 2 = peer-informed
    analysis:     str
    confidence:   int           # 0–100
    sources:      list[str] = field(default_factory=list)
    red_flags:    list[str] = field(default_factory=list)
    key_insights: list[str] = field(default_factory=list)
    error:        Optional[str] = None


@dataclass
class VerityReport:
    report_id:          str     # VR-YYYYMMDD-HHMMSS
    claim:              str
    verdict:            str     # TRUE | FALSE | PARTIALLY TRUE | UNVERIFIED | MISLEADING
    confidence:         int     # 0–100
    summary:            str
    synthesis:          str
    round1:             dict    # agent_name → AgentOutput
    round2:             dict    # agent_name → AgentOutput
    sources:            list[str]
    red_flags:          list[str]
    key_insights:       list[str]
    synthesizer_backend: str    # grok | gemini | claude
    generated_at:       str
    json_path:          str = ""
    pdf_path:           str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Agent prompts — Round 1 (independent analysis)
# ─────────────────────────────────────────────────────────────────────────────

_JSON_SCHEMA = (
    '{\n'
    '  "analysis":     "detailed prose analysis",\n'
    '  "confidence":   0-100,\n'
    '  "sources":      ["specific source 1", "specific source 2"],\n'
    '  "red_flags":    ["SHOUTING_SNAKE_CASE flags only if warranted"],\n'
    '  "key_insights": ["concise insight 1", "concise insight 2"]\n'
    '}'
)

AGENT_R1: dict[str, dict] = {

    "Researcher": {
        "role": "Evidence Researcher",
        "prompt": f"""You are the Researcher — the evidence spine of the VeritySwarm truth-verification swarm.

Your mandate: build the strongest factual record possible, for AND against the claim.
- Cite specific, real sources: academic journals, government bodies, established news orgs, primary documents.
- DO NOT invent sources. If uncertain, append [unverified] to the source name.
- Unpack statistics, definitions, and technical claims with precision.
- Confidence = your certainty that the evidence picture you've assembled is accurate (0–100).
- red_flags: uppercase snake_case strings for serious concerns only (e.g. NO_PEER_REVIEW, SINGLE_SOURCE, RETRACTED_STUDY).
- key_insights: distilled facts a reader must know to evaluate this claim.

Respond with ONLY valid JSON matching this schema exactly — no markdown, no preamble:
{_JSON_SCHEMA}""",
    },

    "Skeptic": {
        "role": "Adversarial Challenger",
        "prompt": f"""You are the Skeptic — the adversarial conscience of the VeritySwarm swarm.

Your mandate: attack the claim relentlessly. Find every weakness, gap, and counter-narrative.
- What evidence directly contradicts or severely complicates this claim?
- What crucial context is missing, minimized, or deliberately omitted?
- What alternative explanations or interpretations exist that the claim ignores?
- Has this claim been made before and later retracted or debunked?
- Confidence = your certainty that the skeptical case you've built is sound (0–100).
- red_flags: for logical fallacies, weasel words, missing controls, cherry-picked data.
- key_insights: the 2–3 strongest counter-points a rational person must acknowledge.

Respond with ONLY valid JSON matching this schema exactly — no markdown, no preamble:
{_JSON_SCHEMA}""",
    },

    "BiasDetector": {
        "role": "Bias & Framing Analyst",
        "prompt": f"""You are the Bias Detector — the framing forensics unit of the VeritySwarm swarm.

Your mandate: expose every layer of motivated reasoning, spin, and structural bias in this claim.
- Identify political, ideological, commercial, cultural, or institutional bias in how the claim is framed.
- Flag loaded language, emotionally charged phrasing, or false equivalencies in the claim itself.
- Who benefits — financially, politically, socially — if this claim is believed to be true?
- Who has historically pushed this claim and what were their incentives?
- Confidence = your certainty that your bias assessment is calibrated and well-supported (0–100).
- red_flags: POLITICAL_SPIN, CORPORATE_CAPTURE, MANUFACTURED_CONSENSUS, etc.
- key_insights: the 2–3 bias vectors that most distort how this claim is understood.

Respond with ONLY valid JSON matching this schema exactly — no markdown, no preamble:
{_JSON_SCHEMA}""",
    },

    "SourceCrossChecker": {
        "role": "Source Credibility Verifier",
        "prompt": f"""You are the Source Cross-Checker — the credibility auditor of the VeritySwarm swarm.

Your mandate: stress-test the source ecosystem around this claim.
- Identify the authoritative primary sources that speak to this claim (peer-reviewed, official, original data).
- Do independent sources converge on the same conclusion, or do they conflict?
- Assess the credibility tier of commonly cited sources: Tier 1 (primary/peer-reviewed) → Tier 4 (tabloid/anonymous).
- Red flags for source pollution: single-source dependency, known disinfo outlets, anonymous sourcing,
  pre-print-only evidence, outdated studies, conflict of interest in funding.
- Confidence = your certainty in the overall source quality around this claim (0–100).
- key_insights: what the most trustworthy sources actually say.

Respond with ONLY valid JSON matching this schema exactly — no markdown, no preamble:
{_JSON_SCHEMA}""",
    },

    "ContextHistorian": {
        "role": "Historical & Temporal Analyst",
        "prompt": f"""You are the Context Historian — the long memory of the VeritySwarm swarm.

Your mandate: place this claim in its full historical and temporal context.
- When and where did this claim originate? What was the original context?
- Has this exact claim (or a close variant) circulated before? When, and with what outcome?
- What historical events, movements, or paradigm shifts are relevant to evaluating it now?
- Is this claim more or less credible in 2026 than it was when it first appeared?
- Does it follow a known historical pattern of misinformation (e.g. recurring health myth,
  political propaganda cycle, corporate disinformation playbook)?
- Confidence = your certainty that the historical context you've provided is accurate (0–100).
- red_flags: RECURRING_MYTH, DEBUNKED_PREVIOUSLY, PROPAGANDA_PATTERN, ANACHRONISTIC_FRAMING.
- key_insights: what history tells us about whether this claim deserves credibility.

Respond with ONLY valid JSON matching this schema exactly — no markdown, no preamble:
{_JSON_SCHEMA}""",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Round 2 — peer-informed refinement prompt template
# ─────────────────────────────────────────────────────────────────────────────

_R2_TEMPLATE = """{r1_system}

─── ROUND 2 REFINEMENT INSTRUCTIONS ───
You have now seen what your four peer agents found in their independent Round 1 analyses.
Your task: refine your own analysis in light of peer findings.

Rules:
- If peers surfaced important evidence or context you missed, incorporate it.
- If peers made errors or overreached, challenge them explicitly.
- If your Round 1 analysis holds up under peer scrutiny, confirm it with greater precision.
- Do NOT simply repeat your Round 1 output verbatim — this round must add value.
- Update your confidence score up or down based on the fuller picture.
- Add new red_flags or key_insights that only become visible after seeing peer analyses.

PEER ANALYSES (Round 1):
{peer_context}

Your Round 1 output was:
{self_r1}

Now produce your refined Round 2 output.
Respond with ONLY valid JSON — no markdown, no preamble:
{schema}"""


# ─────────────────────────────────────────────────────────────────────────────
# Final Synthesizer — Grok's voice: direct, unflinching, anti-hype
# ─────────────────────────────────────────────────────────────────────────────

SYNTHESIZER_PROMPT = f"""You are the Final Synthesizer of the VeritySwarm truth-verification swarm.

You have received two rounds of analysis from five specialized agents:
Researcher, Skeptic, Bias Detector, Source Cross-Checker, and Context Historian.

Your mandate: deliver a definitive, high-integrity Verity Report.

Voice: Direct. Unflinching. Slightly rebellious against hype, spin, and bullshit.
- If the evidence is clear, say so plainly. Do not academically hedge what is obvious.
- If sources are weak or the claim is propaganda, name it.
- If truth is genuinely murky, say that too — with precision about WHY it's murky.
- No "on one hand, on the other hand" equivocation when one side dominates the evidence.
- Cite specific agent findings in your synthesis. Show your work.

Verdict: exactly one of  TRUE | FALSE | PARTIALLY TRUE | UNVERIFIED | MISLEADING
confidence: integer 0–100 (weight of total evidence, not just synthesis confidence)
summary: 2–3 sentences, no hedging, no filler — what a sharp reader needs to know
synthesis: 2–3 paragraphs of rigorous integrated reasoning, citing agent findings
Consolidate sources (deduplicated, max 12), red_flags, key_insights from all agents.

Respond with ONLY valid JSON — no markdown, no preamble:
{{
  "verdict":      "...",
  "confidence":   0-100,
  "summary":      "...",
  "synthesis":    "...",
  "sources":      ["..."],
  "red_flags":    ["..."],
  "key_insights": ["..."]
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# VeritySwarm coordinator
# ─────────────────────────────────────────────────────────────────────────────

class VeritySwarm:

    AGENT_ORDER = ("Researcher", "Skeptic", "BiasDetector", "SourceCrossChecker", "ContextHistorian")

    AGENT_ICONS = {
        "Researcher":        "🔍",
        "Skeptic":           "⚔️",
        "BiasDetector":      "⚖️",
        "SourceCrossChecker":"🔗",
        "ContextHistorian":  "📜",
    }

    def __init__(
        self,
        claude_model: str = "claude-sonnet-4-6",
        grok_model:   str = "grok-3",
        gemini_model: str = "gemini-2.0-flash",
        reports_dir:  str = "reports",
    ):
        self.claude_model = claude_model
        self.grok_model   = grok_model
        self.reports_dir  = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

        loaded_from = f" (from {_ENV_FILE})" if _ENV_FILE else " (no .env found — using system env)"
        backends_ok  = []
        backends_bad = []

        # ── Claude ───────────────────────────────────────────────────────
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            self._claude = anthropic.Anthropic(api_key=anthropic_key)
            backends_ok.append("Claude")
        else:
            self._claude = anthropic.Anthropic(api_key="MISSING")
            backends_bad.append("Claude (missing ANTHROPIC_API_KEY)")

        # ── Grok (xAI) ───────────────────────────────────────────────────
        grok_key = os.getenv("XAI_API_KEY", os.getenv("GROK_API_KEY", ""))
        if grok_key:
            self._grok = OpenAI(api_key=grok_key, base_url="https://api.x.ai/v1")
            backends_ok.append("Grok")
        else:
            self._grok = OpenAI(api_key="MISSING", base_url="https://api.x.ai/v1")
            backends_bad.append("Grok (missing XAI_API_KEY or GROK_API_KEY)")

        # ── Gemini ───────────────────────────────────────────────────────
        self._gemini = None
        if _GEMINI_OK:
            gkey = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
            if gkey:
                genai.configure(api_key=gkey)
                self._gemini = genai.GenerativeModel(gemini_model)
                backends_ok.append("Gemini")
            else:
                backends_bad.append("Gemini (missing GEMINI_API_KEY or GOOGLE_API_KEY)")
        else:
            backends_bad.append("Gemini (google-generativeai not installed)")

        # ── Startup banner ───────────────────────────────────────────────
        print(f"\n  VeritySwarm v2  ·  env{loaded_from}")
        if backends_ok:
            print(f"  Backends ready : {' · '.join(backends_ok)}")
        if backends_bad:
            print(f"  Backends missing: {' | '.join(backends_bad)}")
        if not backends_ok:
            print("  ERROR: No backends loaded. Check your .env keys.")
            sys.exit(1)
        if len(backends_ok) == 1:
            print(f"  WARNING: Only {backends_ok[0]} available — fallback chain limited.")
        print()

    # ── Low-level callers ──────────────────────────────────────────────────

    def _call_claude(self, system: str, user: str, max_tokens: int = 1400) -> str:
        resp = self._claude.messages.create(
            model=self.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text

    def _call_grok(self, system: str, user: str, max_tokens: int = 1600) -> str:
        resp = self._grok.chat.completions.create(
            model=self.grok_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content

    def _call_gemini(self, system: str, user: str) -> str:
        if not self._gemini:
            raise RuntimeError("Gemini not configured")
        resp = self._gemini.generate_content(f"{system}\n\n{user}")
        return resp.text

    def _call_with_fallback(self, system: str, user: str, prefer: str = "claude") -> tuple[str, str]:
        """Returns (raw_text, backend_name). Falls back Grok→Gemini→Claude or Claude→Gemini→Grok."""
        order = (
            [("grok", self._call_grok), ("gemini", self._call_gemini), ("claude", self._call_claude)]
            if prefer == "grok"
            else [("claude", self._call_claude), ("gemini", self._call_gemini), ("grok", self._call_grok)]
        )
        last_exc = None
        for name, fn in order:
            try:
                if name == "gemini" and not self._gemini:
                    continue
                return fn(system, user), name
            except Exception as exc:
                last_exc = exc
        raise RuntimeError(f"All backends failed. Last error: {last_exc}")

    # ── JSON parsing ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Extract and parse JSON from raw LLM output, tolerating markdown fences."""
        raw = raw.strip()
        # Strip markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
        # Find first { ... } block
        m = re.search(r"\{[\s\S]+\}", raw)
        if m:
            raw = m.group(0)
        return json.loads(raw)

    @staticmethod
    def _safe_int(val, default: int = 50) -> int:
        try:
            return max(0, min(100, int(val)))
        except (TypeError, ValueError):
            return default

    # ── Agent runners ─────────────────────────────────────────────────────

    def _run_r1_agent(self, name: str, claim: str) -> AgentOutput:
        cfg = AGENT_R1[name]
        try:
            raw, _ = self._call_with_fallback(cfg["prompt"], f"Claim to verify: {claim}")
            d = self._parse_json(raw)
            return AgentOutput(
                agent_name=name, role=cfg["role"], round=1,
                analysis=str(d.get("analysis", "")),
                confidence=self._safe_int(d.get("confidence", 50)),
                sources=list(d.get("sources", [])),
                red_flags=list(d.get("red_flags", [])),
                key_insights=list(d.get("key_insights", [])),
            )
        except Exception as exc:
            return AgentOutput(
                agent_name=name, role=cfg["role"], round=1,
                analysis=f"[Agent error: {exc}]",
                confidence=0, error=str(exc), red_flags=["AGENT_ERROR"],
            )

    def _run_r2_agent(self, name: str, claim: str, r1_all: dict) -> AgentOutput:
        """Round 2: agent refines its analysis having seen all peers' Round 1 outputs."""
        cfg = AGENT_R1[name]
        self_r1 = r1_all[name]

        peer_lines = []
        for peer_name, peer_out in r1_all.items():
            if peer_name == name:
                continue
            peer_lines.append(
                f"  [{peer_name} — {peer_out.role}]\n"
                f"  Analysis: {peer_out.analysis[:600]}{'...' if len(peer_out.analysis) > 600 else ''}\n"
                f"  Confidence: {peer_out.confidence}/100\n"
                f"  Key Insights: {'; '.join(peer_out.key_insights[:3])}\n"
                f"  Red Flags: {', '.join(peer_out.red_flags[:3]) or 'none'}\n"
            )
        peer_context = "\n".join(peer_lines)

        self_summary = json.dumps({
            "analysis":     self_r1.analysis[:500],
            "confidence":   self_r1.confidence,
            "key_insights": self_r1.key_insights,
            "red_flags":    self_r1.red_flags,
        }, indent=2)

        system = _R2_TEMPLATE.format(
            r1_system=cfg["prompt"],
            peer_context=peer_context,
            self_r1=self_summary,
            schema=_JSON_SCHEMA,
        )

        try:
            raw, _ = self._call_with_fallback(system, f"Claim: {claim}\n\nProduce your Round 2 refined analysis.")
            d = self._parse_json(raw)
            return AgentOutput(
                agent_name=name, role=cfg["role"], round=2,
                analysis=str(d.get("analysis", "")),
                confidence=self._safe_int(d.get("confidence", self_r1.confidence)),
                sources=list(d.get("sources", self_r1.sources)),
                red_flags=list(d.get("red_flags", self_r1.red_flags)),
                key_insights=list(d.get("key_insights", self_r1.key_insights)),
            )
        except Exception as exc:
            # Degrade gracefully — return R1 output tagged as R2 with error note
            return AgentOutput(
                agent_name=name, role=cfg["role"], round=2,
                analysis=f"{self_r1.analysis}\n\n[Round 2 refinement failed: {exc}]",
                confidence=self_r1.confidence,
                sources=self_r1.sources,
                red_flags=self_r1.red_flags + ["R2_DEGRADED"],
                key_insights=self_r1.key_insights,
                error=str(exc),
            )

    # ── Synthesis ─────────────────────────────────────────────────────────

    def _build_synthesis_context(self, claim: str, r1: dict, r2: dict) -> str:
        lines = [f"CLAIM: {claim}\n"]
        for rnd, results in (("1 (Independent)", r1), ("2 (Peer-Refined)", r2)):
            lines.append(f"{'='*60}")
            lines.append(f"ROUND {rnd}")
            lines.append(f"{'='*60}")
            for name, out in results.items():
                lines.append(f"\n── {name} ({out.role})  confidence={out.confidence}/100")
                lines.append(f"Analysis: {out.analysis}")
                if out.sources:
                    lines.append(f"Sources:  {' | '.join(out.sources[:4])}")
                if out.key_insights:
                    lines.append(f"Insights: {' | '.join(out.key_insights[:3])}")
                if out.red_flags:
                    lines.append(f"Flags:    {', '.join(out.red_flags)}")
            lines.append("")
        return "\n".join(lines)

    def _synthesize(self, claim: str, r1: dict, r2: dict) -> tuple[dict, str]:
        """Returns (synthesis_dict, backend_name). Fallback chain: Grok → Gemini → Claude."""
        context = self._build_synthesis_context(claim, r1, r2)
        try:
            raw = self._call_grok(SYNTHESIZER_PROMPT, context, max_tokens=1800)
            return self._parse_json(raw), "grok"
        except Exception as grok_err:
            try:
                raw = self._call_gemini(SYNTHESIZER_PROMPT, context)
                return self._parse_json(raw), "gemini"
            except Exception:
                try:
                    raw = self._call_claude(SYNTHESIZER_PROMPT, context, max_tokens=1800)
                    return self._parse_json(raw), "claude"
                except Exception as claude_err:
                    return {
                        "verdict": "UNVERIFIED", "confidence": 0,
                        "summary": f"Synthesis unavailable. Grok: {grok_err}; Claude: {claude_err}",
                        "synthesis": "", "sources": [], "red_flags": ["SYNTHESIS_ERROR"],
                        "key_insights": [],
                    }, "none"

    # ── Persistence ───────────────────────────────────────────────────────

    def _report_to_dict(self, report: VerityReport) -> dict:
        def out_dict(o: AgentOutput) -> dict:
            return {
                "agent": o.agent_name, "role": o.role, "round": o.round,
                "analysis": o.analysis, "confidence": o.confidence,
                "sources": o.sources, "red_flags": o.red_flags,
                "key_insights": o.key_insights,
                **({"error": o.error} if o.error else {}),
            }
        return {
            "report_id": report.report_id,
            "claim": report.claim,
            "verdict": report.verdict,
            "confidence": report.confidence,
            "summary": report.summary,
            "synthesis": report.synthesis,
            "round1": {k: out_dict(v) for k, v in report.round1.items()},
            "round2": {k: out_dict(v) for k, v in report.round2.items()},
            "sources": report.sources,
            "red_flags": report.red_flags,
            "key_insights": report.key_insights,
            "synthesizer_backend": report.synthesizer_backend,
            "generated_at": report.generated_at,
            "pdf_path": report.pdf_path,
        }

    def _save_json(self, report: VerityReport) -> str:
        slug = re.sub(r"[^\w\s-]", "", report.claim.lower())[:48].strip().replace(" ", "_")
        fname = self.reports_dir / f"{report.report_id}_{slug}.json"
        with open(fname, "w", encoding="utf-8") as fh:
            json.dump(self._report_to_dict(report), fh, indent=2, ensure_ascii=False)
        # Always overwrite the convenience symlink
        latest = self.reports_dir / "verity_report_latest.json"
        with open(latest, "w", encoding="utf-8") as fh:
            json.dump(self._report_to_dict(report), fh, indent=2, ensure_ascii=False)
        return str(fname)

    # ── PDF export ────────────────────────────────────────────────────────

    def export_pdf(self, report: VerityReport) -> str:
        """
        Generate a dark-themed Verity Report PDF using reportlab.
        Returns the PDF file path, or '' if reportlab is not installed.

        pip install reportlab
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.colors import HexColor, white
            from reportlab.lib.units import mm
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table,
                TableStyle, HRFlowable, KeepTogether,
            )
        except ImportError:
            print("  [PDF] reportlab not installed — skipping. Run: pip install reportlab")
            return ""

        # ── Palette ──────────────────────────────────────────────────────
        BG      = HexColor("#07070f")
        CARD    = HexColor("#11112a")
        BORDER  = HexColor("#1e1e42")
        GREEN   = HexColor("#00e5a0")
        RED     = HexColor("#f87171")
        YELLOW  = HexColor("#fbbf24")
        ORANGE  = HexColor("#fb923c")
        BLUE    = HexColor("#4f8ef7")
        PURPLE  = HexColor("#8b5cf6")
        MUTED   = HexColor("#6b7a99")
        TEXT    = HexColor("#dde3f0")
        WHITE   = HexColor("#ffffff")

        VERDICT_C = {
            "TRUE": GREEN, "FALSE": RED, "PARTIALLY TRUE": YELLOW,
            "MISLEADING": ORANGE, "UNVERIFIED": MUTED,
        }.get(report.verdict, MUTED)

        AGENT_C = {
            "Researcher": GREEN, "Skeptic": RED, "BiasDetector": YELLOW,
            "SourceCrossChecker": PURPLE, "ContextHistorian": BLUE,
        }

        PW, PH = A4
        CONTENT_W = PW - 40 * mm

        def page_bg(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(BG)
            canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
            canvas.restoreState()

        # ── Style factory ────────────────────────────────────────────────
        _n = 0
        def S(base="Helvetica", size=9, color=TEXT, bold=False, leading=None,
               align=TA_LEFT, space_after=3, space_before=0) -> ParagraphStyle:
            nonlocal _n
            _n += 1
            return ParagraphStyle(
                f"s{_n}", fontName="Helvetica-Bold" if bold else base,
                fontSize=size, textColor=color,
                leading=leading or max(size + 4, 12),
                alignment=align, spaceAfter=space_after, spaceBefore=space_before,
            )

        def card(content_rows: list, col_widths=None, bg=CARD, border=BORDER) -> Table:
            t = Table(content_rows, colWidths=col_widths or [CONTENT_W])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), bg),
                ("BOX",           (0, 0), (-1, -1), 0.75, border),
                ("TOPPADDING",    (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING",   (0, 0), (-1, -1), 11),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 11),
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ]))
            return t

        def conf_bar(pct: int) -> Table:
            fill = max(1, CONTENT_W * pct / 100)
            rest = max(1, CONTENT_W - fill)
            t = Table([[" ", " "]], colWidths=[fill, rest])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (0, 0), GREEN),
                ("BACKGROUND",    (1, 0), (1, 0), BORDER),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ]))
            return t

        # ── Build story ──────────────────────────────────────────────────
        story = []

        # Header
        story.append(Paragraph("VERITY REPORT", S(size=20, color=WHITE, bold=True,
                                                   leading=24, space_after=2)))
        story.append(Paragraph(
            f"{report.report_id}  ·  {report.generated_at}  ·  "
            f"Synthesized by {report.synthesizer_backend.upper()}",
            S(size=8, color=MUTED, space_after=10),
        ))
        story.append(HRFlowable(width="100%", thickness=0.75, color=BORDER, spaceAfter=10))

        # Claim
        story.append(Paragraph("CLAIM", S(size=7, color=GREEN, bold=True, space_after=4)))
        story.append(card([[
            Paragraph(f'"{report.claim}"', S(size=11, color=WHITE, bold=True, leading=16))
        ]]))
        story.append(Spacer(1, 8))

        # Verdict + Confidence
        verdict_cell = [
            Paragraph("VERDICT", S(size=7, color=GREEN, bold=True, space_after=2)),
            Paragraph(report.verdict, S(size=15, color=VERDICT_C, bold=True, leading=20)),
        ]
        score_cell = [
            Paragraph("CONFIDENCE", S(size=7, color=GREEN, bold=True, space_after=2)),
            Paragraph(f"{report.confidence} / 100",
                      S(size=13, color=WHITE, bold=True, leading=18)),
        ]
        vc = Table([[verdict_cell, score_cell]],
                   colWidths=[CONTENT_W * 0.4, CONTENT_W * 0.6])
        vc.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), CARD),
            ("BOX",           (0, 0), (-1, -1), 0.75, BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 11),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 11),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(vc)
        story.append(Spacer(1, 4))
        story.append(conf_bar(report.confidence))
        story.append(Spacer(1, 10))

        # Summary
        story.append(Paragraph("SUMMARY", S(size=7, color=GREEN, bold=True, space_after=4)))
        story.append(card([[Paragraph(report.summary, S(size=9, color=TEXT, leading=14))]]))
        story.append(Spacer(1, 8))

        # Synthesis
        if report.synthesis:
            story.append(Paragraph("SYNTHESIS", S(size=7, color=GREEN, bold=True, space_after=4)))
            story.append(card(
                [[Paragraph(report.synthesis, S(size=9, color=TEXT, leading=14))]],
                bg=HexColor("#0b1a14"), border=HexColor("#1a3d2b"),
            ))
            story.append(Spacer(1, 10))

        # Reasoning chain — Rounds 1 & 2
        story.append(HRFlowable(width="100%", thickness=0.75, color=BORDER, spaceAfter=8))
        story.append(Paragraph("REASONING CHAIN", S(size=12, color=WHITE, bold=True,
                                                     space_after=6, space_before=4)))

        for rnd_label, rnd_data in (("Round 1 — Independent Analysis", report.round1),
                                     ("Round 2 — Peer-Refined", report.round2)):
            if not rnd_data:
                continue
            story.append(Paragraph(rnd_label, S(size=8, color=MUTED, bold=True,
                                                  space_after=5, space_before=8)))
            for aname, aout in rnd_data.items():
                ac = AGENT_C.get(aname, BLUE)
                rows = [
                    # Header row
                    [Paragraph(f"{aname}  ·  {aout.role}", S(size=9, color=ac, bold=True)),
                     Paragraph(f"Confidence: {aout.confidence}/100",
                                S(size=8, color=MUTED, align=TA_LEFT))],
                    # Analysis
                    [Paragraph(aout.analysis, S(size=8, color=TEXT, leading=13)), ""],
                ]
                if aout.key_insights:
                    rows.append([
                        Paragraph("Insights: " + "  ·  ".join(aout.key_insights[:3]),
                                   S(size=7, color=HexColor("#8899bb"), leading=11)), ""
                    ])
                if aout.red_flags:
                    rows.append([
                        Paragraph("Flags: " + "  ·  ".join(aout.red_flags[:4]),
                                   S(size=7, color=RED, leading=11)), ""
                    ])

                n_rows = len(rows)
                agent_t = Table(rows, colWidths=[CONTENT_W * 0.72, CONTENT_W * 0.28])
                spans = [("SPAN", (0, i), (1, i)) for i in range(1, n_rows)]
                agent_t.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, -1), CARD),
                    ("BOX",           (0, 0), (-1, -1), 0.75, BORDER),
                    ("LINEBELOW",     (0, 0), (-1, 0), 0.5, BORDER),
                    ("TOPPADDING",    (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
                    ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                    *spans,
                ]))
                story.append(KeepTogether([agent_t, Spacer(1, 5)]))

        # Sources
        if report.sources:
            story.append(HRFlowable(width="100%", thickness=0.75, color=BORDER,
                                     spaceAfter=6, spaceBefore=6))
            story.append(Paragraph("KEY SOURCES", S(size=7, color=GREEN, bold=True, space_after=4)))
            src_rows = [[Paragraph(f"• {s}", S(size=8, color=TEXT, leading=12))]
                         for s in report.sources[:12]]
            story.append(card(src_rows))
            story.append(Spacer(1, 8))

        # Red flags
        if report.red_flags:
            flags_str = "   ·   ".join(report.red_flags[:10])
            story.append(card(
                [[Paragraph(f"Red Flags: {flags_str}", S(size=8, color=RED, leading=12))]],
                bg=HexColor("#180808"), border=HexColor("#3a1010"),
            ))
            story.append(Spacer(1, 8))

        # Key insights
        if report.key_insights:
            story.append(Paragraph("KEY INSIGHTS", S(size=7, color=GREEN, bold=True, space_after=4)))
            ins_rows = [[Paragraph(f"→  {i}", S(size=8, color=TEXT, leading=12))]
                         for i in report.key_insights[:8]]
            story.append(card(ins_rows))
            story.append(Spacer(1, 8))

        # Footer
        story.append(HRFlowable(width="100%", thickness=0.75, color=BORDER, spaceAfter=5))
        story.append(Paragraph(
            f"VeritySwarm · verityswarm.com · {report.report_id}  —  "
            "AI-generated. Verify critical claims independently.",
            S(size=7, color=MUTED, align=TA_CENTER),
        ))

        # Write
        slug = re.sub(r"[^\w\s-]", "", report.claim.lower())[:40].strip().replace(" ", "_")
        pdf_path = self.reports_dir / f"{report.report_id}_{slug}.pdf"
        doc = SimpleDocTemplate(
            str(pdf_path), pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=18*mm, bottomMargin=18*mm,
        )
        doc.build(story, onFirstPage=page_bg, onLaterPages=page_bg)
        return str(pdf_path)

    # ── Terminal output ───────────────────────────────────────────────────

    def _print_report(self, report: VerityReport) -> None:
        W = 68
        VERDICT_PREFIX = {
            "TRUE": "✓", "FALSE": "✗", "PARTIALLY TRUE": "~",
            "MISLEADING": "!", "UNVERIFIED": "?",
        }
        pct = report.confidence
        bar_filled = round(pct / 4)
        bar = "█" * bar_filled + "░" * (25 - bar_filled)

        def wrap(text: str, indent: int = 14, width: int = W - 2) -> str:
            lines = textwrap.wrap(text, width - indent)
            pad = " " * indent
            return f"\n{pad}".join(lines)

        print(f"\n╔{'═' * W}╗")
        print(f"║  VeritySwarm · VERITY REPORT · {report.report_id:<32}║")
        print(f"╚{'═' * W}╝")
        print()
        print(f"  Claim      {wrap(report.claim)}")
        print(f"  {'─' * (W - 2)}")
        prefix = VERDICT_PREFIX.get(report.verdict, "·")
        print(f"  Verdict    {prefix}  {report.verdict}")
        print(f"  Score      {pct}/100  {bar}")
        print(f"  Backend    {report.synthesizer_backend.upper()}")
        print()
        print(f"  Summary")
        print(f"  {'─' * (W - 2)}")
        for line in textwrap.wrap(report.summary, W - 4):
            print(f"    {line}")
        print()

        for rnd_label, rnd_data in (("Round 1 — Independent", report.round1),
                                     ("Round 2 — Peer-Refined", report.round2)):
            if not rnd_data:
                continue
            print(f"  ┌─ {rnd_label} {'─' * (W - len(rnd_label) - 5)}┐")
            for aname, out in rnd_data.items():
                icon = self.AGENT_ICONS.get(aname, "·")
                bar_a = round(out.confidence / 4)
                abar = "█" * bar_a + "░" * (25 - bar_a)
                name_col = f"{icon} {aname:<20}"
                print(f"  │  {name_col} [{out.confidence:3}/100] {abar} │")
                snippet = textwrap.shorten(out.analysis, width=W - 8, placeholder="…")
                for ln in textwrap.wrap(snippet, W - 8):
                    print(f"  │    {ln:<{W - 6}}│")
                if out.key_insights:
                    ki = "  ·  ".join(out.key_insights[:2])
                    for ln in textwrap.wrap(f"Key: {ki}", W - 8):
                        print(f"  │    {ln:<{W - 6}}│")
                if out.red_flags:
                    print(f"  │    ⚑ {', '.join(out.red_flags[:3]):<{W - 9}}│")
                print(f"  │  {'─' * (W - 4)}│")
            print(f"  └{'─' * (W)}┘")
            print()

        if report.sources:
            print(f"  Sources")
            for s in report.sources[:6]:
                print(f"    • {s}")
            print()
        if report.red_flags:
            print(f"  Flags     {', '.join(report.red_flags)}")
        if report.key_insights:
            print(f"\n  Insights")
            for ki in report.key_insights[:4]:
                print(f"    → {ki}")
        print()
        print(f"  JSON  → {report.json_path}")
        if report.pdf_path:
            print(f"  PDF   → {report.pdf_path}")
        print(f"{'═' * (W + 2)}\n")

    # ── Public API ────────────────────────────────────────────────────────

    def verify(
        self,
        claim:   str,
        rounds:  int  = 2,
        pdf:     bool = True,
        verbose: bool = True,
    ) -> VerityReport:
        """
        Full swarm verification pipeline.

        Args:
            claim:   Statement to verify.
            rounds:  1 = independent only, 2 = full cross-pollinating iteration (default).
            pdf:     Generate PDF export (requires reportlab).
            verbose: Print progress + final report to terminal.

        Returns:
            VerityReport
        """
        ts = datetime.now()
        report_id = f"VR-{ts.strftime('%Y%m%d-%H%M%S')}"
        generated_at = ts.strftime("%Y-%m-%d %H:%M:%S")

        if verbose:
            print(f"\n[VeritySwarm] {report_id}")
            print(f"[VeritySwarm] Claim: {claim!r}")
            print(f"[VeritySwarm] Rounds: {rounds}  PDF: {pdf}")
            print()

        # ── Round 1 ──────────────────────────────────────────────────────
        r1: dict[str, AgentOutput] = {}
        for name in self.AGENT_ORDER:
            icon = self.AGENT_ICONS[name]
            if verbose:
                print(f"  R1 {icon} {name:<22}", end=" ", flush=True)
            out = self._run_r1_agent(name, claim)
            r1[name] = out
            if verbose:
                flag = f"  ⚑ {out.red_flags[0]}" if out.red_flags else ""
                print(f"conf={out.confidence:3}/100{flag}")

        # ── Round 2 ──────────────────────────────────────────────────────
        r2: dict[str, AgentOutput] = {}
        if rounds >= 2:
            if verbose:
                print()
            for name in self.AGENT_ORDER:
                icon = self.AGENT_ICONS[name]
                if verbose:
                    print(f"  R2 {icon} {name:<22}", end=" ", flush=True)
                out = self._run_r2_agent(name, claim, r1)
                r2[name] = out
                if verbose:
                    delta = out.confidence - r1[name].confidence
                    sign = "+" if delta >= 0 else ""
                    print(f"conf={out.confidence:3}/100  (Δ{sign}{delta})")

        # ── Synthesis ─────────────────────────────────────────────────────
        if verbose:
            print(f"\n  ⚙  Synthesizing (Grok → Gemini → Claude)...", end=" ", flush=True)
        synthesis, backend = self._synthesize(claim, r1, r2 or r1)
        if verbose:
            print(f"[{backend.upper()}]  verdict={synthesis.get('verdict')}  "
                  f"conf={synthesis.get('confidence')}")

        # ── Merge sources / flags / insights ─────────────────────────────
        def _merge_lists(key: str, max_items: int = 12) -> list[str]:
            seen, out = set(), []
            for src in [synthesis.get(key, [])] + [o.__dict__.get(key, [])
                        for rounds_dict in (r1, r2) for o in rounds_dict.values()]:
                for item in (src or []):
                    if item and item not in seen:
                        seen.add(item)
                        out.append(item)
            return out[:max_items]

        all_sources  = _merge_lists("sources",      12)
        all_flags    = _merge_lists("red_flags",    16)
        all_insights = _merge_lists("key_insights", 10)

        report = VerityReport(
            report_id=report_id,
            claim=claim,
            verdict=synthesis.get("verdict", "UNVERIFIED"),
            confidence=self._safe_int(synthesis.get("confidence", 0)),
            summary=synthesis.get("summary", ""),
            synthesis=synthesis.get("synthesis", ""),
            round1=r1,
            round2=r2,
            sources=all_sources,
            red_flags=all_flags,
            key_insights=all_insights,
            synthesizer_backend=backend,
            generated_at=generated_at,
        )

        report.json_path = self._save_json(report)
        if pdf:
            report.pdf_path = self.export_pdf(report)
            if verbose and report.pdf_path:
                print(f"  📄 PDF → {report.pdf_path}")

        if verbose:
            print()
            self._print_report(report)

        return report


# ─────────────────────────────────────────────────────────────────────────────
# Stripe checkout stub
# ─────────────────────────────────────────────────────────────────────────────

def stripe_checkout_stub(tier: str = "pro") -> dict:
    """
    Stripe Checkout stub — swap for live integration.

    Live implementation:
        pip install stripe
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": PRICE_ID_MAP[tier], "quantity": 1}],
            success_url="https://verityswarm.com/welcome",
            cancel_url="https://verityswarm.com/#pricing",
        )
        return {"checkout_url": session.url}
    """
    TIERS = {
        "pro":        {"name": "VeritySwarm Pro",        "price_cents": 900,  "price_usd": 9.00},
        "enterprise": {"name": "VeritySwarm Enterprise", "price_cents": 9900, "price_usd": 99.00},
    }
    info = TIERS.get(tier, TIERS["pro"])
    return {
        "stub": True, "tier": tier, "name": info["name"],
        "price_cents": info["price_cents"], "currency": "usd",
        "checkout_url": "https://buy.stripe.com/REPLACE_WITH_REAL_PRICE_LINK",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="VeritySwarm — AI truth-verification swarm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python agents/swarm.py "Humans only use 10 percent of their brain"
          python agents/swarm.py --rounds 1 "The moon landing was faked"
          python agents/swarm.py --no-pdf "Coffee causes cancer"
        """),
    )
    parser.add_argument("claim", nargs="*",
                        help="Claim to verify (quoted string or multiple words)")
    parser.add_argument("--rounds", type=int, default=2, choices=[1, 2],
                        help="1 = single-pass, 2 = cross-pollinating (default: 2)")
    parser.add_argument("--no-pdf", action="store_true",
                        help="Skip PDF generation")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose terminal output")
    args = parser.parse_args()

    claim = " ".join(args.claim) if args.claim else (
        "The Great Wall of China is visible from space with the naked eye."
    )

    swarm = VeritySwarm()
    swarm.verify(
        claim=claim,
        rounds=args.rounds,
        pdf=not args.no_pdf,
        verbose=not args.quiet,
    )
