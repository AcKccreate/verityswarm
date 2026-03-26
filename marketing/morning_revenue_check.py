"""
Morning Revenue Check
─────────────────────
Runs daily at 7am — checks Stripe for new payments and reports via Telegram.

Setup (cron / Task Scheduler):
  Linux:   0 7 * * * cd /path/to/verityswarm && python -m marketing.morning_revenue_check
  Windows: schtasks /create /tn "MorningRevenue" /tr "python -m marketing.morning_revenue_check" /sc daily /st 07:00
"""

import os
from dotenv import load_dotenv
load_dotenv("C:/Users/acase/AnchorWithin/.env")

import json
import logging
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Revenue] %(message)s")
log = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def check_stripe_revenue() -> dict:
    """Check Stripe for payments in the last 24 hours."""
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY

        yesterday = datetime.now() - timedelta(days=1)
        since = int(yesterday.replace(hour=7, minute=0, second=0).timestamp())

        # Get charges
        charges = stripe.Charge.list(created={"gte": since}, limit=100)
        paid = [c for c in charges.data if c.paid and not c.refunded]

        total_revenue = sum(c.amount for c in paid) / 100
        total_count = len(paid)

        # Get new subscriptions
        subs = stripe.Subscription.list(created={"gte": since}, limit=100)
        new_subs = len(subs.data)

        # Breakdown by product/description
        breakdown = {}
        for c in paid:
            desc = c.description or "Unknown"
            if desc not in breakdown:
                breakdown[desc] = {"count": 0, "total": 0}
            breakdown[desc]["count"] += 1
            breakdown[desc]["total"] += c.amount / 100

        return {
            "total_revenue": total_revenue,
            "payment_count": total_count,
            "new_subscriptions": new_subs,
            "breakdown": breakdown,
            "period": f"{yesterday.strftime('%Y-%m-%d')} 7am to now",
        }

    except ImportError:
        return {"error": "Stripe SDK not installed. Run: pip install stripe"}
    except Exception as e:
        return {"error": str(e)}


def format_report(data: dict) -> str:
    """Format revenue data into a Telegram message."""
    if "error" in data:
        return f"Revenue Check FAILED\n\n{data['error']}"

    lines = [
        "MORNING REVENUE REPORT",
        f"Period: {data['period']}",
        "",
        f"Total Revenue: ${data['total_revenue']:.2f}",
        f"Payments: {data['payment_count']}",
        f"New Subscriptions: {data['new_subscriptions']}",
    ]

    if data["breakdown"]:
        lines.append("")
        lines.append("Breakdown:")
        for desc, info in data["breakdown"].items():
            lines.append(f"  {desc}: ${info['total']:.2f} ({info['count']}x)")
    elif data["payment_count"] == 0:
        lines.append("")
        lines.append("No new payments. Time to push traffic!")

    return "\n".join(lines)


def send_telegram(message: str):
    """Send report via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured. Printing to stdout instead.")
        print(message)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode()
    req = Request(url, data=data)
    try:
        urlopen(req, timeout=10)
        log.info("Revenue report sent to Telegram")
        return True
    except Exception as e:
        log.error(f"Failed to send Telegram message: {e}")
        print(message)
        return False


def run():
    """Main entry point."""
    log.info("Running morning revenue check...")

    if not STRIPE_SECRET_KEY:
        msg = (
            "MORNING REVENUE REPORT\n\n"
            "Stripe not configured yet.\n"
            "Set STRIPE_SECRET_KEY in C:/Users/acase/AnchorWithin/.env\n"
            "Then set up a scheduled task to run this at 7am daily."
        )
        send_telegram(msg)
        return

    data = check_stripe_revenue()
    report = format_report(data)
    send_telegram(report)


if __name__ == "__main__":
    run()
