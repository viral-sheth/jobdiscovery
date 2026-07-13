from typing import Dict, Iterable
from urllib.parse import urlparse

# Checked in order; first hostname match wins.
INTERFACE_DOMAINS = [
    ("greenhouse.io", "Greenhouse"),
    ("jobs.lever.co", "Lever"),
    ("jobs.ashbyhq.com", "Ashby"),
    ("ashbyhq.com", "Ashby"),
    ("myworkdayjobs.com", "Workday"),
    ("icims.com", "iCIMS"),
    ("paylocity.com", "Paylocity"),
]

# Ordering of interface groups in the Telegram digest (easy-apply ATSes first).
INTERFACE_ORDER = {
    "Greenhouse": 0,
    "Lever": 1,
    "Ashby": 2,
    "Workday": 3,
    "iCIMS": 4,
    "Paylocity": 5,
    "Other/Unknown": 9,
}


def detect_interface(url: str, source: str = "") -> str:
    # Jobs fetched straight from an ATS board API are that ATS by definition,
    # even when the company serves the posting from a custom careers domain.
    for prefix, name in (("greenhouse:", "Greenhouse"), ("lever:", "Lever"),
                         ("ashby:", "Ashby")):
        if source.startswith(prefix):
            return name
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    for domain, name in INTERFACE_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return name
    # Greenhouse job embedded in a company's own careers page
    if "gh_jid=" in (parsed.query or ""):
        return "Greenhouse"
    return "Other/Unknown"


def classify_sponsorship(text: str, signals: Dict[str, Iterable[str]]) -> str:
    t = text.lower()
    # Negative signals override positive ones ("no sponsorship" contains
    # "sponsorship", so this order matters).
    if any(sig.lower() in t for sig in signals.get("negative", [])):
        return "Likely no sponsor"
    if any(sig.lower() in t for sig in signals.get("positive", [])):
        return "Sponsor-friendly"
    return "Unknown"
