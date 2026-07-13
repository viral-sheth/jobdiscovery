import logging
import os
from datetime import datetime, timezone
from typing import List

import requests
from bs4 import BeautifulSoup

from .models import Job

log = logging.getLogger(__name__)

API_BASE = "https://api.adzuna.com/v1/api/jobs"


def _clean_html(text: str) -> str:
    return BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)


def _resolve_redirect(session: requests.Session, url: str) -> str:
    """Follow Adzuna's redirect link to find the real apply URL (best effort)."""
    try:
        resp = session.get(url, timeout=10, allow_redirects=True, stream=True)
        final = resp.url
        resp.close()
        return final or url
    except requests.RequestException:
        return url


def fetch(config: dict, keywords: List[str], max_age_hours: int) -> List[Job]:
    app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        log.warning("Adzuna credentials missing (ADZUNA_APP_ID / ADZUNA_APP_KEY) — skipping Adzuna")
        return []

    country = config.get("country", "us")
    per_page = config.get("results_per_page", 50)
    max_pages = config.get("max_pages_per_keyword", 1)
    resolve = config.get("resolve_redirects", False)
    max_days_old = max(1, round(max_age_hours / 24))

    session = requests.Session()
    session.headers["User-Agent"] = "job-discovery-agent/1.0"

    jobs: List[Job] = []
    seen_ids = set()
    for keyword in keywords:
        for page in range(1, max_pages + 1):
            try:
                resp = session.get(
                    f"{API_BASE}/{country}/search/{page}",
                    params={
                        "app_id": app_id,
                        "app_key": app_key,
                        # Match keywords in the job title only — plain `what`
                        # searches full descriptions and returns lots of
                        # unrelated roles.
                        "title_only": keyword,
                        "results_per_page": per_page,
                        "max_days_old": max_days_old,
                        "sort_by": "date",
                        "content-type": "application/json",
                    },
                    timeout=30,
                )
                resp.raise_for_status()
            except requests.RequestException as e:
                log.warning("Adzuna request failed for %r page %d: %s", keyword, page, e)
                break

            results = resp.json().get("results", [])
            for item in results:
                ad_id = item.get("id")
                if ad_id in seen_ids:
                    continue
                seen_ids.add(ad_id)

                url = item.get("redirect_url", "")
                if not url:
                    continue
                if resolve:
                    url = _resolve_redirect(session, url)

                posted_at = None
                created = item.get("created")
                if created:
                    try:
                        posted_at = datetime.fromisoformat(
                            created.replace("Z", "+00:00")
                        ).astimezone(timezone.utc)
                    except ValueError:
                        pass

                jobs.append(Job(
                    url=url,
                    title=item.get("title", "").strip(),
                    company=(item.get("company") or {}).get("display_name", "Unknown"),
                    location=(item.get("location") or {}).get("display_name", ""),
                    description=_clean_html(item.get("description", "")),
                    posted_at=posted_at,
                    source="adzuna",
                ))
            if len(results) < per_page:
                break

    log.info("Adzuna: %d jobs fetched", len(jobs))
    return jobs
