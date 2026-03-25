"""
Step 2: Cross-document profile linking.

Two-phase approach:
1. Deterministic: Link documents sharing strong identifiers (email, phone, ssn, etc.)
2. Contextual: Use LLM to find matches based on accumulated weak identifiers
"""

import os
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from src.extraction.models import Profile
from src.linking.linking_config import STRONG_IDENTIFIERS, WEAK_IDENTIFIERS, IDENTIFICATION_THRESHOLD
from src.linking.linking_models import (
    DocumentNode, DocumentGroup, ProfileCandidate, 
    LinkingResult, IdentificationStatus
)


class ProfileLinker:
    """Links profiles across documents using two-phase linking."""
    
    def __init__(self, use_llm: bool = True, llm_model: str = "gpt-4o-mini"):
        # Normalize strong ID keys to lowercase for matching
        self.strong_ids = {k.lower().replace("'s", "").replace(" ", "_"): v 
                          for k, v in STRONG_IDENTIFIERS.items()}
        # Enable LLM if API key is set OR mock mode is enabled
        self.use_llm = use_llm and (
            os.getenv("OPENAI_API_KEY") is not None or 
            os.getenv("LLM_MOCK", "").lower() == "true"
        )
        self.llm_model = llm_model
        self._llm_client = None
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
    
    @property
    def llm_client(self):
        """Lazy initialization of LLM client."""
        if self._llm_client is None and self.use_llm:
            from src.linking.llm_client import LLMClient
            self._llm_client = LLMClient(model=self.llm_model)
        return self._llm_client
    
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
        
        # Track Phase 1 metrics before Phase 2
        phase1_linked = [p for p in merged_profiles if len(p.linked_document_ids) > 1]
        phase1_linked_profiles = len(phase1_linked)
        phase1_docs_merged = sum(len(p.linked_document_ids) for p in phase1_linked)
        
        # Build document nodes for Phase 2
        document_nodes = self._build_document_nodes(merged_profiles, identified_map)
        
        # Phase 2: LLM Contextual matching
        print("\n=== Phase 2: LLM Contextual Matching ===")
        unidentified_docs = [doc_id for doc_id, node in document_nodes.items() 
                           if node.status != IdentificationStatus.IDENTIFIED]
        
        phase2_linked_profiles = 0
        phase2_docs_merged = 0
        document_groups = []
        
        if unidentified_docs and self.use_llm:
            print(f"  Analyzing {len(unidentified_docs)} unidentified documents...")
            merged_profiles, document_groups, phase2_linked, phase2_merged, new_enrichments = (
                self._llm_contextual_matching(merged_profiles, unidentified_docs, document_nodes)
            )
            phase2_linked_profiles = phase2_linked
            phase2_docs_merged = phase2_merged
            enrichments.update(new_enrichments)
            print(f"  LLM linked {phase2_linked_profiles} profile groups ({phase2_docs_merged} docs)")
        elif unidentified_docs:
            print(f"  {len(unidentified_docs)} unidentified docs (LLM disabled - set OPENAI_API_KEY)")
            # Fall back to heuristic matching
            document_nodes = self._heuristic_matching(document_nodes, merged_profiles)
        else:
            print("  All documents already identified via strong IDs")
        
        # Calculate final metrics
        total_documents = len(profiles)
        total_profiles = len(merged_profiles)
        
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
    
    def _llm_contextual_matching(
        self,
        profiles: List[Profile],
        unidentified_doc_ids: List[str],
        document_nodes: Dict[str, DocumentNode]
    ) -> Tuple[List[Profile], List[DocumentGroup], int, int, Dict[str, Dict[str, str]]]:
        """
        Phase 2: Use LLM to find matches among unidentified documents.
        
        Returns:
            Tuple of (updated profiles, document groups, linked count, docs merged, enrichments)
        """
        from src.linking.llm_client import LLMClient
        
        # Build index of unidentified docs by their PII values
        unid_profiles = {p.profile_id: p for p in profiles 
                        if p.profile_id in unidentified_doc_ids}
        
        # Find candidate pairs based on weak identifier overlap
        candidate_pairs = self._find_candidate_pairs(unid_profiles)
        print(f"  Found {len(candidate_pairs)} candidate pairs to analyze")
        
        if not candidate_pairs:
            return profiles, [], 0, 0, {}
        
        # Use LLM to analyze pairs
        llm = self.llm_client
        matched_pairs = []
        
        # Limit to avoid too many API calls (configurable)
        max_pairs = int(os.getenv("MAX_LLM_PAIRS", "50"))
        pairs_to_analyze = candidate_pairs[:max_pairs]
        
        for i, (doc1_id, doc2_id) in enumerate(pairs_to_analyze):
            if (i + 1) % 10 == 0:
                print(f"    Analyzed {i + 1}/{len(pairs_to_analyze)} pairs...")
            
            doc1 = unid_profiles.get(doc1_id)
            doc2 = unid_profiles.get(doc2_id)
            
            if not doc1 or not doc2:
                continue
            
            result = llm.analyze_match(
                doc1.pii_values, doc2.pii_values,
                doc1_id, doc2_id
            )
            
            if result.is_same_person and result.confidence >= 0.7:
                matched_pairs.append((doc1_id, doc2_id, result))
        
        print(f"  LLM confirmed {len(matched_pairs)} matches")
        
        if not matched_pairs:
            return profiles, [], 0, 0, {}
        
        # Build groups from matched pairs using Union-Find
        groups = self._build_groups_from_pairs(matched_pairs, unid_profiles)
        
        # Merge profiles within each group
        merged_profiles, document_groups, enrichments = self._merge_llm_groups(
            profiles, groups, matched_pairs
        )
        
        linked_count = len([g for g in groups if len(g) > 1])
        docs_merged = sum(len(g) for g in groups if len(g) > 1)
        
        return merged_profiles, document_groups, linked_count, docs_merged, enrichments
    
    def _find_candidate_pairs(
        self, 
        profiles: Dict[str, Profile]
    ) -> List[Tuple[str, str]]:
        """Find candidate pairs based on weak identifier overlap."""
        # Build inverted index: pii_value -> [profile_ids]
        value_index = defaultdict(set)
        
        for profile_id, profile in profiles.items():
            for pii_type, value in profile.pii_values.items():
                if value:
                    # Normalize value
                    norm_value = f"{pii_type.lower()}:{value.lower().strip()}"
                    value_index[norm_value].add(profile_id)
        
        # Find pairs that share at least 2 weak identifiers
        pair_overlap = defaultdict(int)
        
        for profiles_with_value in value_index.values():
            if len(profiles_with_value) > 1 and len(profiles_with_value) < 50:  # Avoid too common values
                profiles_list = list(profiles_with_value)
                for i in range(len(profiles_list)):
                    for j in range(i + 1, len(profiles_list)):
                        pair = tuple(sorted([profiles_list[i], profiles_list[j]]))
                        pair_overlap[pair] += 1
        
        # Return pairs with at least 2 overlapping values, sorted by overlap count
        candidates = [(p[0], p[1]) for p, count in pair_overlap.items() if count >= 2]
        candidates.sort(key=lambda p: pair_overlap[tuple(sorted(p))], reverse=True)
        
        return candidates
    
    def _build_groups_from_pairs(
        self,
        matched_pairs: List[Tuple[str, str, any]],
        profiles: Dict[str, Profile]
    ) -> List[Set[str]]:
        """Build connected groups from matched pairs using Union-Find."""
        profile_ids = list(profiles.keys())
        id_to_idx = {pid: i for i, pid in enumerate(profile_ids)}
        n = len(profile_ids)
        parent = list(range(n))
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        for doc1_id, doc2_id, _ in matched_pairs:
            if doc1_id in id_to_idx and doc2_id in id_to_idx:
                union(id_to_idx[doc1_id], id_to_idx[doc2_id])
        
        # Group by root
        groups = defaultdict(set)
        for pid in profile_ids:
            groups[find(id_to_idx[pid])].add(pid)
        
        return [g for g in groups.values() if len(g) > 1]
    
    def _merge_llm_groups(
        self,
        all_profiles: List[Profile],
        groups: List[Set[str]],
        matched_pairs: List[Tuple[str, str, any]]
    ) -> Tuple[List[Profile], List[DocumentGroup], Dict[str, Dict[str, str]]]:
        """Merge profiles in LLM-identified groups."""
        profile_map = {p.profile_id: p for p in all_profiles}
        merged_ids = set()
        document_groups = []
        enrichments = {}
        
        for group in groups:
            group_list = list(group)
            canonical_id = group_list[0]
            canonical = profile_map.get(canonical_id)
            
            if not canonical:
                continue
            
            # Merge all profiles in group
            combined_pii = canonical.pii_values.copy()
            all_doc_ids = list(canonical.linked_document_ids or [canonical.document_id])
            all_pii_types = set(canonical.piis_detected)
            
            for other_id in group_list[1:]:
                other = profile_map.get(other_id)
                if other:
                    merged_ids.add(other_id)
                    all_doc_ids.extend(other.linked_document_ids or [other.document_id])
                    all_pii_types.update(other.piis_detected)
                    for pii_type, value in other.pii_values.items():
                        if pii_type not in combined_pii and value:
                            combined_pii[pii_type] = value
            
            # Update canonical profile
            canonical.pii_values = combined_pii
            canonical.linked_document_ids = list(set(all_doc_ids))
            canonical.piis_detected = list(all_pii_types)
            
            # Track enrichments
            original_piis = set(profile_map[canonical_id].pii_values.keys())
            new_piis = {k: v for k, v in combined_pii.items() if k not in original_piis}
            if new_piis:
                enrichments[canonical_id] = new_piis
            
            # Create DocumentGroup
            doc_group = DocumentGroup(
                group_id=f"llm_group_{canonical_id}",
                document_ids=all_doc_ids,
                grouping_reason="LLM contextual analysis",
                combined_pii_values=combined_pii,
                status=IdentificationStatus.LIKELY,
                identified_profile=canonical_id
            )
            document_groups.append(doc_group)
        
        # Filter out merged profiles
        final_profiles = [p for p in all_profiles if p.profile_id not in merged_ids]
        
        return final_profiles, document_groups, enrichments
    
    def _heuristic_matching(
        self, 
        document_nodes: Dict[str, DocumentNode],
        profiles: List[Profile]
    ) -> Dict[str, DocumentNode]:
        """
        Fallback heuristic matching when LLM is disabled.
        
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
