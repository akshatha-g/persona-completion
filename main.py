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

    # Step 2: Visualize profile completeness (before linking)
    dashboard = Dashboard()
    print("\n=== BEFORE LINKING ===")
    dashboard.display(profiles)
    
    # Step 3: Link profiles across documents
    linker = ProfileLinker()
    linked_profiles, linking_result = linker.link_profiles(profiles)
    
    # Display linking summary
    print("\n=== LINKING SUMMARY ===")
    print(f"  Profiles with enrichments: {len(linking_result.enrichments)}")
    for profile_id, new_piis in linking_result.enrichments.items():
        print(f"    {profile_id}: +{list(new_piis.keys())}")
    
    # Step 4: Re-visualize profile completeness (after linking)
    print("\n=== AFTER LINKING ===")
    dashboard.display(linked_profiles)
    
    # Save linked profiles
    processor.save_profiles(linked_profiles, "data/output/linked_profiles.json")
    print("\nSaved linked profiles to data/output/linked_profiles.json")


if __name__ == "__main__":
    main()
