"""
Step 1: Process documents with PII span data and generate profile database.
"""

import json
import os
from typing import List, Dict, Set
from collections import defaultdict
from .models import Profile
from .persona_config import PERSONA_TRAIT_SETS, PII_TYPE_ALIASES


class PIIProcessor:
    """Processes documents with PII detections and generates profiles."""
    
    def __init__(self, trait_sets: List[Dict] = None):
        self.trait_sets = trait_sets or PERSONA_TRAIT_SETS
        self.aliases = PII_TYPE_ALIASES
    
    def process_documents(self, input_dir: str) -> List[Profile]:
        """
        Process all documents in input directory and extract profiles.
        
        Args:
            input_dir: Path to directory containing input JSON files
            
        Returns:
            List of Profile objects
        """
        all_profiles: Dict[str, Profile] = {}  # document_id -> Profile
        
        for filename in os.listdir(input_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(input_dir, filename)
                with open(filepath, "r") as f:
                    data = json.load(f)
                
                # Handle both single doc and array of docs
                docs = data if isinstance(data, list) else [data]
                
                for doc in docs:
                    doc_profiles = self._process_document(doc)
                    # Each document is its own profile (no merging by persona_id)
                    for profile in doc_profiles:
                        all_profiles[profile.document_id] = profile
        
        # Don't merge by profile_id - each document is independent
        # profile_id in input is ground truth for evaluation only
        return list(all_profiles.values())
    
    def _process_document(self, doc_data: dict) -> List[Profile]:
        """Process a single document - each document is its own profile initially."""
        document_id = doc_data.get("id", doc_data.get("document_id", "unknown"))
        pii_spans = doc_data.get("pii_spans", [])
        
        # Ground truth profile_id for evaluation (not used for linking)
        ground_truth_id = doc_data.get("persona_id", doc_data.get("profile_id"))
        
        # Collect all PIIs from this document (ignore profile_id in spans)
        piis: Set[str] = set()
        pii_values: Dict[str, str] = {}
        
        for span in pii_spans:
            pii_type = span.get("pii_type")
            pii_value = span.get("value")
            
            if pii_type:
                piis.add(pii_type)
                pii_values[pii_type] = pii_value
        
        # Each document starts as its own profile
        piis_detected = list(piis)
        completion_pct = self._calculate_completion(piis_detected)
        
        profile = Profile(
            document_id=document_id,
            profile_id=document_id,  # Use doc_id as initial profile_id
            piis_detected=piis_detected,
            profile_completion_pct=completion_pct,
            pii_values=pii_values,
            linked_document_ids=[document_id],
            ground_truth_id=ground_truth_id  # For evaluation
        )
        
        return [profile]
    
    def _merge_profile(self, existing: Profile, new: Profile):
        """Merge new profile data into existing profile."""
        existing.piis_detected = list(set(existing.piis_detected) | set(new.piis_detected))
        existing.pii_values.update(new.pii_values)
        if new.document_id not in existing.linked_document_ids:
            existing.linked_document_ids.append(new.document_id)
    
    def _calculate_completion(self, detected_piis: List[str]) -> float:
        """
        Calculate profile completion as max percentage across all trait sets.
        
        For each trait set, calculates what % of required traits are present.
        Returns the maximum percentage across all trait sets.
        
        Example:
            - If you have "name" -> matches set 1 (50%), set 5 (33%) -> returns 50%
            - If you have "social_media_handle" -> matches set 3 (100%) -> returns 100%
        """
        if not detected_piis:
            return 0.0
        
        # Normalize detected PIIs using aliases
        normalized_piis: Set[str] = set()
        for pii in detected_piis:
            canonical = self.aliases.get(pii.lower(), pii.lower())
            normalized_piis.add(canonical)
        
        # Calculate completion for each trait set
        max_completion = 0.0
        
        for trait_set in self.trait_sets:
            traits = trait_set["traits"]
            if not traits:
                continue
            
            matched = sum(1 for trait in traits if trait in normalized_piis)
            completion = (matched / len(traits)) * 100
            max_completion = max(max_completion, completion)
        
        return round(max_completion, 2)
    
    def save_profiles(self, profiles: List[Profile], output_path: str):
        """Save profiles to JSON file."""
        data = [
            {
                "document_id": p.document_id,
                "profile_id": p.profile_id,
                "ground_truth_id": p.ground_truth_id,  # For evaluation
                "piis_detected": p.piis_detected,
                "pii_values": p.pii_values,
                "profile_completion_pct": p.profile_completion_pct,
                "linked_document_ids": p.linked_document_ids
            }
            for p in profiles
        ]
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
