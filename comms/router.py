import os
from dotenv import load_dotenv
load_dotenv("C:/Users/acase/AnchorWithin/.env")

"""
VeritySwarm Communications Router
──────────────────────────────────
Routes messages between Telegram, email, and internal systems.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Router] %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class CommsRouter:
    """Central message router for all communication channels."""

    def __init__(self):
        self.channels = {
            "telegram": self._send_telegram,
            "log": self._send_log,
        }

    async def send(self, channel: str, message: str, **kwargs):
        """Route a message to the specified channel."""
        handler = self.channels.get(channel)
        if not handler:
            log.warning(f"Unknown channel: {channel}")
            return False
        try:
            await handler(message, **kwargs)
            return True
        except Exception as e:
            log.error(f"Failed to send via {channel}: {e}")
            return False

    async def broadcast(self, message: str, channels: list[str] | None = None):
        """Send message to multiple channels."""
        targets = channels or list(self.channels.keys())
        results = {}
        for ch in targets:
            results[ch] = await self.send(ch, message)
        return results

    async def _send_telegram(self, message: str, chat_id: str | None = None, **kwargs):
        """Send via Telegram Bot API."""
        import urllib.request
        import urllib.parse

        target_chat = chat_id or TELEGRAM_CHAT_ID
        if not TELEGRAM_BOT_TOKEN or not target_chat:
            log.warning("Telegram not configured (missing token or chat_id)")
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": target_chat,
            "text": message,
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
        log.info(f"Telegram message sent to {target_chat}")

    async def _send_log(self, message: str, **kwargs):
        """Log message to file."""
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"comms_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")
        log.info(f"Message logged to {log_file.name}")


# Singleton instance
router = CommsRouter()
