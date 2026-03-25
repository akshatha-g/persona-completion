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
    
    def __init__(self, model: str = "gpt-4o-mini", mock: bool = False):
        self.model = model
        self.mock = mock or os.getenv("LLM_MOCK", "").lower() == "true"
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None and not self.mock:
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
        # Use mock analysis for testing
        if self.mock:
            return self._mock_analyze(doc1_piis, doc2_piis, doc1_id, doc2_id)
        
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
    
    def _mock_analyze(
        self,
        doc1_piis: Dict[str, str],
        doc2_piis: Dict[str, str],
        doc1_id: str,
        doc2_id: str
    ) -> MatchResult:
        """
        Mock LLM analysis using heuristics for testing.
        
        Uses weighted scoring similar to browser fingerprinting:
        - Common attributes (nationality, job title): low weight
        - Semi-rare (employer, age combo): medium weight
        - Rare combinations (family names + location): high weight
        """
        # Weight mapping for different PII types
        weights = {
            "nationality": 3,
            "job_title": 5,
            "job title": 5,
            "employer": 12,
            "age": 8,
            "birth_city": 15,
            "birth city": 15,
            "marital_status": 5,
            "marital status": 5,
            "first_name": 10,
            "first name": 10,
            "last_name": 15,
            "last name": 15,
            "father's_name": 25,
            "father's name": 25,
            "mother's_name": 25,
            "mother's name": 25,
            "spouse_name": 30,
            "spouse name": 30,
            "children_count": 8,
            "children count": 8,
        }
        
        matching_evidence = []
        score = 0.0
        contradictions = []
        
        # Normalize keys for comparison
        doc1_norm = {k.lower(): v.lower().strip() if v else "" for k, v in doc1_piis.items()}
        doc2_norm = {k.lower(): v.lower().strip() if v else "" for k, v in doc2_piis.items()}
        
        # Check each attribute
        for key, val1 in doc1_norm.items():
            if key in doc2_norm and val1 and doc2_norm[key]:
                val2 = doc2_norm[key]
                weight = weights.get(key, 5)
                
                if val1 == val2:
                    score += weight
                    matching_evidence.append(f"{key}: {val1}")
                elif key == "age":
                    # Age within ±2 is a weak match
                    try:
                        if abs(int(val1) - int(val2)) <= 2:
                            score += weight * 0.5
                            matching_evidence.append(f"age ~{val1}")
                        else:
                            contradictions.append(f"age mismatch: {val1} vs {val2}")
                    except ValueError:
                        pass
                elif key in ("nationality", "marital status", "marital_status"):
                    # These are contradictions if different
                    contradictions.append(f"{key} mismatch: {val1} vs {val2}")
        
        # Apply contradiction penalty
        if contradictions:
            score *= 0.3  # Heavy penalty for contradictions
        
        # Calculate confidence 
        # For mock: lower threshold since weak-ID-only docs have few attributes
        threshold = 15  # Minimum score for a match (e.g., nationality+job+employer = 20)
        max_score = 60  # Score for high confidence
        
        confidence = min(score / max_score, 0.95)
        is_match = score >= threshold and len(contradictions) == 0 and len(matching_evidence) >= 2
        
        reasoning = f"Mock analysis: score={score:.1f}, matches={len(matching_evidence)}"
        if contradictions:
            reasoning += f", contradictions={contradictions}"
        
        return MatchResult(
            is_same_person=is_match,
            confidence=confidence,
            reasoning=reasoning,
            matching_evidence=matching_evidence
        )


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
