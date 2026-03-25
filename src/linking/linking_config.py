"""
Configuration for cross-document profile linking.

Defines strong vs weak identifiers and their weights for the
browser-fingerprinting-style identification approach.
"""

# Strong identifiers: single match = identification
STRONG_IDENTIFIERS = {
    "Email Address": {"weight": 100, "unique": True},
    "Work Email": {"weight": 100, "unique": True},
    "Phone Number": {"weight": 100, "unique": True},
    "Work Phone": {"weight": 95, "unique": True},
    "Passport Number": {"weight": 100, "unique": True},
    "Driver's License": {"weight": 100, "unique": True},
    "National ID": {"weight": 100, "unique": True},
    "Social Media Handles": {"weight": 100, "unique": True},
}

# Weak identifiers: need multiple matches to narrow candidates
# Weight reflects how much this narrows the candidate pool
WEAK_IDENTIFIERS = {
    "First Name": {"weight": 5, "commonality": "high"},
    "Last Name": {"weight": 10, "commonality": "medium"},
    "Age": {"weight": 8, "commonality": "medium"},
    "Birth Date": {"weight": 25, "commonality": "low"},
    "Birth City": {"weight": 15, "commonality": "medium"},
    "Employer": {"weight": 12, "commonality": "medium"},
    "Job Title": {"weight": 10, "commonality": "medium"},
    "Nationality": {"weight": 3, "commonality": "high"},
    "Gender": {"weight": 2, "commonality": "very_high"},
    "Marital Status": {"weight": 3, "commonality": "high"},
    "Children Count": {"weight": 8, "commonality": "medium"},
    
    # Family names - fairly unique combinations
    "Mother's Name": {"weight": 25, "commonality": "low"},
    "Father's Name": {"weight": 25, "commonality": "low"},
    "Spouse Name": {"weight": 30, "commonality": "low"},
    
    # Other weak identifiers
    "Education Info": {"weight": 8, "commonality": "medium"},
    "Address": {"weight": 20, "commonality": "low"},
    "Credit Score": {"weight": 15, "commonality": "medium"},
    "Blood Type": {"weight": 5, "commonality": "high"},
    "Allergies": {"weight": 12, "commonality": "medium"},
    "Emergency Contact Name": {"weight": 20, "commonality": "low"},
}

# Thresholds for identification
IDENTIFICATION_THRESHOLD = 85  # Sum of weak weights needed to consider "identified"
LIKELY_THRESHOLD = 60  # Above this = likely match
CANDIDATE_THRESHOLD = 30  # Above this = candidate

# LLM configuration for contextual grouping
LLM_CONFIG = {
    "model": "gpt-4",  # or local model
    "temperature": 0.1,  # Low temperature for consistency
    "max_tokens": 500,
}

# Contextual signals for LLM to consider when grouping documents
CONTEXTUAL_SIGNALS = [
    "author_signature",
    "writing_style",
    "platform_handle",
    "email_thread",
    "timestamp_proximity",
    "document_source",
    "mentioned_relationships",
]
