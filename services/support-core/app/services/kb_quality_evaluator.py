"""
KB Quality Evaluator - Scores article quality and determines review needs
"""
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import json

from app.models.kb_article import KBQualityScore, KBArticleIndex, KBArticleRevision
from app.services.ai_client import get_ai_client


class KBQualityResult:
    """Result of quality evaluation"""
    def __init__(
        self,
        clarity_score: int,
        completeness_score: int,
        technical_accuracy_score: int,
        structure_score: int,
        overall_score: int,
        needs_review: bool,
        reason: Optional[str] = None
    ):
        self.clarity_score = clarity_score
        self.completeness_score = completeness_score
        self.technical_accuracy_score = technical_accuracy_score
        self.structure_score = structure_score
        self.overall_score = overall_score
        self.needs_review = needs_review
        self.reason = reason


class KBQualityEvaluator:
    """Evaluates KB article quality using LLM"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_client = get_ai_client()
    
    async def evaluate_article(
        self,
        markdown_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> KBQualityResult:
        """
        Evaluate article quality using LLM
        
        Returns scores 1-10 for each dimension and overall
        Flags needs_review if overall < 7 or any dimension < 6
        """
        prompt = f"""Evaluate this knowledge base article for quality. Rate each dimension 1-10 and provide an overall score.

Article Content:
{markdown_content[:3000]}

Context: {json.dumps(context) if context else "None"}

Evaluate:
1. Clarity: Is the article clear and easy to understand?
2. Completeness: Does it cover the topic thoroughly?
3. Technical Accuracy: Are the technical details correct?
4. Structure: Is it well-organized with proper sections?

Return ONLY valid JSON in this exact format:
{{
  "clarity_score": <1-10>,
  "completeness_score": <1-10>,
  "technical_accuracy_score": <1-10>,
  "structure_score": <1-10>,
  "overall_score": <1-10>,
  "needs_review": <true/false>,
  "reason": "<explanation if needs_review is true>"
}}

Flag needs_review = true if:
- overall_score < 7, OR
- any dimension < 6, OR
- content appears speculative or uncertain"""
        
        try:
            headers = {}
            if self.ai_client.api_key:
                headers["Authorization"] = f"Bearer {self.ai_client.api_key}"
            
            payload = {
                "prompt": prompt,
                "operation": "evaluate_kb_quality",
                "max_tokens": 500,
                "temperature": 0.2  # Low temperature for consistent scoring
            }
            
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ai_client.base_url}/generate",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                ai_response = result.get("response", result.get("answer", ""))
                
                # Parse JSON from response
                try:
                    # Extract JSON block
                    if "{" in ai_response:
                        start = ai_response.find("{")
                        end = ai_response.rfind("}") + 1
                        json_str = ai_response[start:end]
                        parsed = json.loads(json_str)
                    else:
                        # Fallback to default scores
                        parsed = {
                            "clarity_score": 5,
                            "completeness_score": 5,
                            "technical_accuracy_score": 5,
                            "structure_score": 5,
                            "overall_score": 5,
                            "needs_review": True,
                            "reason": "Could not parse evaluation"
                        }
                    
                    clarity = int(parsed.get("clarity_score", 5))
                    completeness = int(parsed.get("completeness_score", 5))
                    technical = int(parsed.get("technical_accuracy_score", 5))
                    structure = int(parsed.get("structure_score", 5))
                    overall = int(parsed.get("overall_score", 5))
                    needs_review = bool(parsed.get("needs_review", True))
                    reason = parsed.get("reason")
                    
                    # Validate scores are in range
                    clarity = max(1, min(10, clarity))
                    completeness = max(1, min(10, completeness))
                    technical = max(1, min(10, technical))
                    structure = max(1, min(10, structure))
                    overall = max(1, min(10, overall))
                    
                    # Override needs_review based on scores
                    if overall < 7 or min(clarity, completeness, technical, structure) < 6:
                        needs_review = True
                        if not reason:
                            reason = f"Overall score {overall} or dimension score < 6"
                    
                    return KBQualityResult(
                        clarity_score=clarity,
                        completeness_score=completeness,
                        technical_accuracy_score=technical,
                        structure_score=structure,
                        overall_score=overall,
                        needs_review=needs_review,
                        reason=reason
                    )
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    # Fallback to safe defaults
                    return KBQualityResult(
                        clarity_score=5,
                        completeness_score=5,
                        technical_accuracy_score=5,
                        structure_score=5,
                        overall_score=5,
                        needs_review=True,
                        reason=f"Evaluation parsing error: {str(e)}"
                    )
        except Exception as e:
            # Fallback to safe defaults on error
            return KBQualityResult(
                clarity_score=5,
                completeness_score=5,
                technical_accuracy_score=5,
                structure_score=5,
                overall_score=5,
                needs_review=True,
                reason=f"Evaluation error: {str(e)}"
            )
    
    def store_quality_score(
        self,
        outline_document_id: str,
        article_id: Optional[uuid.UUID],
        revision_id: Optional[uuid.UUID],
        quality_result: KBQualityResult
    ) -> KBQualityScore:
        """Store quality score in database"""
        score = KBQualityScore(
            outline_document_id=outline_document_id,
            article_id=article_id,
            version_revision_id=revision_id,
            clarity_score=quality_result.clarity_score,
            completeness_score=quality_result.completeness_score,
            technical_accuracy_score=quality_result.technical_accuracy_score,
            structure_score=quality_result.structure_score,
            overall_score=quality_result.overall_score,
            needs_review=quality_result.needs_review,
            reason=quality_result.reason
        )
        self.db.add(score)
        self.db.commit()
        self.db.refresh(score)
        return score

