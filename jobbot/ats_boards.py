"""Fetch jobs from public, no-auth JSON APIs of company ATS job boards
(Greenhouse, Lever, Ashby)."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .models import Job

log = logging.getLogger(__name__)

TIMEOUT = 20


def _clean_html(text: str) -> str:
    return BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)


def _parse_iso(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _get_json(session: requests.Session, url: str, params: dict = None):
    resp = session.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _fetch_greenhouse(session: requests.Session, slug: str,
                      company: str) -> List[Job]:
    # The board root endpoint carries the proper company display name.
    if not company:
        try:
            board = _get_json(
                session, f"https://boards-api.greenhouse.io/v1/boards/{slug}")
            company = board.get("name") or ""
        except requests.RequestException:
            pass
    company = company or slug.capitalize()

    data = _get_json(
        session,
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        params={"content": "true"},
    )
    jobs = []
    for item in data.get("jobs", []):
        posted_at = _parse_iso(item.get("first_published") or item.get("updated_at"))
        jobs.append(Job(
            url=item.get("absolute_url", ""),
            title=(item.get("title") or "").strip(),
            company=company,
            location=((item.get("location") or {}).get("name") or ""),
            description=_clean_html(item.get("content", "")),
            posted_at=posted_at,
            source=f"greenhouse:{slug}",
        ))
    return jobs


def _fetch_lever(session: requests.Session, slug: str, company: str) -> List[Job]:
    data = _get_json(
        session,
        f"https://api.lever.co/v0/postings/{slug}",
        params={"mode": "json"},
    )
    jobs = []
    for item in data:
        created_ms = item.get("createdAt")
        posted_at = None
        if created_ms:
            posted_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
        categories = item.get("categories") or {}
        jobs.append(Job(
            url=item.get("hostedUrl", ""),
            title=(item.get("text") or "").strip(),
            company=company or slug.capitalize(),
            location=categories.get("location") or "",
            description=_clean_html(item.get("descriptionPlain")
                                    or item.get("description", "")),
            posted_at=posted_at,
            source=f"lever:{slug}",
        ))
    return jobs


def _fetch_ashby(session: requests.Session, slug: str, company: str) -> List[Job]:
    data = _get_json(
        session,
        f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
        params={"includeCompensation": "false"},
    )
    jobs = []
    for item in data.get("jobs", []):
        locations = [item.get("location") or ""]
        locations += [loc.get("location", "")
                      for loc in item.get("secondaryLocations") or []]
        location = "; ".join(l for l in locations if l)
        if item.get("isRemote") and "remote" not in location.lower():
            location = f"Remote — {location}" if location else "Remote"
        jobs.append(Job(
            url=item.get("jobUrl") or item.get("applyUrl", ""),
            title=(item.get("title") or "").strip(),
            company=company or slug.capitalize(),
            location=location,
            description=_clean_html(item.get("descriptionHtml")
                                    or item.get("descriptionPlain", "")),
            posted_at=_parse_iso(item.get("publishedAt")),
            source=f"ashby:{slug}",
        ))
    return jobs


FETCHERS = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "ashby": _fetch_ashby,
}


def fetch(config: dict) -> List[Job]:
    session = requests.Session()
    session.headers["User-Agent"] = "job-discovery-agent/1.0"

    jobs: List[Job] = []
    for ats, fetcher in FETCHERS.items():
        for entry in config.get(ats) or []:
            # Entries are either a plain slug or a `slug: Display Name` pair.
            if isinstance(entry, dict):
                slug, company = next(iter(entry.items()))
            else:
                slug, company = entry, ""
            try:
                board_jobs = fetcher(session, slug, company)
                jobs.extend(board_jobs)
                log.info("%s/%s: %d jobs", ats, slug, len(board_jobs))
            except requests.RequestException as e:
                log.warning("Skipping %s board %r: %s", ats, slug, e)
    return jobs
