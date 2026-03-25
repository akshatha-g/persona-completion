"""
Configuration for persona trait sets.

Each trait set represents a combination of PII types that can uniquely identify an individual.
Profile completion is calculated as the maximum match percentage across all trait sets.
"""

# Each trait set is a list of PII types required to uniquely identify someone
# Completion = (matched traits / total traits in set) * 100
# Final completion = max across all trait sets

PERSONA_TRAIT_SETS = [
    {
        "id": "identity_basic",
        "name": "Name + Age/DOB",
        "traits": ["name", "date_of_birth"],
    },
    {
        "id": "contact_email",
        "name": "Email",
        "traits": ["email"],
    },
    {
        "id": "contact_phone",
        "name": "Phone",
        "traits": ["phone"],
    },
    {
        "id": "social_media",
        "name": "Social Media Handles",
        "traits": ["social_media_handle"],
    },
    {
        "id": "customer_id",
        "name": "Customer ID",
        "traits": ["customer_id"],
    },
    {
        "id": "demographic_gender",
        "name": "Name + Gender",
        "traits": ["name", "gender"],
    },
    {
        "id": "demographic_location",
        "name": "Name + Location",
        "traits": ["name", "address"],
    },
]

# Mapping of alternate PII type names to canonical names (case-insensitive)
PII_TYPE_ALIASES = {
    # Name variations
    "first name": "name",
    "last name": "name",
    "full name": "name",
    "firstname": "name",
    "lastname": "name",
    
    # Date of birth / age variations
    "age": "date_of_birth",
    "dob": "date_of_birth",
    "birthday": "date_of_birth",
    "birth date": "date_of_birth",
    "birthdate": "date_of_birth",
    
    # Phone variations
    "phone number": "phone",
    "phone_number": "phone",
    "telephone": "phone",
    "work phone": "phone",
    "mobile": "phone",
    
    # Email variations
    "email address": "email_address",
    "email_address": "email",
    "work email": "email",
    
    # Social media variations
    "social media handles": "social_media_handle",
    "twitter": "social_media_handle",
    "twitter_handle": "social_media_handle",
    "facebook": "social_media_handle",
    "instagram": "social_media_handle",
    "linkedin": "social_media_handle",
    
    # Address variations
    "zipcode": "address",
    "zip_code": "address",
    "postal_code": "address",
    "location": "address",
    "birth city": "address",
}
