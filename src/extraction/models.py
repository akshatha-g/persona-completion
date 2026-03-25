"""
Data models for PII extraction and profile management.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PIISpan:
    """Represents a detected PII span in a document."""
    pii_type: str          # e.g., "name", "email", "phone", "ssn"
    value: str             # The actual PII value
    start_offset: int      # Start position in document
    end_offset: int        # End position in document
    confidence: float = 1.0


@dataclass
class Document:
    """Represents a scraped document with PII detections."""
    document_id: str
    content: str
    pii_spans: List[PIISpan] = field(default_factory=list)


@dataclass
class Profile:
    """Represents a profile extracted from documents."""
    document_id: str
    profile_id: str
    piis_detected: List[str]           # List of PII types found
    profile_completion_pct: float      # 0-100 percentage
    pii_values: dict = field(default_factory=dict)  # PII type -> value mapping
    linked_document_ids: List[str] = field(default_factory=list)
