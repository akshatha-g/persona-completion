# Persona Completion

Cross-document profile linking to determine how uniquely identifiable individuals are from scraped web data.

## Methodology

### 1. PII Extraction
- Process documents with PII span annotations
- Each document treated independently (no pre-grouping)
- Calculate profile completion % using trait sets (e.g., email alone = 100%, name+DOB = 100%)

### 2. Two-Phase Cross-Document Linking

**Phase 1: Deterministic (Strong IDs)**
- Link documents sharing email, phone, SSN, passport, or social media handles
- Union-Find algorithm to merge connected profiles
- Enriches profiles with combined PII from linked documents

**Phase 2: LLM Contextual (Weak IDs)**
- For documents without strong identifiers
- Uses "browser fingerprinting" approach: combinations of innocuous data (nationality + employer + age) can uniquely identify
- Finds candidate pairs with 2+ overlapping weak IDs
- LLM confirms matches with confidence scoring
- Detects contradictions (different nationality = no match)

### 3. Visualization
- Profile completeness dashboard 

## Results (Synthetic Data)

```
Total Documents:                    1,807
Total Profiles (after linking):     1,711
--------------------------------------------------
Phase 1 - Strong ID Linking:
  Linked profiles:                  22
  Documents merged:                 110
--------------------------------------------------
Phase 2 - LLM Contextual Linking:
  Linked profiles:                  6
  Documents merged:                 14
--------------------------------------------------
Unlinked Profiles (singletons):     1,683
```

**Input files:**
- `non_identifiable_doc.json` (325 docs) - Only weak IDs (job title, nationality)
- `dynamic_characteristics.json` (728 docs) - Mixed weak IDs
- `panorama_sample.json` (756 docs) - Strong + weak IDs

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# With mock LLM (no API key needed)
LLM_MOCK=true python main.py

# With real LLM
export OPENAI_API_KEY="your-key"
python main.py

# Analyze more candidate pairs
MAX_LLM_PAIRS=500 LLM_MOCK=true python main.py
```

## Output

```json
{
  "document_id": "doc_0138",
  "profile_id": "doc_0138",
  "ground_truth_id": "abc-123",
  "piis_detected": ["First Name", "Employer", "Mother's Name"],
  "pii_values": {"First Name": "Lana", "Employer": "LLC Store"},
  "profile_completion_pct": 0.0,
  "linked_document_ids": ["doc_0138", "doc_0111", "doc_0135"]
}
```

## Next Steps

1. **Real data evaluation** - Current results are on synthetic PANORAMA dataset; need crawled web data for realistic evaluation
2. **Richer PII extraction** - Integrate actual NER/PII detection instead of pre-annotated spans
3. **LLM prompt tuning** - Optimize prompts for better precision/recall on real data
4. **Visualization dashboard** - Implement actual completeness visualization
5. **Ground truth evaluation** - Compare linked profiles against `ground_truth_id` to measure accuracy
6. **Scalability** - Batch LLM calls, caching, and parallel processing for large datasets
