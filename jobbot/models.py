from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    url: str
    title: str
    company: str
    location: str
    description: str = ""
    posted_at: Optional[datetime] = None
    source: str = ""
    interface: str = "Other/Unknown"
    sponsorship: str = "Unknown"
