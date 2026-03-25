"""
Step 3: Visualization component showing profile completeness.
"""

from typing import List
from src.extraction.models import Profile


class Dashboard:
    """Displays profile completeness as progress bars."""
    
    def __init__(self, bar_width: int = 40):
        self.bar_width = bar_width
    
    def display(self, profiles: List[Profile]):
        """
        Display profile completeness as progress bars in terminal.
        
        Args:
            profiles: List of profiles to visualize
        """
        # TODO: Implement visualization
        print("PROFILE COMPLETENESS DASHBOARD goes here")
