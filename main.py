"""Job Discovery Agent — fetch, filter, enrich, dedupe, and send job alerts."""

import argparse
import logging

import yaml
from dotenv import load_dotenv

from jobbot import adzuna, ats_boards
from jobbot.db import JobDB
from jobbot.enrich import classify_sponsorship, detect_interface
from jobbot.filters import (is_recent, location_is_us, title_is_excluded,
                            title_matches_keywords)
from jobbot.notify import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print jobs instead of sending to Telegram "
                             "(still records them in the database)")
    args = parser.parse_args()

    load_dotenv()
    config = load_config()

    keywords = config["keywords"]
    exclude_terms = config["exclude_title_terms"]
    max_age_hours = config.get("max_age_hours", 24)
    sponsorship_signals = config.get("sponsorship", {})

    # 1. Fetch
    jobs = []
    if config.get("adzuna", {}).get("enabled", True):
        jobs += adzuna.fetch(config["adzuna"], keywords, max_age_hours)
    if config.get("ats_boards", {}).get("enabled", True):
        board_jobs = ats_boards.fetch(config["ats_boards"])
        # ATS boards list every open role globally — keep US roles only.
        # (Adzuna results are already US-scoped.)
        jobs += [j for j in board_jobs if location_is_us(j.location)]
    log.info("Fetched %d candidate jobs", len(jobs))

    # 2. Filter: role keywords + recency + seniority
    jobs = [j for j in jobs
            if j.url
            and title_matches_keywords(j.title, keywords)
            and is_recent(j.posted_at, max_age_hours)
            and not title_is_excluded(j.title, exclude_terms)]
    log.info("%d jobs after keyword/recency/seniority filters", len(jobs))

    # 2b. Collapse multi-location repostings of the same role so one job
    # doesn't fill the digest with near-identical messages.
    by_role = {}
    for job in jobs:
        key = (job.company.lower(), job.title.lower())
        if key in by_role:
            by_role[key].location += " (+ other locations)" \
                if not by_role[key].location.endswith("(+ other locations)") else ""
        else:
            by_role[key] = job
    jobs = list(by_role.values())
    log.info("%d jobs after collapsing multi-location duplicates", len(jobs))

    # 3. Enrich: sponsorship signals + application interface
    for job in jobs:
        job.interface = detect_interface(job.url, job.source)
        job.sponsorship = classify_sponsorship(
            f"{job.title}\n{job.description}", sponsorship_signals)

    # 4. Dedupe against previous runs
    db = JobDB(config.get("database_path", "jobs.db"))
    new_jobs = db.filter_new(jobs)
    db.close()
    log.info("%d new jobs after dedupe", len(new_jobs))

    # 5. Notify
    if args.dry_run:
        for job in new_jobs:
            print("-" * 60)
            print(TelegramNotifier.format_job(job))
        print("-" * 60)
        print(f"[dry-run] {len(new_jobs)} new jobs (not sent)")
        return

    notifier = TelegramNotifier()
    notifier.send_digest(
        new_jobs, max_jobs=config.get("telegram", {}).get("max_jobs_per_digest", 40))
    log.info("Digest sent")


if __name__ == "__main__":
    main()
