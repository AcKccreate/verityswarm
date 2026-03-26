import os
from dotenv import load_dotenv
load_dotenv("C:/Users/acase/AnchorWithin/.env")

"""
VeritySwarm Telegram Commander
─────────────────────────────
Bang commands for revenue operations via Telegram bot.

Commands:
  !revenue   — Today's Stripe revenue summary
  !leads     — Show active outreach leads
  !verify    — Run a quick claim verification
  !status    — System health check
  !content   — Show content queue status
  !help      — List all commands
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TelegramCMD] %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

# ─── Command Handlers ────────────────────────────────────────────────────────

async def cmd_revenue(chat_id: str) -> str:
    """Fetch today's Stripe revenue."""
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        today_start = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp())
        charges = stripe.Charge.list(created={"gte": today_start}, limit=100)
        total = sum(c.amount for c in charges.data if c.paid) / 100
        count = sum(1 for c in charges.data if c.paid)
        return f"Today's Revenue: ${total:.2f} ({count} payments)"
    except ImportError:
        return "Stripe SDK not installed. Run: pip install stripe"
    except Exception as e:
        return f"Revenue check failed: {e}"


async def cmd_leads(chat_id: str) -> str:
    """Show active outreach leads count."""
    queue_path = Path(__file__).parent / "outreach_queue.json"
    if not queue_path.exists():
        return "No outreach queue found."
    with open(queue_path, "r") as f:
        leads = json.load(f)
    active = [l for l in leads if l.get("status") != "sent"]
    return f"Active leads: {len(active)} / {len(leads)} total"


async def cmd_verify(chat_id: str, claim: str = "") -> str:
    """Quick verification of a claim."""
    if not claim:
        return "Usage: !verify <claim to check>"
    try:
        from agents.swarm import VeritySwarm
        swarm = VeritySwarm()
        report = await asyncio.to_thread(swarm.verify, claim)
        return f"Verdict: {report.verdict} (Confidence: {report.confidence}%)\n{report.summary[:200]}"
    except Exception as e:
        return f"Verification error: {e}"


async def cmd_status(chat_id: str) -> str:
    """System health check."""
    checks = []
    checks.append(f"Bot: ONLINE")
    checks.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    checks.append(f"Stripe: {'configured' if STRIPE_SECRET_KEY else 'NOT SET'}")
    checks.append(f"Telegram: {'configured' if TELEGRAM_BOT_TOKEN else 'NOT SET'}")

    queue_path = Path(__file__).parent / "marketing" / "content_queue"
    if queue_path.exists():
        pending = len(list(queue_path.glob("*.json")))
        checks.append(f"Content queue: {pending} posts pending")

    return "\n".join(checks)


async def cmd_content(chat_id: str) -> str:
    """Show content queue status."""
    queue_path = Path(__file__).parent / "marketing" / "content_queue"
    if not queue_path.exists():
        return "Content queue directory not found."
    files = sorted(queue_path.glob("*.json"))
    if not files:
        return "Content queue is empty."
    return f"Content queue: {len(files)} posts ready\nLatest: {files[-1].name}"


async def cmd_help(chat_id: str) -> str:
    """List all commands."""
    return (
        "VeritySwarm Commands:\n"
        "  !revenue  — Today's Stripe revenue\n"
        "  !leads    — Active outreach leads\n"
        "  !verify <claim> — Quick verification\n"
        "  !status   — System health check\n"
        "  !content  — Content queue status\n"
        "  !help     — This message"
    )


COMMANDS = {
    "!revenue": cmd_revenue,
    "!leads": cmd_leads,
    "!verify": cmd_verify,
    "!status": cmd_status,
    "!content": cmd_content,
    "!help": cmd_help,
}

# ─── Telegram Bot Loop ───────────────────────────────────────────────────────

async def send_message(chat_id: str, text: str):
    """Send a message via Telegram Bot API."""
    import urllib.request
    import urllib.parse
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=data)
    urllib.request.urlopen(req, timeout=10)


async def poll_updates():
    """Long-poll for Telegram updates and dispatch bang commands."""
    import urllib.request
    offset = 0
    log.info("Telegram Commander started. Polling for updates...")

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read().decode())

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "").strip()
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if not text.startswith("!"):
                    continue

                parts = text.split(maxsplit=1)
                cmd_name = parts[0].lower()
                cmd_args = parts[1] if len(parts) > 1 else ""

                handler = COMMANDS.get(cmd_name)
                if handler:
                    log.info(f"Executing: {cmd_name} from chat {chat_id}")
                    if cmd_name == "!verify":
                        result = await handler(chat_id, cmd_args)
                    else:
                        result = await handler(chat_id)
                    await send_message(chat_id, result)
                else:
                    await send_message(chat_id, f"Unknown command: {cmd_name}\nType !help for available commands.")

        except Exception as e:
            log.error(f"Polling error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in environment.")
        print("Set it in C:/Users/acase/AnchorWithin/.env")
        exit(1)
    asyncio.run(poll_updates())
