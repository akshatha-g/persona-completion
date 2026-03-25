"""
Compile all data sources into a unified dataset with failure case analysis.
"""
import json
import os
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), '../../data/data_sources')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../../data')


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    return json.load(open(path))


def load_jsonl(filename):
    path = os.path.join(DATA_DIR, filename)
    return [json.loads(line) for line in open(path)]


def compile_data():
    # Load all sources
    panorama = load_json('panorama_sample.json')
    dynamic = load_json('dynamic_characteristics.json')
    non_identifiable = load_json('non_identifiable_doc.json')
    ambiguous = load_jsonl('persona_ambiguity_head.json')

    # Compile summary
    summary = {
        'sources': {
            'panorama': {
                'count': len(panorama),
                'description': 'Clear persona matches with full PII detection'
            }
        },
        'total_documents': len(panorama) + len(dynamic) + len(non_identifiable) + len(ambiguous),
        'success_cases': len(panorama),
        'failure_cases': {
            'non_identifiable': len(non_identifiable),
            'dynamic_characteristics': len(dynamic),
            'ambiguous': len(ambiguous),
            'total': len(non_identifiable) + len(dynamic) + len(ambiguous)
        }
    }

    # Analyze non-identifiable cases
    non_id_analysis = []
    pii_type_counts = Counter()
    for doc in non_identifiable:
        piis = [s['pii_type'] for s in doc.get('pii_spans', [])]
        for p in piis:
            pii_type_counts[p] += 1
        non_id_analysis.append({
            'id': doc['id'],
            'pii_count': len(piis),
            'pii_types': piis,
            'text_preview': doc['document']['text'][:150] + '...'
        })

    summary['non_identifiable_analysis'] = {
        'avg_piis_per_doc': sum(d['pii_count'] for d in non_id_analysis) / len(non_id_analysis),
        'pii_type_distribution': dict(pii_type_counts.most_common(10)),
        'samples': non_id_analysis[:10]
    }

    # Analyze ambiguous cases
    amb_analysis = []
    for doc in ambiguous:
        matching_count = len(doc.get('matching_personas', {}))
        amb_analysis.append({
            'document_id': doc['document_id'],
            'detected_piis': doc['piis'],
            'matching_personas_count': matching_count,
            'matching_persona_names': [
                f"{p.get('First Name', '')} {p.get('Last Name', '')}"
                for p in list(doc.get('matching_personas', {}).values())[:3]
            ],
            'text_preview': doc['document']['text'][:150] + '...'
        })

    summary['ambiguous_analysis'] = {
        'avg_matching_personas': sum(d['matching_personas_count'] for d in amb_analysis) / len(amb_analysis),
        'samples': amb_analysis[:10]
    }

    # Analyze dynamic characteristics cases
    dyn_analysis = []
    dyn_pii_counts = Counter()
    for doc in dynamic:
        piis = [s['pii_type'] for s in doc.get('pii_spans', [])]
        for p in piis:
            dyn_pii_counts[p] += 1
        dyn_analysis.append({
            'id': doc['id'],
            'pii_count': len(piis),
            'pii_types': piis,
            'text_preview': doc['document']['text'][:150] + '...'
        })

    summary['dynamic_analysis'] = {
        'avg_piis_per_doc': sum(d['pii_count'] for d in dyn_analysis) / len(dyn_analysis),
        'pii_type_distribution': dict(dyn_pii_counts.most_common(10)),
        'samples': dyn_analysis[:10]
    }

    # Save compiled summary
    output_path = os.path.join(OUTPUT_DIR, 'compiled_summary.json')
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Compiled summary saved to {output_path}")
    print(f"\nSummary:")
    print(f"  Total documents: {summary['total_documents']}")
    print(f"  Success cases: {summary['success_cases']}")
    print(f"  Failure cases: {summary['failure_cases']['total']}")
    print(f"    - Non-identifiable: {summary['failure_cases']['non_identifiable']}")
    print(f"    - Dynamic characteristics: {summary['failure_cases']['dynamic_characteristics']}")
    print(f"    - Ambiguous: {summary['failure_cases']['ambiguous']}")

    return summary


if __name__ == '__main__':
    compile_data()
