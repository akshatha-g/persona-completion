"""
LLM client for contextual profile linking.
"""

import os
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MatchResult:
    """Result of LLM matching analysis."""
    is_same_person: bool
    confidence: float  # 0.0 - 1.0
    reasoning: str
    matching_evidence: List[str]


class LLMClient:
    """Client for LLM-based contextual matching."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI()  # Uses OPENAI_API_KEY env var
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client
    
    def analyze_match(
        self, 
        doc1_piis: Dict[str, str],
        doc2_piis: Dict[str, str],
        doc1_id: str,
        doc2_id: str
    ) -> MatchResult:
        """
        Analyze whether two documents likely belong to the same person.
        
        Uses weak identifiers and contextual clues to determine match likelihood.
        """
        prompt = self._build_match_prompt(doc1_piis, doc2_piis, doc1_id, doc2_id)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return MatchResult(
                is_same_person=result.get("is_same_person", False),
                confidence=result.get("confidence", 0.0),
                reasoning=result.get("reasoning", ""),
                matching_evidence=result.get("matching_evidence", [])
            )
            
        except Exception as e:
            # Return low confidence on error
            return MatchResult(
                is_same_person=False,
                confidence=0.0,
                reasoning=f"Error during analysis: {str(e)}",
                matching_evidence=[]
            )
    
    def batch_analyze_candidates(
        self,
        target_doc: Dict[str, str],
        target_id: str,
        candidates: List[Tuple[str, Dict[str, str]]]  # [(doc_id, pii_values), ...]
    ) -> List[Tuple[str, MatchResult]]:
        """
        Analyze multiple candidate matches for a target document.
        
        Returns list of (candidate_doc_id, MatchResult) sorted by confidence.
        """
        results = []
        
        for candidate_id, candidate_piis in candidates:
            result = self.analyze_match(
                target_doc, candidate_piis,
                target_id, candidate_id
            )
            results.append((candidate_id, result))
        
        # Sort by confidence descending
        results.sort(key=lambda x: x[1].confidence, reverse=True)
        return results
    
    def _build_match_prompt(
        self,
        doc1_piis: Dict[str, str],
        doc2_piis: Dict[str, str],
        doc1_id: str,
        doc2_id: str
    ) -> str:
        """Build the prompt for match analysis."""
        return f"""Analyze whether these two documents likely belong to the same person.

Document 1 ({doc1_id}):
{json.dumps(doc1_piis, indent=2)}

Document 2 ({doc2_id}):
{json.dumps(doc2_piis, indent=2)}

Consider:
1. Matching weak identifiers (nationality, employer, job title, age, etc.)
2. Combinations that would be rare in a population
3. Contradicting information that would rule out a match
4. The browser-fingerprinting principle: many innocuous data points together can uniquely identify someone

Respond with JSON:
{{
    "is_same_person": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "explanation of your analysis",
    "matching_evidence": ["list", "of", "matching", "points"]
}}"""


SYSTEM_PROMPT = """You are an expert at identity resolution and profile linking.

Your task is to determine if two documents belong to the same person based on weak identifiers 
(attributes that alone don't uniquely identify someone, but in combination can).

Key principles:
1. Single weak identifiers (nationality, job title) are NOT enough to confirm a match
2. Combinations become powerful: "Australian + Human Resources Manager + Age 49" is much more specific
3. Family names (mother's name, father's name, spouse) are semi-strong identifiers
4. Contradicting information (different nationalities, incompatible ages) should lower confidence
5. Consider rarity: "Cook from Canada" is common, "Paralegal + Age 75 + Australian" is rare

Confidence scale:
- 0.9-1.0: Near certain match (multiple rare identifiers align)
- 0.7-0.9: Likely same person (several identifiers match, no contradictions)
- 0.4-0.7: Possible match (some identifiers match, needs more data)
- 0.0-0.4: Unlikely or not enough data

Always respond with valid JSON."""
