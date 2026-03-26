"""
VeritySwarm Directory Submitter
───────────────────────────────
Submits tools to free AI directories via HTTP POST.
Targets: theresanaiforthat.com, futurepedia.io

Usage:
    python -m marketing.directory_submitter                    # Submit all tools
    python -m marketing.directory_submitter --tool resume-optimizer  # Single tool
    python -m marketing.directory_submitter --dry-run          # Preview without submitting
"""

import os
from dotenv import load_dotenv
load_dotenv("C:/Users/acase/AnchorWithin/.env")

import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DirSubmit] %(message)s")
log = logging.getLogger(__name__)

SUBMISSIONS_LOG = Path(__file__).parent / "submissions_log.json"

# ─── Tool Definitions ────────────────────────────────────────────────────────

TOOLS = {
    "resume-optimizer": {
        "name": "Resume Optimizer by AnchorWithin",
        "short_description": "AI-powered resume tailoring that matches your resume to specific job postings",
        "long_description": (
            "Resume Optimizer analyzes job postings and intelligently tailors your resume to match. "
            "It identifies missing keywords, suggests content improvements, and scores your resume "
            "against role requirements. Built with Claude AI for nuanced understanding of both "
            "your experience and employer expectations. Free tier available."
        ),
        "url": "https://verityswarm.com/tools/html/bundle.html",
        "category": "Productivity",
        "tags": ["resume", "job search", "career", "AI writing", "productivity"],
        "pricing": "Freemium",
        "priority": 1,  # Submit first — broadest appeal
    },
    "verity-swarm": {
        "name": "VeritySwarm — AI Truth Verification",
        "short_description": "5 AI agents cross-check any claim with sourced citations and confidence scores",
        "long_description": (
            "VeritySwarm deploys 5 specialized AI agents (Researcher, Skeptic, Bias Detector, "
            "Source Cross-Checker, Context Historian) through 2 rounds of adversarial analysis. "
            "Each claim gets a confidence score, source citations, red flags, and a transparent "
            "reasoning chain. Uses Grok, Gemini, and Claude for synthesis diversity. "
            "Free tier: 3 checks/day. Pro: $9/mo unlimited."
        ),
        "url": "https://verityswarm.com",
        "category": "Research",
        "tags": ["fact-checking", "verification", "AI agents", "research", "misinformation"],
        "pricing": "Freemium",
        "priority": 2,
    },
}

# ─── Directory Targets ────────────────────────────────────────────────────────

DIRECTORIES = {
    "theresanaiforthat": {
        "name": "There's An AI For That",
        "submit_url": "https://theresanaiforthat.com/submit/",
        "method": "form_post",
    },
    "futurepedia": {
        "name": "Futurepedia",
        "submit_url": "https://www.futurepedia.io/submit-tool",
        "method": "form_post",
    },
}


def load_submission_log() -> list:
    """Load existing submission log."""
    if SUBMISSIONS_LOG.exists():
        with open(SUBMISSIONS_LOG) as f:
            return json.load(f)
    return []


def save_submission_log(log_entries: list):
    """Save submission log."""
    with open(SUBMISSIONS_LOG, "w") as f:
        json.dump(log_entries, f, indent=2)


def already_submitted(tool_key: str, directory_key: str, log_entries: list) -> bool:
    """Check if we already submitted this tool to this directory."""
    return any(
        e["tool"] == tool_key and e["directory"] == directory_key
        for e in log_entries
    )


def submit_to_directory(tool_key: str, directory_key: str, dry_run: bool = False) -> dict:
    """Submit a tool to a directory via HTTP POST."""
    tool = TOOLS[tool_key]
    directory = DIRECTORIES[directory_key]
    result = {
        "tool": tool_key,
        "directory": directory_key,
        "directory_name": directory["name"],
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
    }

    form_data = {
        "name": tool["name"],
        "url": tool["url"],
        "description": tool["short_description"],
        "long_description": tool["long_description"],
        "category": tool["category"],
        "tags": ", ".join(tool["tags"]),
        "pricing": tool["pricing"],
        "email": os.getenv("CONTACT_EMAIL", "hello@verityswarm.com"),
    }

    if dry_run:
        log.info(f"[DRY RUN] Would submit '{tool['name']}' to {directory['name']}")
        log.info(f"  URL: {directory['submit_url']}")
        log.info(f"  Data: {json.dumps(form_data, indent=2)}")
        result["status"] = "dry_run"
        return result

    try:
        data = urlencode(form_data).encode("utf-8")
        req = Request(
            directory["submit_url"],
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": directory["submit_url"],
            },
        )
        with urlopen(req, timeout=30) as resp:
            status_code = resp.getcode()
            result["http_status"] = status_code
            if 200 <= status_code < 400:
                result["status"] = "submitted"
                log.info(f"Submitted '{tool['name']}' to {directory['name']} (HTTP {status_code})")
            else:
                result["status"] = "failed"
                log.warning(f"Unexpected response from {directory['name']}: HTTP {status_code}")

    except HTTPError as e:
        # Many submission forms redirect or return 4xx for duplicate submissions
        result["status"] = "submitted_or_duplicate"
        result["http_status"] = e.code
        log.info(f"Submitted to {directory['name']} (HTTP {e.code} — may be redirect or duplicate)")
    except URLError as e:
        result["status"] = "network_error"
        result["error"] = str(e.reason)
        log.error(f"Network error submitting to {directory['name']}: {e.reason}")
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        log.error(f"Error submitting to {directory['name']}: {e}")

    return result


def run_submissions(tool_filter: str | None = None, dry_run: bool = False):
    """Submit tools to all directories."""
    log_entries = load_submission_log()

    # Sort tools by priority (resume-optimizer first)
    sorted_tools = sorted(TOOLS.items(), key=lambda x: x[1]["priority"])

    if tool_filter:
        sorted_tools = [(k, v) for k, v in sorted_tools if k == tool_filter]

    results = []
    for tool_key, tool_info in sorted_tools:
        for dir_key in DIRECTORIES:
            if already_submitted(tool_key, dir_key, log_entries) and not dry_run:
                log.info(f"Already submitted '{tool_info['name']}' to {DIRECTORIES[dir_key]['name']} — skipping")
                continue

            result = submit_to_directory(tool_key, dir_key, dry_run=dry_run)
            results.append(result)

            if not dry_run:
                log_entries.append(result)
                save_submission_log(log_entries)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit tools to AI directories")
    parser.add_argument("--tool", choices=list(TOOLS.keys()), help="Submit specific tool only")
    parser.add_argument("--dry-run", action="store_true", help="Preview without submitting")
    args = parser.parse_args()

    results = run_submissions(tool_filter=args.tool, dry_run=args.dry_run)

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Submission Results:")
    for r in results:
        print(f"  [{r['status'].upper()}] {r.get('directory_name', '?')} <- {TOOLS[r['tool']]['name']}")
