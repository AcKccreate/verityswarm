# VeritySwarm — Trade Secret Registry & IP Protection

**Classification:** CONFIDENTIAL — PROPRIETARY
**Owner:** AcKccreate / Casey Ace
**Date Established:** March 25, 2026
**Purpose:** Document proprietary innovations for trade secret protection and patent priority

---

## DECLARATION

This document establishes inventorship, first-date-of-conception, and trade secret status for the intellectual property assets of VeritySwarm. All assets described herein constitute proprietary information protected under the Defend Trade Secrets Act (DTSA), 18 U.S.C. § 1836, and applicable state trade secret laws (Utah Uniform Trade Secrets Act, Utah Code § 13-24).

**Inventor/First Disclosed To:** Casey Ace
**First Conception Date:** March 2026
**System Name:** VeritySwarm
**Domain:** verityswarm.com · verityswarm.net

---

## TRADE SECRET #001 — Multi-Agent Truth Verification Architecture

**Designation:** TS-001-SWARM-ARCH
**Date:** March 25, 2026
**Inventor:** Casey Ace

### Description
A multi-agent AI swarm architecture for truth verification in which 5–6 specialized agents operate in two iterative rounds:

- **Round 1 (Independent):** Each agent independently analyzes a claim from its designated epistemic perspective.
- **Round 2 (Cross-Pollinating):** Each agent reads the full output of all peer agents and refines its analysis in light of collective findings before synthesis.
- **Final Synthesis:** A dedicated Synthesizer agent (preferring Grok, with Gemini and Claude as fallbacks) produces a definitive verdict integrating all rounds.

### Proprietary Elements
1. The specific 5-agent configuration: Researcher, Skeptic, Bias Detector, Source Cross-Checker, Context Historian
2. The two-round cross-pollination protocol (each agent reads peers before refinement)
3. The confidence delta tracking between rounds (Δ confidence) as a signal of claim stability
4. The synthesizer fallback chain: Grok → Gemini → Claude

### Why Protectable
This specific agent topology and iterative cross-pollination protocol is not publicly documented in academic literature or commercial products as of the conception date. The combination of adversarial skeptic + bias detection + historical context in a coherent swarm pipeline is novel.

---

## TRADE SECRET #002 — Agent Prompt Engineering System

**Designation:** TS-002-PROMPTS
**Date:** March 25, 2026

### Description
The specific system prompts for each of the 6 specialized agents, including:
- Role definition and mandate language
- Strict JSON output schema contract enforced via prompt
- Round 2 refinement template that injects peer context
- Synthesizer voice ("unflinching, anti-hype, slightly rebellious against misinformation")

### Proprietary Elements
- Word-for-word prompt text for all 6 agents
- The JSON schema contract (`analysis, confidence 0-100, sources[], red_flags[], key_insights[]`)
- The cross-pollination template (`_R2_TEMPLATE`)
- The synthesizer persona voice and instruction set

---

## TRADE SECRET #003 — Verity Report Format & Scoring System

**Designation:** TS-003-REPORT
**Date:** March 25, 2026

### Description
The structured output format of a Verity Report, including:
- Five verdict categories with specific semantic definitions: TRUE, FALSE, PARTIALLY TRUE, MISLEADING, UNVERIFIED
- Confidence scoring methodology (0–100 integer, calibrated across agent consensus)
- Confidence delta between rounds as a stability indicator
- Red flag taxonomy (SHOUTING_SNAKE_CASE flags with specific semantic meaning)
- Key insights field as synthesized takeaways

---

## TRADE SECRET #004 — AnchorWithin Autonomous Operating System

**Designation:** TS-004-ANCHORWITHIN
**Date:** March 25, 2026

### Description
The full AnchorWithin autonomous revenue system, including:
- Claw swarm architecture (specialized autonomous agents running as NSSM services)
- Telegram commander as sole bot polling point with inline keyboard decision loop
- TrinityDecider auto-answer protocol (60-second threshold)
- Autonomous loop with conservative fallback (protect capital = default YES on closing losing trades)
- Multi-persona AI COO system (Radiant)

---

## CONFIDENTIALITY OBLIGATIONS

All contractors, employees, or collaborators who receive access to this material must sign the NDA in `NDA_TEMPLATE.md` prior to access. Unauthorized disclosure constitutes misappropriation of trade secrets under federal and state law.

---

## PATENT WATCH

The following may qualify for provisional patent protection (consult patent counsel):

1. **Two-round cross-pollinating multi-agent verification swarm** (TS-001)
2. **Confidence delta as claim stability signal** (TS-001)
3. **Adversarial agent topology for AI-assisted fact verification** (TS-001, TS-002)

**Provisional Patent Deadline:** File within 12 months of any public disclosure. First public disclosure of VeritySwarm: March 25, 2026.

**Recommended Action:** Engage a patent attorney to file a provisional patent application within 90 days covering TS-001 and TS-002.

---

*This document is CONFIDENTIAL. Do not distribute outside AcKccreate without explicit written authorization.*
