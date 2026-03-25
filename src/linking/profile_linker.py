"""
Step 2: Cross-document profile linking.

Two-phase approach:
1. Deterministic: Link documents sharing strong identifiers (email, phone, ssn, etc.)
2. Contextual: Use LLM to find matches based on accumulated weak identifiers
"""

from typing import List, Dict, Set, Tuple
from collections import defaultdict
from src.extraction.models import Profile
from src.linking.linking_config import STRONG_IDENTIFIERS, WEAK_IDENTIFIERS, IDENTIFICATION_THRESHOLD
from src.linking.linking_models import (
    DocumentNode, DocumentGroup, ProfileCandidate, 
    LinkingResult, IdentificationStatus
)


class ProfileLinker:
    """Links profiles across documents using two-phase linking."""
    
    def __init__(self):
        # Normalize strong ID keys to lowercase for matching
        self.strong_ids = {k.lower().replace("'s", "").replace(" ", "_"): v 
                          for k, v in STRONG_IDENTIFIERS.items()}
        # Also add common aliases
        self.strong_id_aliases = {
            "email": "email_address",
            "phone": "phone_number",
            "ssn": "national_id",
            "passport": "passport_number",
            "drivers_license": "drivers_license",
            "social_media_handle": "social_media_handles",
        }
        self.weak_ids = WEAK_IDENTIFIERS
    
    def link_profiles(self, profiles: List[Profile]) -> Tuple[List[Profile], LinkingResult]:
        """
        Link profiles across documents.
        
        Phase 1: Deterministic linking via strong identifiers
        Phase 2: Contextual matching via LLM (placeholder for now)
        
        Returns:
            Tuple of (merged profiles list, linking result with graph)
        """
        print("\n=== Phase 1: Deterministic Linking ===")
        
        # Build inverted index: {pii_type: {value: [profile indices]}}
        strong_index = self._build_strong_id_index(profiles)
        
        # Find connected components (profiles that share any strong ID)
        profile_groups = self._find_connected_profiles(profiles, strong_index)
        
        # Merge profiles in each group
        merged_profiles, identified_map, enrichments = self._merge_profile_groups(
            profiles, profile_groups
        )
        
        print(f"  Found {len(profile_groups)} profile groups from {len(profiles)} profiles")
        print(f"  Merged into {len(merged_profiles)} distinct profiles")
        
        # Build document nodes for Phase 2
        document_nodes = self._build_document_nodes(merged_profiles, identified_map)
        
        # Phase 2: Contextual matching using weak identifiers
        print("\n=== Phase 2: Contextual Matching ===")
        unidentified_docs = [doc_id for doc_id, node in document_nodes.items() 
                           if node.status != IdentificationStatus.IDENTIFIED]
        
        if unidentified_docs:
            document_nodes = self._contextual_matching(document_nodes, merged_profiles)
            print(f"  Processed {len(unidentified_docs)} unidentified documents")
        else:
            print("  All documents already identified via strong IDs")
        
        document_groups = []  # Will be populated by LLM grouping in future
        
        # Calculate metrics
        total_documents = len(profiles)
        total_profiles = len(merged_profiles)
        
        # Phase 1 metrics
        phase1_linked = [p for p in merged_profiles if len(p.linked_document_ids) > 1]
        phase1_linked_profiles = len(phase1_linked)
        phase1_docs_merged = sum(len(p.linked_document_ids) for p in phase1_linked)
        
        # Phase 2 metrics (placeholder - currently 0, will be populated when LLM is added)
        phase2_linked_profiles = 0
        phase2_docs_merged = 0
        
        # Unlinked = singletons
        unlinked_profiles = sum(1 for p in merged_profiles if len(p.linked_document_ids) == 1)
        
        # Build result
        result = LinkingResult(
            identified_profiles=identified_map,
            enrichments=enrichments,
            document_nodes=document_nodes,
            document_groups=document_groups,
            total_documents=total_documents,
            total_profiles=total_profiles,
            phase1_linked_profiles=phase1_linked_profiles,
            phase1_docs_merged=phase1_docs_merged,
            phase2_linked_profiles=phase2_linked_profiles,
            phase2_docs_merged=phase2_docs_merged,
            unlinked_profiles=unlinked_profiles,
        )
        
        return merged_profiles, result
    
    def _build_strong_id_index(self, profiles: List[Profile]) -> Dict[str, Dict[str, List[int]]]:
        """Build inverted index of strong identifier values to profile indices."""
        index = defaultdict(lambda: defaultdict(list))
        
        for i, profile in enumerate(profiles):
            for pii_type, value in profile.pii_values.items():
                pii_type_lower = pii_type.lower().replace("'s", "").replace(" ", "_")
                
                # Check if it's a strong ID (direct match or via alias)
                is_strong = (pii_type_lower in self.strong_ids or 
                            pii_type_lower in self.strong_id_aliases or
                            self.strong_id_aliases.get(pii_type_lower) in self.strong_ids)
                
                if is_strong and value:
                    # Normalize value for matching
                    normalized = self._normalize_value(pii_type_lower, value)
                    index[pii_type_lower][normalized].append(i)
        
        return index
    
    def _normalize_value(self, pii_type: str, value: str) -> str:
        """Normalize a PII value for comparison."""
        value = value.strip().lower()
        
        if pii_type == "phone":
            # Remove non-digits
            value = ''.join(c for c in value if c.isdigit())
        elif pii_type == "email":
            # Already lowercased
            pass
        elif pii_type == "ssn":
            # Remove dashes
            value = value.replace("-", "")
        
        return value
    
    def _find_connected_profiles(
        self, 
        profiles: List[Profile], 
        strong_index: Dict[str, Dict[str, List[int]]]
    ) -> List[Set[int]]:
        """Find connected components of profiles sharing strong IDs (Union-Find)."""
        n = len(profiles)
        parent = list(range(n))
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        # Union profiles that share any strong ID value
        for pii_type, value_map in strong_index.items():
            for value, profile_indices in value_map.items():
                if len(profile_indices) > 1:
                    first = profile_indices[0]
                    for other in profile_indices[1:]:
                        union(first, other)
        
        # Group by root
        groups = defaultdict(set)
        for i in range(n):
            groups[find(i)].add(i)
        
        return list(groups.values())
    
    def _merge_profile_groups(
        self, 
        profiles: List[Profile], 
        groups: List[Set[int]]
    ) -> Tuple[List[Profile], Dict[str, List[str]], Dict[str, Dict[str, str]]]:
        """Merge profiles within each group, enriching with combined PII."""
        merged = []
        identified_map = {}  # profile_id -> [doc_ids]
        enrichments = {}  # profile_id -> {pii_type: value}
        
        for group in groups:
            group_profiles = [profiles[i] for i in group]
            
            # Use the first profile's ID as canonical
            canonical = group_profiles[0]
            
            # Merge all PII values
            combined_pii: Dict[str, str] = {}
            all_pii_types: Set[str] = set()
            all_doc_ids: List[str] = []
            
            for p in group_profiles:
                all_doc_ids.append(p.document_id)
                all_pii_types.update(p.piis_detected)
                for pii_type, value in p.pii_values.items():
                    if pii_type not in combined_pii and value:
                        combined_pii[pii_type] = value
            
            # Create merged profile
            merged_profile = Profile(
                document_id=canonical.document_id,
                profile_id=canonical.profile_id,
                piis_detected=list(all_pii_types),
                profile_completion_pct=canonical.profile_completion_pct,  # Recalc later
                pii_values=combined_pii,
                linked_document_ids=all_doc_ids
            )
            merged.append(merged_profile)
            
            # Track identification
            identified_map[canonical.profile_id] = all_doc_ids
            
            # Track enrichments (new PIIs from linked docs)
            if len(group_profiles) > 1:
                original_piis = set(canonical.pii_values.keys())
                new_piis = {k: v for k, v in combined_pii.items() if k not in original_piis}
                if new_piis:
                    enrichments[canonical.profile_id] = new_piis
        
        return merged, identified_map, enrichments
    
    def _build_document_nodes(
        self, 
        profiles: List[Profile], 
        identified_map: Dict[str, List[str]]
    ) -> Dict[str, DocumentNode]:
        """Build document nodes for the linking graph."""
        nodes = {}
        
        for profile in profiles:
            # Check if this profile was identified via strong ID (has strong ID values)
            has_strong_id = self._has_strong_identifier(profile.pii_values)
            
            for doc_id in profile.linked_document_ids or [profile.document_id]:
                node = DocumentNode(
                    document_id=doc_id,
                    pii_values=profile.pii_values.copy(),
                    status=IdentificationStatus.IDENTIFIED if has_strong_id else IdentificationStatus.UNKNOWN,
                    identified_profile=profile.profile_id if has_strong_id else None,
                    identified_via="strong_id" if has_strong_id else None,
                    grouped_with=[d for d in (profile.linked_document_ids or []) if d != doc_id]
                )
                nodes[doc_id] = node
        
        return nodes
    
    def _has_strong_identifier(self, pii_values: Dict[str, str]) -> bool:
        """Check if profile has any strong identifier values."""
        for pii_type in pii_values.keys():
            pii_key = pii_type.lower().replace("'s", "").replace(" ", "_")
            if (pii_key in self.strong_ids or 
                pii_key in self.strong_id_aliases or
                self.strong_id_aliases.get(pii_key) in self.strong_ids):
                return True
        return False
    
    def _contextual_matching(
        self, 
        document_nodes: Dict[str, DocumentNode],
        profiles: List[Profile]
    ) -> Dict[str, DocumentNode]:
        """
        Phase 2: Match unidentified documents to profiles using weak identifiers.
        
        Uses a browser-fingerprinting approach where combinations of innocuous
        data points can uniquely identify a person.
        """
        # Normalize weak ID keys
        weak_weights = {
            k.lower().replace("'s", "").replace(" ", "_"): v["weight"] 
            for k, v in WEAK_IDENTIFIERS.items()
        }
        weak_weights.update({
            "first_name": 5, "last_name": 10, "age": 8,
            "nationality": 3, "employer": 12, "birth_city": 15
        })
        
        for doc_id, node in document_nodes.items():
            if node.status == IdentificationStatus.IDENTIFIED:
                continue
            
            candidates = []
            
            for profile in profiles:
                matching_piis = []
                matching_values = {}
                weight_score = 0.0
                
                for pii_type, value in node.pii_values.items():
                    pii_key = pii_type.lower().replace("'s", "").replace(" ", "_")
                    profile_value = profile.pii_values.get(pii_type)
                    
                    if profile_value and self._values_match(pii_key, value, profile_value):
                        matching_piis.append(pii_type)
                        matching_values[pii_type] = value
                        weight_score += weak_weights.get(pii_key, 5)
                
                if matching_piis:
                    candidates.append(ProfileCandidate(
                        profile_id=profile.profile_id,
                        likelihood=min(weight_score / IDENTIFICATION_THRESHOLD, 1.0),
                        matching_piis=matching_piis,
                        matching_values=matching_values,
                        weight_score=weight_score
                    ))
            
            # Sort by weight score
            candidates.sort(key=lambda c: c.weight_score, reverse=True)
            node.candidates = candidates[:5]  # Top 5 candidates
            
            # Determine status based on top candidates
            if candidates:
                top = candidates[0]
                if top.weight_score >= IDENTIFICATION_THRESHOLD:
                    # Check if there's ambiguity (multiple high scorers)
                    high_scorers = [c for c in candidates 
                                   if c.weight_score >= IDENTIFICATION_THRESHOLD * 0.9]
                    if len(high_scorers) > 1:
                        node.status = IdentificationStatus.AMBIGUOUS
                    else:
                        node.status = IdentificationStatus.LIKELY
                        node.identified_profile = top.profile_id
                        node.identified_via = "accumulated_weak"
                elif top.weight_score >= IDENTIFICATION_THRESHOLD * 0.5:
                    node.status = IdentificationStatus.CANDIDATE
                else:
                    node.status = IdentificationStatus.UNKNOWN
        
        return document_nodes
    
    def _values_match(self, pii_type: str, val1: str, val2: str) -> bool:
        """Check if two PII values match (with type-specific normalization)."""
        if not val1 or not val2:
            return False
        
        v1 = val1.strip().lower()
        v2 = val2.strip().lower()
        
        if pii_type in ("phone", "phone_number", "work_phone"):
            v1 = ''.join(c for c in v1 if c.isdigit())
            v2 = ''.join(c for c in v2 if c.isdigit())
        elif pii_type in ("email", "email_address", "work_email"):
            pass  # Already lowercased
        elif pii_type in ("age",):
            # Allow age ±1 to match
            try:
                return abs(int(v1) - int(v2)) <= 1
            except ValueError:
                return v1 == v2
        
        return v1 == v2
