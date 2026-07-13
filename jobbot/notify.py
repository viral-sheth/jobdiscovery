import html
import logging
import os
import time
from datetime import date
from typing import List

import requests

from .enrich import INTERFACE_ORDER
from .models import Job

log = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
RATE_LIMIT_SECONDS = 1.1


class TelegramNotifier:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not self.token or not self.chat_id:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env "
                "(run get_chat_id.py to find your chat id)")

    def _send(self, text: str):
        resp = requests.post(
            f"{API_BASE}/bot{self.token}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if not resp.ok:
            log.error("Telegram send failed (%d): %s", resp.status_code, resp.text)
        time.sleep(RATE_LIMIT_SECONDS)

    @staticmethod
    def format_job(job: Job) -> str:
        return (
            f"🏢 <b>{html.escape(job.company)}</b> | {html.escape(job.title)}\n"
            f"📍 {html.escape(job.location or 'Not specified')}\n"
            f"🖥️ Interface: {html.escape(job.interface)}\n"
            f"🌐 Sponsorship: {html.escape(job.sponsorship)}\n"
            f"🔗 <a href=\"{html.escape(job.url, quote=True)}\">Apply Link</a>"
        )

    def send_digest(self, jobs: List[Job], max_jobs: int = 40):
        today = date.today().strftime("%b %d, %Y")
        self._send(f"📋 Job Digest — {today} | {len(jobs)} new jobs found")
        if not jobs:
            return

        ordered = sorted(jobs, key=lambda j: (INTERFACE_ORDER.get(j.interface, 9),
                                              j.company.lower()))
        for job in ordered[:max_jobs]:
            self._send(self.format_job(job))

        overflow = len(ordered) - max_jobs
        if overflow > 0:
            self._send(f"…and {overflow} more new jobs (over the per-digest cap; "
                       f"raise telegram.max_jobs_per_digest in config.yaml to see more).")
