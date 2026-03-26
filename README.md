# VeritySwarm — AI Truth Verification Swarm

**The strongest truth-verification engine on the internet.**

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](legal/TRADE_SECRETS.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Powered by Claude](https://img.shields.io/badge/AI-Claude%20%2B%20Grok%20%2B%20Gemini-8b5cf6.svg)](https://anthropic.com)

> **verityswarm.com** · AI fact-checking · Multi-agent verification · Confidence scores · Source citations

---

## What is VeritySwarm?

VeritySwarm deploys a coordinated swarm of 6 specialized AI agents to verify any claim — gathering evidence, stress-testing it adversarially, detecting bias, auditing sources, and placing it in historical context before a final synthesis delivers a definitive verdict.

**No spin. No hedging. Just transparent, structured truth.**

---

## How It Works

```
Claim Input
    │
    ▼
┌─────────────────────────────── Round 1: Independent Analysis ──────────────────────────────┐
│  🔍 Researcher      Evidence mining, fact gathering, source assembly                        │
│  ⚔️  Skeptic         Adversarial challenge, counter-evidence, gap analysis                  │
│  ⚖️  Bias Detector   Political/commercial/ideological framing analysis                      │
│  🔗 Source Cross-Checker   Credibility audit, inter-source consistency check               │
│  📜 Context Historian      Historical precedent, claim origin, pattern matching             │
└────────────────────────────────────────────────────────────────────────────────────────────┘
    │
    ▼ (each agent reads all peers' Round 1 output)
    │
┌─────────────────────────────── Round 2: Cross-Pollinating Refinement ──────────────────────┐
│  All 5 agents refine their analysis in light of peer findings                              │
│  Confidence scores shift. New red flags emerge. Weak arguments are challenged.             │
└────────────────────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────── Final Synthesis (Grok → Gemini → Claude) ───────────────────┐
│  🏛️  Synthesizer    Weighs all evidence across both rounds                                  │
│                    Issues definitive verdict with full reasoning chain                     │
└────────────────────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
Verity Report: Verdict · Confidence Score · Sources · Red Flags · Key Insights · PDF
```

---

## Verity Report Output

Every report includes:

| Field | Description |
|-------|-------------|
| **Verdict** | `TRUE` `FALSE` `PARTIALLY TRUE` `MISLEADING` `UNVERIFIED` |
| **Confidence Score** | 0–100 integer, weighted across all agents and rounds |
| **Summary** | 2–3 sentences, plain language, no hedging |
| **Synthesis** | Multi-paragraph integrated reasoning |
| **Sources** | Consolidated citations from all agents |
| **Red Flags** | `SNAKE_CASE` tags: `SINGLE_SOURCE`, `RECURRING_MYTH`, `POLITICAL_SPIN`... |
| **Key Insights** | Synthesized takeaways any sharp reader needs to know |
| **Reasoning Chain** | Full per-agent analysis (Round 1 and Round 2) |
| **PDF Export** | Dark-themed professional PDF via reportlab |

---

## Quick Start

```bash
# Install
pip install anthropic openai google-generativeai reportlab

# Set API keys in .env
ANTHROPIC_API_KEY=your_key
GEMINI_API_KEY=your_key
XAI_API_KEY=your_key  # optional (Grok synthesis)

# Run
python agents/swarm.py "Humans only use 10 percent of their brain"

# Options
python agents/swarm.py --rounds 1 --no-pdf "The moon landing was faked"
python agents/swarm.py --quiet "Wind turbines cause cancer" > report.txt
```

---

## Architecture

```
verityswarm/
├── agents/
│   ├── swarm.py          # Core swarm engine (v2)
│   └── __init__.py
├── legal/
│   ├── TERMS_OF_SERVICE.md
│   ├── PRIVACY_POLICY.md
│   ├── TRADE_SECRETS.md
│   └── NDA_TEMPLATE.md
├── cloudflare/
│   ├── setup_tunnel.bat  # One-click tunnel setup
│   └── config_template.yml
├── reports/              # Timestamped JSON + PDF history
└── index.html            # Landing page (Tailwind, dark mode)
```

---

## Agent Configuration

Each agent outputs strict JSON:

```json
{
  "analysis":     "detailed prose analysis",
  "confidence":   0-100,
  "sources":      ["source 1", "source 2"],
  "red_flags":    ["SNAKE_CASE_FLAGS"],
  "key_insights": ["concise insight 1", "concise insight 2"]
}
```

The Synthesizer aggregates all agents across both rounds and outputs:

```json
{
  "verdict":      "FALSE",
  "confidence":   94,
  "summary":      "Plain-language 2-3 sentence verdict.",
  "synthesis":    "Full integrated reasoning...",
  "sources":      ["..."],
  "red_flags":    ["PERSISTENT_MYTH", "DEBUNKED_PREVIOUSLY"],
  "key_insights": ["..."]
}
```

---

## Pricing

| Plan | Price | Limit |
|------|-------|-------|
| Free | $0 | 3 verifications/day |
| Pro | $9/mo | Unlimited + API + PDF |
| Enterprise | Custom | Bulk + white-label |

**[Get Pro at verityswarm.com](https://verityswarm.com/#pricing)**

---

## Keywords

AI fact checking · automated fact verification · truth verification AI · claim verification tool · misinformation detection · AI skeptic · bias detection tool · source credibility checker · multi-agent AI · swarm intelligence fact check · LLM fact checker · Grok verification · Claude fact check · AI truth engine

---

## Legal

Proprietary. All rights reserved. © 2026 AcKccreate.
See [TRADE_SECRETS.md](legal/TRADE_SECRETS.md) for IP protection details.
Contact: hello@verityswarm.com
