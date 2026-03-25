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
        "traits": ["name", "date_of_birth"],  # age maps to date_of_birth
    },
    {
        "id": "contact_email",
        "name": "Email",
        "traits": ["email"],  # email alone can identify
    },
    {
        "id": "contact_phone",
        "name": "Phone",
        "traits": ["phone"],  # phone alone can identify
    },
    {
        "id": "social_media",
        "name": "Social Media Handles",
        "traits": ["social_media_handle"],  # single trait = 100% if present
    },
    {
        "id": "customer_id",
        "name": "Customer ID",
        "traits": ["customer_id"],  # single trait = 100% if present
    },
    {
        "id": "demographic_gender",
        "name": "Name + Gender",
        "traits": ["name", "gender"],  # name + gender can identify
    },
    {
        "id": "demographic_location",
        "name": "Name + Location",
        "traits": ["name", "address"],  # name + address/zipcode can identify
    },
]

# Mapping of alternate PII type names to canonical names
PII_TYPE_ALIASES = {
    "age": "date_of_birth",
    "dob": "date_of_birth",
    "birthday": "date_of_birth",
    "phone_number": "phone",
    "telephone": "phone",
    "email_address": "email",
    "twitter": "social_media_handle",
    "twitter_handle": "social_media_handle",
    "facebook": "social_media_handle",
    "instagram": "social_media_handle",
    "linkedin": "social_media_handle",
    "zipcode": "address",
    "zip_code": "address",
    "postal_code": "address",
    "location": "address",
}
