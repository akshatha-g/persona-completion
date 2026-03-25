"""
Persona Completion - Entry Point
"""

from src.extraction.pii_processor import PIIProcessor
from src.linking.profile_linker import ProfileLinker
from src.visualization.dashboard import Dashboard


def main():
    # Step 1: Extract PIIs from documents
    processor = PIIProcessor()
    profiles = processor.process_documents("data/input")
    
    # Save profiles database to JSON
    processor.save_profiles(profiles, "data/output/profiles.json")
    print("Saved profiles database to data/output/profiles.json")

    # Step 2: Visualize profile completeness
    dashboard = Dashboard()
    dashboard.display(profiles)
    
    # Step 3: Link profiles across documents
    linker = ProfileLinker()
    linked_profiles = linker.link_profiles(profiles)
    
    # Step 4: Re-visualize profile completeness
    dashboard.display(linked_profiles)


if __name__ == "__main__":
    main()
