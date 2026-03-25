"""
Data models for cross-document linking graph.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class IdentificationStatus(Enum):
    IDENTIFIED = "identified"  # 100% confidence via strong ID
    LIKELY = "likely"  # High confidence via accumulated weak IDs
    CANDIDATE = "candidate"  # Possible match, needs more data
    AMBIGUOUS = "ambiguous"  # Multiple equally likely candidates
    UNKNOWN = "unknown"  # No matches found


@dataclass
class ProfileCandidate:
    """A potential profile match for a document."""
    profile_id: str
    likelihood: float  # 0.0 - 1.0
    matching_piis: List[str]  # PII types that matched
    matching_values: Dict[str, str]  # PII type -> value
    weight_score: float  # Sum of weights from matching PIIs


@dataclass
class DocumentNode:
    """A document in the linking graph."""
    document_id: str
    pii_values: Dict[str, str]  # PII type -> value
    candidates: List[ProfileCandidate] = field(default_factory=list)
    status: IdentificationStatus = IdentificationStatus.UNKNOWN
    identified_profile: Optional[str] = None
    identified_via: Optional[str] = None  # "strong_id" or "accumulated_weak"
    grouped_with: List[str] = field(default_factory=list)  # Other doc IDs in same group


@dataclass
class DocumentGroup:
    """A group of documents determined to be about/from the same person."""
    group_id: str
    document_ids: List[str]
    grouping_reason: str  # LLM's explanation
    combined_pii_values: Dict[str, str]  # Merged PII from all docs
    candidates: List[ProfileCandidate] = field(default_factory=list)
    status: IdentificationStatus = IdentificationStatus.UNKNOWN
    identified_profile: Optional[str] = None


@dataclass
class LinkingResult:
    """Result of the cross-document linking process."""
    # Phase 1 results: deterministically identified
    identified_profiles: Dict[str, List[str]]  # profile_id -> [doc_ids]
    enrichments: Dict[str, Dict[str, str]]  # profile_id -> {pii_type: value}
    
    # Phase 2 results: document graph with candidates
    document_nodes: Dict[str, DocumentNode]  # doc_id -> DocumentNode
    document_groups: List[DocumentGroup]
    
    # Summary stats
    total_documents: int = 0
    identified_count: int = 0
    likely_count: int = 0
    candidate_count: int = 0
    ambiguous_count: int = 0
