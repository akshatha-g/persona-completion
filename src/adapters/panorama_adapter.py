"""
Adapter to convert panorama_sample.json into snapshot format.

Each document represents a point in time. We create incremental snapshots
showing the cumulative state of detected PIIs as documents are processed.
"""

import json
from datetime import date, timedelta
from typing import Dict, List, Set
from collections import defaultdict

from src.extraction.persona_config import PII_TYPE_ALIASES


def load_panorama_data(filepath: str) -> List[dict]:
    """Load panorama sample JSON."""
    with open(filepath, 'r') as f:
        return json.load(f)


def normalize_pii_type(pii_type: str) -> str:
    """Convert PII type to canonical form."""
    return PII_TYPE_ALIASES.get(pii_type.lower(), pii_type.lower().replace(' ', '_').replace("'", ''))


def build_incremental_snapshots(documents: List[dict], snapshot_interval: int = 50) -> List[dict]:
    """
    Build incremental snapshots as documents are processed.

    Args:
        documents: List of panorama documents
        snapshot_interval: Create a snapshot every N documents

    Returns:
        List of snapshots showing cumulative state
    """
    # Track cumulative state per persona
    personas = defaultdict(lambda: {
        'detected_piis': set(),
        'full_profile': {},
        'source_documents': [],
        'label': None,
        'first_seen': None
    })

    snapshots = []
    base_date = date(2025, 1, 1)

    for i, doc in enumerate(documents):
        persona_id = doc['persona_id']

        # First time seeing this persona?
        if personas[persona_id]['first_seen'] is None:
            personas[persona_id]['first_seen'] = len(snapshots)

        # Add document to sources
        personas[persona_id]['source_documents'].append(doc['id'])

        # Aggregate detected PIIs
        for span in doc.get('pii_spans', []):
            normalized = normalize_pii_type(span['pii_type'])
            personas[persona_id]['detected_piis'].add(normalized)

        # Store full profile (ground truth)
        if doc.get('full_profile') and not personas[persona_id]['full_profile']:
            personas[persona_id]['full_profile'] = doc['full_profile']
            first = doc['full_profile'].get('First Name', '')
            last = doc['full_profile'].get('Last Name', '')
            personas[persona_id]['label'] = f"{first} {last}".strip() or persona_id[:8]

        # Create snapshot at intervals
        if (i + 1) % snapshot_interval == 0 or i == len(documents) - 1:
            snapshot_num = len(snapshots) + 1
            snapshot_date = base_date + timedelta(days=snapshot_num * 7)  # Weekly snapshots

            snapshot = build_snapshot_from_state(
                personas,
                snapshot_id=f"snapshot_{snapshot_num:03d}",
                snapshot_date=snapshot_date.isoformat(),
                current_snapshot_idx=len(snapshots)
            )
            snapshots.append(snapshot)

    return snapshots


def build_snapshot_from_state(personas: Dict, snapshot_id: str, snapshot_date: str, current_snapshot_idx: int) -> dict:
    """Build a snapshot from current cumulative state."""
    profiles = {}

    field_mapping = {
        'Gender': 'gender',
        'Age': 'age',
        'Birth Date': 'birth_date',
        'Birth City': 'birth_city',
        'Nationality': 'nationality',
        'Address': 'address',
        'Marital Status': 'marital_status',
        'Spouse Name': 'spouse_name',
        'Children Count': 'children_count',
        "Father's Name": 'fathers_name',
        "Mother's Name": 'mothers_name',
        'Employer': 'employer',
        'Job Title': 'job_title',
        'Education Info': 'education_info',
        'Annual Salary': 'annual_salary',
        'Finance Status': 'finance_status',
        'Net Worth': 'net_worth',
        'Credit Score': 'credit_score',
        'Blood Type': 'blood_type',
        'Allergies': 'allergies',
        'Disability': 'disability',
        'Emergency Contact Name': 'emergency_contact_name',
        'Emergency Contact Phone': 'emergency_contact_phone',
        'Social Media Handles': 'social_media_handles',
    }

    for persona_id, data in personas.items():
        if not data['label']:  # Skip if not yet seen
            continue

        # Only include personal values for fields that were DETECTED
        # Map detected PII types to personal field keys
        detected = set(data['detected_piis'])
        values = {}
        full = data['full_profile']

        for src_key, dst_key in field_mapping.items():
            # Only populate if this field's PII type was detected
            if dst_key in detected:
                val = full.get(src_key)
                values[f"personal.{dst_key}"] = val if val else None
            else:
                values[f"personal.{dst_key}"] = None

        # Determine when this profile was first added
        first_snapshot_idx = data['first_seen']
        added_in = f"snapshot_{first_snapshot_idx + 1:03d}" if first_snapshot_idx is not None else snapshot_id

        profiles[persona_id] = {
            'meta': {
                'label': data['label'],
                'added_in': added_in,
                'source_documents': list(data['source_documents'])
            },
            'detected_piis': sorted(list(data['detected_piis'])),
            'values': values
        }

    return {
        'snapshot_id': snapshot_id,
        'snapshot_date': snapshot_date,
        'profiles': profiles
    }


def process_panorama_file(input_path: str, output_dir: str = None, interval: int = 50) -> List[dict]:
    """
    Process panorama_sample.json and create incremental snapshots.

    Args:
        input_path: Path to panorama_sample.json
        output_dir: Directory to save snapshot JSONs
        interval: Create snapshot every N documents

    Returns:
        List of generated snapshots
    """
    import os

    documents = load_panorama_data(input_path)
    snapshots = build_incremental_snapshots(documents, snapshot_interval=interval)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

        # Clear old panorama snapshots
        for f in os.listdir(output_dir):
            if f.startswith('snapshot_') and f.endswith('.json'):
                os.remove(os.path.join(output_dir, f))

        for snap in snapshots:
            path = os.path.join(output_dir, f"{snap['snapshot_id']}.json")
            with open(path, 'w') as f:
                json.dump(snap, f, indent=2)

        print(f"Created {len(snapshots)} snapshots in {output_dir}")
        print(f"  - {len(documents)} source documents")
        print(f"  - {len(snapshots[-1]['profiles'])} final profiles")

    return snapshots


if __name__ == '__main__':
    import sys
    input_path = sys.argv[1] if len(sys.argv) > 1 else 'data/panorama_sample.json'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'data/snapshots'
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    process_panorama_file(input_path, output_dir, interval)
