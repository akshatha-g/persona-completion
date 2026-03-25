"""
Step 2: Cross-document profile linking.
"""

from typing import List
from src.extraction.models import Profile


class ProfileLinker:
    """Links profiles across documents based on shared PII attributes."""
    
    def __init__(self, linking_keys: List[str] = None):
        # PII types used to determine if two profiles are the same person
        self.linking_keys = linking_keys or ["email", "phone", "ssn", "name"]
    
    def link_profiles(self, profiles: List[Profile]) -> List[Profile]:
        """
        Link profiles that share common PII values.
        
        Args:
            profiles: List of profiles extracted from documents
            
        Returns:
            List of merged/linked profiles
        """
        # TODO: Implement cross-document linking
        print("Linking profiles")
        return profiles
