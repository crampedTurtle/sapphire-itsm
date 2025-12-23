"""
AI Client abstraction for intent classification and response generation
"""
import httpx
from typing import Dict, List, Optional, Any
from app.core.config import settings
from app.models.intake import Intent, Urgency, RecommendedAction


class AIClient:
    """Abstraction for AI gateway operations"""
    
    def __init__(self):
        self.base_url = settings.AI_GATEWAY_URL
        self.api_key = settings.AI_GATEWAY_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def classify_intent(
        self,
        subject: Optional[str],
        body_text: str,
        from_email: str
    ) -> Dict[str, Any]:
        """
        Classify intent of an intake event
        
        Returns:
            {
                "intent": "support" | "sales" | "onboarding" | "billing" | "compliance" | "outage" | "unknown",
                "urgency": "low" | "normal" | "high" | "critical",
                "confidence": float (0.0-1.0),
                "compliance_flag": bool,
                "recommended_action": "self_service" | "create_case" | "route_sales" | "escalate_ops" | "needs_review"
            }
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "subject": subject,
            "body_text": body_text,
            "from_email": from_email,
            "operation": "classify_intent"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/classify",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Normalize response
            return {
                "intent": Intent(result.get("intent", "unknown")),
                "urgency": Urgency(result.get("urgency", "normal")),
                "confidence": float(result.get("confidence", 0.5)),
                "compliance_flag": bool(result.get("compliance_flag", False)),
                "recommended_action": RecommendedAction(result.get("recommended_action", "needs_review")),
                "model_used": result.get("model_used", "unknown")
            }
        except Exception as e:
            # Fallback to safe defaults on error
            return {
                "intent": Intent.UNKNOWN,
                "urgency": Urgency.NORMAL,
                "confidence": 0.0,
                "compliance_flag": True,  # Safe default: flag for review
                "recommended_action": RecommendedAction.NEEDS_REVIEW,
                "model_used": "fallback"
            }
    
    async def generate_response(
        self,
        case_id: str,
        case_title: str,
        case_messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate summary and draft response for a case
        
        Returns:
            {
                "summary": str,
                "suggested_next_steps": List[str],
                "draft_response": str,
                "confidence": float,
                "model_used": str
            }
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "case_id": case_id,
            "case_title": case_title,
            "case_messages": case_messages,
            "context": context or {},
            "operation": "generate_response",
            "safety_rules": [
                "Never claim actions taken unless confirmed",
                "Acknowledge uncertainty and ask clarifying questions if needed",
                "Never provide legal advice",
                "Provide operational guidance and platform support only"
            ]
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/generate",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "summary": result.get("summary", ""),
                "suggested_next_steps": result.get("suggested_next_steps", []),
                "draft_response": result.get("draft_response", ""),
                "confidence": float(result.get("confidence", 0.5)),
                "model_used": result.get("model_used", "unknown")
            }
        except Exception as e:
            return {
                "summary": "Unable to generate AI summary at this time.",
                "suggested_next_steps": ["Review case manually"],
                "draft_response": "",
                "confidence": 0.0,
                "model_used": "fallback"
            }
    
    async def kb_answer_with_citations(
        self,
        question: str,
        kb_context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate KB answer with citations using RAG
        
        Returns:
            {
                "answer": str,
                "citations": List[{"title": str, "url": str, "snippet": str}],
                "confidence": float,
                "model_used": str
            }
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "question": question,
            "kb_context": kb_context or [],
            "operation": "kb_answer_with_citations"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/kb-answer",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "answer": result.get("answer", "I couldn't find a specific answer to your question."),
                "citations": result.get("citations", []),
                "confidence": float(result.get("confidence", 0.5)),
                "model_used": result.get("model_used", "unknown")
            }
        except Exception as e:
            return {
                "answer": "I'm unable to answer your question right now. Please try again or open a support case.",
                "citations": [],
                "confidence": 0.0,
                "model_used": "fallback"
            }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance
_ai_client: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    """Get singleton AI client instance"""
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client

