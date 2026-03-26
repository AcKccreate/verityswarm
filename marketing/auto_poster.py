"""
VeritySwarm Auto Poster
───────────────────────
Generates one helpful Reddit-style post per day per tool using the Claude API.
Saves posts to marketing/content_queue/ as JSON files for later publishing.

Usage:
    python -m marketing.auto_poster              # Generate today's posts
    python -m marketing.auto_poster --tool verity-swarm  # Single tool only
"""

import os
from dotenv import load_dotenv
load_dotenv("C:/Users/acase/AnchorWithin/.env")

import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AutoPoster] %(message)s")
log = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CONTENT_QUEUE = Path(__file__).parent / "content_queue"
CONTENT_QUEUE.mkdir(exist_ok=True)

# Tools we're promoting
TOOLS = {
    "verity-swarm": {
        "name": "VeritySwarm",
        "tagline": "AI Truth Verification — 5 agents cross-check any claim",
        "url": "https://verityswarm.com",
        "subreddits": ["artificial", "MachineLearning", "journalism", "media_criticism", "factcheck"],
        "description": (
            "VeritySwarm runs 5 specialized AI agents (Researcher, Skeptic, Bias Detector, "
            "Source Cross-Checker, Context Historian) through 2 rounds of analysis to verify "
            "any claim. It produces confidence scores, source citations, and transparent reasoning chains."
        ),
    },
    "resume-optimizer": {
        "name": "Resume Optimizer",
        "tagline": "AI-powered resume tailoring for job applications",
        "url": "https://verityswarm.com/tools/resume-optimizer",
        "subreddits": ["resumes", "jobs", "careerguidance", "cscareerquestions", "GetEmployed"],
        "description": (
            "Our Resume Optimizer uses AI to analyze job postings and tailor your resume "
            "to match. It highlights missing keywords, suggests improvements, and scores "
            "your resume against the specific role requirements."
        ),
    },
    "bundle": {
        "name": "AnchorWithin AI Tool Bundle",
        "tagline": "All our AI tools for $19.99/mo — VeritySwarm + Resume Optimizer + more",
        "url": "https://verityswarm.com/tools/html/bundle.html",
        "subreddits": ["SideProject", "startups", "Entrepreneur", "smallbusiness", "productivity"],
        "description": (
            "The AnchorWithin AI Bundle gives you access to all our AI tools: "
            "VeritySwarm truth verification, Resume Optimizer, and future tools as they launch, "
            "all for one flat price of $19.99/month."
        ),
    },
}

POST_PROMPT_TEMPLATE = """You are a helpful Reddit community member who genuinely wants to help people.
Write a Reddit-style post for r/{subreddit} that provides genuine value while naturally mentioning {tool_name}.

Tool info:
- Name: {tool_name}
- What it does: {description}
- URL: {url}

RULES:
1. Lead with a genuine insight, tip, or discussion question relevant to r/{subreddit}
2. The post must provide standalone value even without the tool mention
3. Mention the tool naturally as ONE option (not a hard sell) — "I've been using X" or "tools like X"
4. Use a conversational, authentic Reddit tone — NOT marketing speak
5. Keep it under 200 words
6. Include a compelling title that would get upvotes on its own merit
7. Do NOT use phrases like "game-changer", "revolutionary", or "check it out"

Output valid JSON with these exact keys:
{{"title": "...", "body": "...", "subreddit": "r/{subreddit}"}}"""


def generate_post(tool_key: str, subreddit: str) -> dict | None:
    """Generate a single Reddit-style post using Claude API."""
    tool = TOOLS[tool_key]
    prompt = POST_PROMPT_TEMPLATE.format(
        subreddit=subreddit,
        tool_name=tool["name"],
        description=tool["description"],
        url=tool["url"],
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Extract JSON from response
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        post = json.loads(text)
        post["tool"] = tool_key
        post["generated_at"] = datetime.now().isoformat()
        post["status"] = "pending"
        return post
    except ImportError:
        log.error("anthropic SDK not installed. Run: pip install anthropic")
        return None
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse Claude response as JSON: {e}")
        return None
    except Exception as e:
        log.error(f"Claude API error: {e}")
        return None


def save_post(post: dict) -> Path:
    """Save a generated post to the content queue."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tool = post.get("tool", "unknown")
    subreddit = post.get("subreddit", "unknown").replace("r/", "")
    filename = f"{timestamp}_{tool}_{subreddit}.json"
    filepath = CONTENT_QUEUE / filename
    with open(filepath, "w") as f:
        json.dump(post, f, indent=2)
    log.info(f"Saved: {filepath.name}")
    return filepath


def generate_daily_posts(tool_filter: str | None = None):
    """Generate one post per tool (rotating subreddit daily)."""
    today = datetime.now().timetuple().tm_yday  # day of year for rotation

    tools_to_post = {tool_filter: TOOLS[tool_filter]} if tool_filter else TOOLS
    generated = []

    for tool_key, tool_info in tools_to_post.items():
        # Rotate through subreddits based on day of year
        subs = tool_info["subreddits"]
        subreddit = subs[today % len(subs)]

        log.info(f"Generating post for {tool_info['name']} -> r/{subreddit}")
        post = generate_post(tool_key, subreddit)
        if post:
            path = save_post(post)
            generated.append(path)
        else:
            log.warning(f"Failed to generate post for {tool_key}")

    return generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate daily Reddit-style content")
    parser.add_argument("--tool", choices=list(TOOLS.keys()), help="Generate for specific tool only")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        exit(1)

    posts = generate_daily_posts(args.tool)
    print(f"\nGenerated {len(posts)} posts to marketing/content_queue/")
