"""
Sapphire Support AI Resolution Engine
Implements AI-first support resolution pipeline with RAG and decision logic
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid
import httpx

from app.services.ai_client import get_ai_client
from app.services.outline_client import get_outline_client
from app.models.case import Case
from app.models.ai import AIArtifact


class SupportResponse:
    """Structured response from AI resolution engine"""
    def __init__(
        self,
        answer: str,
        confidence: float,
        citations: List[Dict[str, Any]] = None,
        follow_up_needed: bool = False,
        clarifying_question: Optional[str] = None,
        resolution_successful: bool = False,
        suggest_escalation: bool = False,
        steps: Optional[List[str]] = None,
        probable_root_cause: Optional[str] = None,
        recommended_fix_attempts: Optional[List[str]] = None
    ):
        self.answer = answer
        self.confidence = confidence
        self.citations = citations or []
        self.follow_up_needed = follow_up_needed
        self.clarifying_question = clarifying_question
        self.resolution_successful = resolution_successful
        self.suggest_escalation = suggest_escalation
        self.steps = steps or []
        self.probable_root_cause = probable_root_cause
        self.recommended_fix_attempts = recommended_fix_attempts or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        result = {
            "answer": self.answer,
            "confidence": self.confidence,
            "citations": self.citations,
            "follow_up_needed": self.follow_up_needed,
            "resolution_successful": self.resolution_successful,
            "suggest_escalation": self.suggest_escalation
        }
        if self.clarifying_question:
            result["clarifying_question"] = self.clarifying_question
        if self.steps:
            result["steps"] = self.steps
        if self.probable_root_cause:
            result["probable_root_cause"] = self.probable_root_cause
        if self.recommended_fix_attempts:
            result["recommended_fix_attempts"] = self.recommended_fix_attempts
        return result


class SupportAIEngine:
    """AI Resolution Engine for support requests"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_client = get_ai_client()
        self.outline_client = get_outline_client()
    
    async def classify_intent(self, message: str, subject: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify the intent and urgency of a support message
        
        Returns:
            {
                "intent": Intent enum,
                "urgency": Urgency enum,
                "confidence": float,
                "compliance_flag": bool,
                "recommended_action": RecommendedAction enum,
                "model_used": str
            }
        """
        return await self.ai_client.classify_intent(
            subject=subject,
            body_text=message,
            from_email=""  # Not needed for classification
        )
    
    async def retrieve_context(
        self,
        tenant_id: uuid.UUID,
        query: str,
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for RAG
        
        Combines:
        - Tenant KB articles (from Outline)
        - Global system documentation
        - Prior solved cases (from database)
        - Workflow guides
        - Known failure patterns
        
        Returns list of context documents
        """
        context_docs = []
        
        # 1. Knowledge Base search (Outline)
        try:
            kb_results = await self.outline_client.search(query, limit=limit)
            for result in kb_results:
                context_docs.append({
                    "type": "kb_article",
                    "title": result.get("title", ""),
                    "content": result.get("text", ""),
                    "url": result.get("url", ""),
                    "source": "knowledge_base"
                })
        except Exception as e:
            # Continue if KB search fails
            pass
        
        # 2. Prior solved cases (last 90 days)
        try:
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            similar_cases = self.db.query(Case).filter(
                and_(
                    Case.tenant_id == tenant_id,
                    Case.status.in_(["resolved", "closed"]),
                    Case.created_at >= ninety_days_ago,
                    Case.ai_confidence.isnot(None),
                    Case.ai_confidence >= 0.7  # Only high-confidence resolutions
                )
            ).order_by(Case.ai_confidence.desc()).limit(3).all()
            
            for case in similar_cases:
                # Get AI summary from artifacts
                summary_artifact = self.db.query(AIArtifact).filter(
                    and_(
                        AIArtifact.case_id == case.id,
                        AIArtifact.artifact_type == "summary"
                    )
                ).first()
                
                if summary_artifact:
                    context_docs.append({
                        "type": "prior_case",
                        "title": case.title,
                        "content": summary_artifact.content,
                        "case_id": str(case.id),
                        "confidence": case.ai_confidence,
                        "source": "case_history"
                    })
        except Exception as e:
            # Continue if case retrieval fails
            pass
        
        # 3. Global system documentation (could be from a separate doc store)
        # For now, we'll rely on KB and case history
        
        return context_docs
    
    async def generate_resolution(
        self,
        context: List[Dict[str, Any]],
        message: str,
        subject: Optional[str] = None,
        tier: int = 0
    ) -> SupportResponse:
        """
        Generate resolution using RAG context
        
        Uses different prompts based on tier:
        - Tier 0: Self-service resolution
        - Tier 1+: Escalation analysis
        """
        if tier == 0:
            return await self._generate_tier0_resolution(context, message, subject)
        else:
            return await self._generate_tier1_escalation_analysis(context, message, subject)
    
    async def _generate_tier0_resolution(
        self,
        context: List[Dict[str, Any]],
        message: str,
        subject: Optional[str] = None
    ) -> SupportResponse:
        """Generate Tier 0 self-service resolution"""
        # Build context text
        context_text = ""
        citations = []
        
        for doc in context[:6]:  # Top 6 documents
            context_text += f"\n--- {doc.get('title', 'Document')} ---\n"
            context_text += doc.get('content', '')[:500] + "\n"
            
            if doc.get('url'):
                citations.append({
                    "title": doc.get('title', 'Document'),
                    "url": doc.get('url', ''),
                    "snippet": doc.get('content', '')[:200]
                })
            elif doc.get('case_id'):
                citations.append({
                    "title": f"Similar Case: {doc.get('title', '')}",
                    "url": f"/cases/{doc.get('case_id')}",
                    "snippet": doc.get('content', '')[:200]
                })
        
        # Build prompt
        prompt = f"""ROLE: Sapphire Support AI
GOAL: Solve the issue without human intervention.

You have access to:
- Knowledge Base articles
- Workflow guides
- Prior case solutions
- Tenant-specific context

User Request:
Subject: {subject or 'N/A'}
Message: {message}

Context from Knowledge Base and Case History:
{context_text}

Instructions:
1. Provide a clear, actionable answer with specific steps
2. If you're confident (>= 0.78), provide the solution
3. If moderately confident (0.45-0.78), ask ONE clarifying question
4. If low confidence (< 0.45), suggest escalation
5. Always cite sources when using KB articles or prior cases

Return structured JSON:
{{
  "answer": "Clear explanation and solution steps",
  "steps": ["Step 1", "Step 2", ...],
  "confidence": 0.0-1.0,
  "citations": ["doc references"],
  "needs_clarification": true/false,
  "clarifying_question": "optional single question",
  "resolution_successful": true/false
}}"""
        
        # Call AI gateway
        try:
            headers = {}
            if self.ai_client.api_key:
                headers["Authorization"] = f"Bearer {self.ai_client.api_key}"
            
            payload = {
                "prompt": prompt,
                "operation": "support_resolution",
                "max_tokens": 1000,
                "temperature": 0.3  # Lower temperature for more consistent responses
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ai_client.base_url}/generate",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
            
            # Parse AI response
            ai_answer = result.get("response", result.get("answer", ""))
            # Try to extract JSON from response if it's wrapped
            if "{" in ai_answer and "}" in ai_answer:
                import json
                try:
                    # Extract JSON block
                    start = ai_answer.find("{")
                    end = ai_answer.rfind("}") + 1
                    json_str = ai_answer[start:end]
                    parsed = json.loads(json_str)
                    ai_answer = parsed.get("answer", ai_answer)
                    confidence = float(parsed.get("confidence", 0.5))
                    steps = parsed.get("steps", [])
                    needs_clarification = parsed.get("needs_clarification", False)
                    clarifying_question = parsed.get("clarifying_question")
                    resolution_successful = parsed.get("resolution_successful", confidence >= 0.78)
                except:
                    # Fallback to parsing from text
                    confidence = 0.5
                    steps = []
                    needs_clarification = False
                    clarifying_question = None
                    resolution_successful = False
            else:
                # Simple text response, estimate confidence
                confidence = 0.6 if len(ai_answer) > 100 else 0.4
                steps = []
                needs_clarification = confidence < 0.7
                clarifying_question = None
                resolution_successful = confidence >= 0.78
            
            return SupportResponse(
                answer=ai_answer,
                confidence=confidence,
                citations=citations,
                follow_up_needed=needs_clarification,
                clarifying_question=clarifying_question,
                resolution_successful=resolution_successful,
                suggest_escalation=confidence < 0.45,
                steps=steps
            )
            
        except Exception as e:
            # Fallback response
            return SupportResponse(
                answer="I'm having trouble processing your request right now. Please try again or contact support.",
                confidence=0.0,
                citations=[],
                follow_up_needed=False,
                resolution_successful=False,
                suggest_escalation=True
            )
    
    async def _generate_tier1_escalation_analysis(
        self,
        context: List[Dict[str, Any]],
        message: str,
        subject: Optional[str] = None
    ) -> SupportResponse:
        """Generate Tier 1 escalation analysis for agent review"""
        context_text = "\n".join([
            f"- {doc.get('title', 'Document')}: {doc.get('content', '')[:300]}"
            for doc in context[:5]
        ])
        
        prompt = f"""ROLE: Senior Support Agent AI
GOAL: Determine if the case requires human intervention.

User Issue:
Subject: {subject or 'N/A'}
Message: {message}

Available Context:
{context_text}

Analyze and provide:
1. Summary for human agent
2. Probable root cause
3. Recommended fix attempts before escalation
4. Whether escalation is required

Return JSON:
{{
  "summary_for_agent": "...",
  "probable_root_cause": "...",
  "recommended_fix_attempts": ["...", "..."],
  "escalation_required": true/false,
  "confidence": 0.0-1.0
}}"""
        
        try:
            headers = {}
            if self.ai_client.api_key:
                headers["Authorization"] = f"Bearer {self.ai_client.api_key}"
            
            payload = {
                "prompt": prompt,
                "operation": "escalation_analysis",
                "max_tokens": 800
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ai_client.base_url}/generate",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
            
            ai_response = result.get("response", "")
            # Parse JSON from response
            import json
            try:
                start = ai_response.find("{")
                end = ai_response.rfind("}") + 1
                parsed = json.loads(ai_response[start:end])
                summary = parsed.get("summary_for_agent", ai_response)
                root_cause = parsed.get("probable_root_cause", "")
                fix_attempts = parsed.get("recommended_fix_attempts", [])
                escalation_required = parsed.get("escalation_required", True)
                confidence = float(parsed.get("confidence", 0.5))
            except:
                summary = ai_response
                root_cause = ""
                fix_attempts = []
                escalation_required = True
                confidence = 0.5
            
            return SupportResponse(
                answer=summary,
                confidence=confidence,
                citations=[],
                follow_up_needed=False,
                resolution_successful=not escalation_required,
                suggest_escalation=escalation_required,
                probable_root_cause=root_cause,
                recommended_fix_attempts=fix_attempts
            )
        except Exception as e:
            return SupportResponse(
                answer="Case requires human review.",
                confidence=0.0,
                citations=[],
                resolution_successful=False,
                suggest_escalation=True
            )
    
    def score_confidence(self, response: SupportResponse) -> float:
        """
        Score confidence of a response
        Can be enhanced with additional heuristics
        """
        base_confidence = response.confidence
        
        # Boost confidence if we have citations
        if response.citations:
            base_confidence += 0.05 * min(len(response.citations), 3)
        
        # Boost if we have steps
        if response.steps:
            base_confidence += 0.05 * min(len(response.steps), 3)
        
        # Cap at 1.0
        return min(base_confidence, 1.0)
    
    def should_escalate(
        self,
        confidence: float,
        attempts: int = 1,
        user_rejected: bool = False
    ) -> bool:
        """
        Determine if case should be escalated
        
        Decision thresholds:
        - confidence < 0.45 → escalate
        - attempts > 2 → escalate
        - user_rejected → escalate
        """
        if user_rejected:
            return True
        if confidence < 0.45:
            return True
        if attempts > 2:
            return True
        return False
    
    def format_resolution(self, response: SupportResponse) -> str:
        """Format resolution for display to user"""
        formatted = response.answer
        
        if response.steps:
            formatted += "\n\nSteps to resolve:\n"
            for i, step in enumerate(response.steps, 1):
                formatted += f"{i}. {step}\n"
        
        if response.citations:
            formatted += "\n\nSources:\n"
            for citation in response.citations:
                formatted += f"- {citation.get('title', 'Source')}\n"
        
        if response.clarifying_question:
            formatted += f"\n\nTo help me better assist you: {response.clarifying_question}"
        
        return formatted
    
    def summarize_for_case(self, response: SupportResponse) -> str:
        """Create summary for case record"""
        summary = f"AI Resolution Attempt:\n"
        summary += f"Confidence: {response.confidence:.2f}\n"
        summary += f"Resolution Successful: {response.resolution_successful}\n\n"
        summary += f"Answer: {response.answer}\n"
        
        if response.probable_root_cause:
            summary += f"\nProbable Root Cause: {response.probable_root_cause}\n"
        
        if response.recommended_fix_attempts:
            summary += f"\nRecommended Fixes:\n"
            for fix in response.recommended_fix_attempts:
                summary += f"- {fix}\n"
        
        return summary

