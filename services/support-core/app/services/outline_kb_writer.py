"""
Outline KB Writer - Automatic KB article generation
Generates KB articles when AI successfully resolves support requests
"""
import httpx
from typing import List, Dict, Optional, Any
from app.core.config import settings
from app.services.outline_client import get_outline_client
from app.services.ai_client import get_ai_client


class OutlineKBWriter:
    """Writer for creating KB articles in Outline"""
    
    def __init__(self):
        self.base_url = settings.OUTLINE_API_URL.rstrip("/")
        self.api_key = settings.OUTLINE_API_KEY
        self.collection_id = settings.OUTLINE_COLLECTION
        self.outline_client = get_outline_client()
        self.ai_client = get_ai_client()
    
    async def search_existing_articles(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for existing articles in Outline
        
        Returns list of matching documents with similarity scores
        """
        try:
            results = await self.outline_client.search(query, limit=limit)
            return results
        except Exception as e:
            return []
    
    def should_create_article(
        self,
        existing_articles: List[Dict[str, Any]],
        confidence: float,
        similarity_threshold: float = 0.7
    ) -> bool:
        """
        Determine if a new article should be created
        
        Args:
            existing_articles: List of existing articles from search
            confidence: AI resolution confidence score
            similarity_threshold: Minimum similarity to consider a match (0.0-1.0)
        
        Returns:
            True if article should be created, False otherwise
        """
        # If confidence is low, don't create article
        if confidence < 0.75:
            return False
        
        # If no existing articles found, create one
        if not existing_articles or len(existing_articles) == 0:
            return True
        
        # Simple text similarity check (can be enhanced with embeddings)
        # For now, if we found articles, assume they might be similar
        # In production, use embedding similarity
        # If top result has high relevance, don't create duplicate
        if len(existing_articles) > 0:
            # Check if any article title is very similar
            # This is a simple heuristic - in production use semantic similarity
            return True  # Always create if confidence is high enough
        
        return False
    
    async def generate_article_content(
        self,
        issue_title: str,
        problem_description: str,
        resolution_steps: List[str],
        notes: Optional[str] = None,
        related_articles: Optional[List[str]] = None
    ) -> str:
        """
        Generate KB article content using LLM with template
        
        Returns markdown formatted article
        """
        # Build content from provided information
        content = f"# {issue_title}\n\n"
        
        content += "## Problem\n"
        content += f"{problem_description}\n\n"
        
        if resolution_steps:
            content += "## Resolution\n"
            for i, step in enumerate(resolution_steps, 1):
                content += f"{i}. {step}\n"
            content += "\n"
        
        if notes:
            content += "## Notes\n"
            content += f"{notes}\n\n"
        
        if related_articles:
            content += "## Related\n"
            for article in related_articles:
                content += f"- {article}\n"
            content += "\n"
        
        # Use AI to enhance and format the article
        try:
            prompt = f"""Format the following KB article content into a clear, professional knowledge base article.
Make it concise, actionable, and easy to follow.

Current content:
{content}

Return the improved markdown content, keeping the same structure but enhancing clarity and completeness."""
            
            headers = {}
            if self.ai_client.api_key:
                headers["Authorization"] = f"Bearer {self.ai_client.api_key}"
            
            payload = {
                "prompt": prompt,
                "operation": "format_kb_article",
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ai_client.base_url}/generate",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract formatted content
                formatted = result.get("response", result.get("answer", content))
                # If AI wrapped it, extract the markdown
                if "```markdown" in formatted:
                    start = formatted.find("```markdown") + 11
                    end = formatted.find("```", start)
                    formatted = formatted[start:end].strip()
                elif "```" in formatted:
                    start = formatted.find("```") + 3
                    end = formatted.find("```", start)
                    formatted = formatted[start:end].strip()
                
                return formatted if formatted else content
        except Exception as e:
            # Fallback to template content if AI formatting fails
            return content
    
    async def create_kb_article(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        publish: bool = False
    ) -> Dict[str, Any]:
        """
        Create a KB article in Outline
        
        Args:
            title: Article title
            content: Markdown content
            tags: Optional tags (Outline uses collections, not tags directly)
            publish: Whether to publish immediately (default: False, creates draft)
        
        Returns:
            {
                "kb_created": bool,
                "document_id": str or None,
                "url": str or None,
                "error": str or None
            }
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "title": title,
            "text": content,
            "publish": publish
        }
        
        # Add collection if configured
        if self.collection_id:
            payload["collectionId"] = self.collection_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/documents.create",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                doc = data.get("data", {})
                document_id = doc.get("id")
                url_id = doc.get("urlId", "")
                url = f"{self.base_url}/doc/{url_id}" if url_id else None
                
                return {
                    "kb_created": True,
                    "document_id": document_id,
                    "url": url,
                    "error": None
                }
        except Exception as e:
            return {
                "kb_created": False,
                "document_id": None,
                "url": None,
                "error": str(e)
            }
    
    async def create_article_from_resolution(
        self,
        issue_title: str,
        problem_description: str,
        resolution_answer: str,
        resolution_steps: List[str],
        confidence: float,
        tenant_name: Optional[str] = None,
        is_tenant_specific: bool = False
    ) -> Dict[str, Any]:
        """
        Complete workflow: Check for existing articles, generate content, create article
        
        Args:
            issue_title: Title of the issue
            problem_description: Description of the problem
            resolution_answer: AI-generated resolution answer
            resolution_steps: List of resolution steps
            confidence: AI confidence score
            tenant_name: Optional tenant name for tagging
            is_tenant_specific: Whether this is tenant-specific (private) or general (public)
        
        Returns:
            {
                "kb_created": bool,
                "document_id": str or None,
                "url": str or None,
                "similar_articles_found": int,
                "error": str or None
            }
        """
        # Step 1: Search for existing articles
        search_query = f"{issue_title} {problem_description[:100]}"
        existing_articles = await self.search_existing_articles(search_query, limit=5)
        
        # Step 2: Check if we should create article
        if not self.should_create_article(existing_articles, confidence):
            return {
                "kb_created": False,
                "document_id": None,
                "url": None,
                "similar_articles_found": len(existing_articles),
                "error": "Similar article exists or confidence too low"
            }
        
        # Step 3: Generate article content
        related_articles = []
        if existing_articles:
            related_articles = [
                f"[{article.get('title', 'Article')}]({article.get('url', '')})"
                for article in existing_articles[:3]
            ]
        
        # Extract notes from resolution if available
        notes = None
        if "Note:" in resolution_answer or "Important:" in resolution_answer:
            # Try to extract notes section
            parts = resolution_answer.split("Note:")
            if len(parts) > 1:
                notes = parts[1].strip()
        
        content = await self.generate_article_content(
            issue_title=issue_title,
            problem_description=problem_description,
            resolution_steps=resolution_steps,
            notes=notes,
            related_articles=related_articles
        )
        
        # Step 4: Create article in Outline
        tags = []
        if tenant_name and is_tenant_specific:
            tags.append(f"tenant-{tenant_name}")
        tags.append("ai-generated")
        tags.append("support-resolution")
        
        result = await self.create_kb_article(
            title=issue_title,
            content=content,
            tags=tags,
            publish=False  # Always create as draft for review
        )
        
        result["similar_articles_found"] = len(existing_articles)
        return result


# Singleton instance
_outline_kb_writer: Optional[OutlineKBWriter] = None


def get_outline_kb_writer() -> OutlineKBWriter:
    """Get singleton Outline KB writer instance"""
    global _outline_kb_writer
    if _outline_kb_writer is None:
        _outline_kb_writer = OutlineKBWriter()
    return _outline_kb_writer

