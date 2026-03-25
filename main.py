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
    print("\n" + "="*50)
    print("LINKING SUMMARY")
    print("="*50)
    print(f"Total Documents:                    {linking_result.total_documents}")
    print(f"Total Profiles (after linking):     {linking_result.total_profiles}")
    print("-"*50)
    print(f"Phase 1 - Strong ID Linking:")
    print(f"  Linked profiles:                  {linking_result.phase1_linked_profiles}")
    print(f"  Documents merged:                 {linking_result.phase1_docs_merged}")
    print("-"*50)
    print(f"Phase 2 - LLM Contextual Linking:")
    print(f"  Linked profiles:                  {linking_result.phase2_linked_profiles}")
    print(f"  Documents merged:                 {linking_result.phase2_docs_merged}")
    print("-"*50)
    print(f"Unlinked Profiles (singletons):     {linking_result.unlinked_profiles}")
    print("="*50)
    
    if linking_result.enrichments:
        print(f"\nEnrichments from linking ({len(linking_result.enrichments)} profiles):")
        for profile_id, new_piis in list(linking_result.enrichments.items())[:10]:
            print(f"  {profile_id}: +{list(new_piis.keys())}")
        if len(linking_result.enrichments) > 10:
            print(f"  ... and {len(linking_result.enrichments) - 10} more")
    
    # Step 4: Re-visualize profile completeness (after linking)
    print("\n=== AFTER LINKING ===")
    dashboard.display(linked_profiles)
    
    # Save linked profiles
    processor.save_profiles(linked_profiles, "data/output/linked_profiles.json")
    print("\nSaved linked profiles to data/output/linked_profiles.json")


if __name__ == "__main__":
    main()
