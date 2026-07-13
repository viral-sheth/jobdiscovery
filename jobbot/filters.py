import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

US_STATE_ABBREVS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}

US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire",
    "new jersey", "new mexico", "new york", "north carolina", "north dakota",
    "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west virginia", "wisconsin", "wyoming",
}


def title_matches_keywords(title: str, keywords: Iterable[str]) -> bool:
    t = title.lower()
    return any(kw.lower() in t for kw in keywords)


def title_is_excluded(title: str, exclude_terms: Iterable[str]) -> bool:
    t = title.lower()
    for term in exclude_terms:
        if re.search(r"\b" + re.escape(term.lower()) + r"\b", t):
            return True
    return False


def is_recent(posted_at: Optional[datetime], max_age_hours: int) -> bool:
    """Jobs with no timestamp pass (their source already filtered by date)."""
    if posted_at is None:
        return True
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return posted_at >= cutoff


NON_US_MARKERS = re.compile(
    r"united kingdom|\buk\b|canada|india|germany|france|ireland|netherlands|"
    r"poland|spain|portugal|italy|brazil|mexico|colombia|argentina|japan|"
    r"china|korea|singapore|australia|new zealand|israel|emea|europe|apac|"
    r"latam|london|dublin|toronto|vancouver|montreal|berlin|munich|paris|"
    r"amsterdam|warsaw|madrid|lisbon|zurich|stockholm|copenhagen|bangalore|"
    r"bengaluru|hyderabad|mumbai|delhi|tokyo|osaka|seoul|sydney|melbourne|"
    r"tel aviv|dubai|singapore|hong kong|taipei|sao paulo|mexico city|bogota")


def location_is_us(location: str) -> bool:
    """Heuristic US-location check for ATS boards that list jobs globally."""
    loc = location.lower().strip()
    if not loc:
        return False
    if NON_US_MARKERS.search(loc):
        return False
    if any(marker in loc for marker in
           ("united states", "usa", "u.s.", " us)", ", us", "- us", "us-")):
        return True
    if "remote" in loc:
        return True
    if any(name in loc for name in US_STATE_NAMES):
        return True
    # Trailing state abbreviation, e.g. "New York, NY" or "Austin, TX (Hybrid)"
    for token in re.findall(r"\b[A-Z]{2}\b", location):
        if token in US_STATE_ABBREVS:
            return True
    return False
