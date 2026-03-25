# Persona Completion

A tool to analyze scraped documents with PII detection and determine how well an individual can be uniquely identified.

## Overview

This project works in 3 steps:

1. **PII Extraction** - Process documents with PII span data → generate a JSON database with document_id, profile_id, PIIs detected, and profile completion percentage
2. **Cross-Document Linking** - Link profiles across documents based on shared PII attributes
3. **Visualization** - Display profile completeness as progress bars

## Project Structure

```
persona-completion/
├── main.py                    # Entry point / CLI
├── src/
│   ├── extraction/            # Step 1: PII processing
│   ├── linking/               # Step 2: Profile linking
│   └── visualization/         # Step 3: Progress bar dashboard
├── data/
│   ├── input/                 # Input documents with PII spans
│   └── output/                # Generated profile database
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Output Schema

```json
[
  {
    "document_id": "doc_001",
    "profile_id": "profile_abc",
    "piis_detected": ["name", "email", "phone"],
    "profile_completion_pct": 75.0
  }
]
```
