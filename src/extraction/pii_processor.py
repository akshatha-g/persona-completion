"""
Step 1: Process documents with PII span data and generate profile database.
"""

import json
import os
from typing import List
from .models import Document, Profile, PIISpan


# Define which PII types contribute to a "complete" profile
PROFILE_PII_TYPES = [
    "name",
    "email", 
    "phone",
    "address",
    "ssn",
    "date_of_birth",
    "employer",
    "occupation"
]


class PIIProcessor:
    """Processes documents with PII detections and generates profiles."""
    
    def __init__(self, pii_types: List[str] = None):
        self.pii_types = pii_types or PROFILE_PII_TYPES
    
    def process_documents(self, input_dir: str) -> List[Profile]:
        """
        Process all documents in input directory and extract profiles.
        
        Args:
            input_dir: Path to directory containing input JSON files
            
        Returns:
            List of Profile objects
        """
        profiles = []
        
        for filename in os.listdir(input_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(input_dir, filename)
                with open(filepath, "r") as f:
                    data = json.load(f)
                
                doc_profiles = self._process_document(data)
                profiles.extend(doc_profiles)
        
        return profiles
    
    def _process_document(self, doc_data: dict) -> List[Profile]:
        """Process a single document and extract profiles."""
        document_id = doc_data.get("document_id", "unknown")
        pii_spans = doc_data.get("pii_spans", [])
        
        # Group PIIs by profile (simplified: one profile per document for now)
        pii_types_found = set()
        pii_values = {}
        
        for span in pii_spans:
            pii_type = span.get("pii_type")
            pii_value = span.get("value")
            if pii_type:
                pii_types_found.add(pii_type)
                pii_values[pii_type] = pii_value
        
        # Calculate profile completion percentage
        completion_pct = self._calculate_completion(list(pii_types_found))
        
        profile = Profile(
            document_id=document_id,
            profile_id=f"profile_{document_id}",
            piis_detected=list(pii_types_found),
            profile_completion_pct=completion_pct,
            pii_values=pii_values
        )
        
        return [profile]
    
    def _calculate_completion(self, detected_piis: List[str]) -> float:
        """Calculate profile completion as percentage of expected PII types."""
        if not self.pii_types:
            return 0.0
        
        matched = sum(1 for pii in detected_piis if pii in self.pii_types)
        return round((matched / len(self.pii_types)) * 100, 2)
    
    def save_profiles(self, profiles: List[Profile], output_path: str):
        """Save profiles to JSON file."""
        data = [
            {
                "document_id": p.document_id,
                "profile_id": p.profile_id,
                "piis_detected": p.piis_detected,
                "profile_completion_pct": p.profile_completion_pct
            }
            for p in profiles
        ]
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
