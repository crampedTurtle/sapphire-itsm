"""
KB Update Agent - Decides whether to create or update KB articles
Avoids duplicates and maintains article history
"""
from typing import List, Dict, Optional, Any, Literal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime
import uuid
import json

from app.models.kb_article import KBArticleIndex, KBArticleRevision, KBDecisionLog
from app.services.outline_kb_writer import get_outline_kb_writer
from app.services.ai_client import get_ai_client


class KBUpdateResult:
    """Result of KB article update operation"""
    def __init__(
        self,
        success: bool,
        outline_document_id: Optional[str] = None,
        action: str = "none",  # "created", "updated", "skipped"
        revision_number: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.outline_document_id = outline_document_id
        self.action = action
        self.revision_number = revision_number
        self.error = error


class KBCreateResult:
    """Result of KB article creation operation"""
    def __init__(
        self,
        success: bool,
        outline_document_id: Optional[str] = None,
        article_id: Optional[uuid.UUID] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.outline_document_id = outline_document_id
        self.article_id = article_id
        self.error = error


class KBUpdateAgent:
    """Agent for managing KB article creation and updates"""
    
    def __init__(self, db: Session):
        self.db = db
        self.kb_writer = get_outline_kb_writer()
        self.ai_client = get_ai_client()
    
    async def find_similar_articles(
        self,
        tenant_id: Optional[uuid.UUID],
        issue_title: str,
        problem_description: str
    ) -> List[Dict[str, Any]]:
        """
        Find similar articles using title similarity and search
        
        Returns list of candidates with similarity scores
        """
        candidates = []
        
        # Search Outline for similar articles
        search_query = f"{issue_title} {problem_description[:200]}"
        outline_results = await self.kb_writer.search_existing_articles(search_query, limit=10)
        
        # Check our index for matching articles
        for result in outline_results:
            doc_id = result.get("id")
            if not doc_id:
                continue
            
            # Check if we have this in our index
            indexed_article = self.db.query(KBArticleIndex).filter(
                KBArticleIndex.outline_document_id == doc_id
            ).first()
            
            if indexed_article:
                # Calculate title similarity (simple for now, can use embeddings later)
                title_similarity = self._calculate_text_similarity(
                    issue_title.lower(),
                    indexed_article.title.lower()
                )
                
                candidates.append({
                    "outline_document_id": doc_id,
                    "article_id": str(indexed_article.id),
                    "title": indexed_article.title,
                    "similarity": title_similarity,
                    "type": "indexed"
                })
            else:
                # Article exists in Outline but not in our index
                # Calculate similarity anyway
                title_similarity = self._calculate_text_similarity(
                    issue_title.lower(),
                    result.get("title", "").lower()
                )
                
                candidates.append({
                    "outline_document_id": doc_id,
                    "article_id": None,
                    "title": result.get("title", ""),
                    "similarity": title_similarity,
                    "type": "outline_only"
                })
        
        # Sort by similarity descending
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        
        return candidates
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity calculation (Jaccard-like)
        Can be replaced with embedding similarity later
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    async def decide_update_or_create(
        self,
        candidates: List[Dict[str, Any]],
        ai_confidence: float
    ) -> Literal["create", "update", "skip"]:
        """
        Decide whether to create, update, or skip based on similarity
        
        Rules:
        - similarity > 0.85 → update
        - 0.6-0.85 → update with variant section OR create if context different
        - < 0.6 → create
        - Low confidence (< 0.75) → skip
        """
        if ai_confidence < 0.75:
            return "skip"
        
        if not candidates or len(candidates) == 0:
            return "create"
        
        best_match = candidates[0]
        similarity = best_match.get("similarity", 0.0)
        
        if similarity > 0.85:
            return "update"
        elif similarity >= 0.6:
            # Check if context is materially different using AI
            # For now, default to update with variant section
            return "update"
        else:
            return "create"
    
    async def update_article(
        self,
        existing_doc_id: str,
        new_content: str,
        new_title: str,
        merge_strategy: str = "append_variant"
    ) -> KBUpdateResult:
        """
        Update an existing article
        
        merge_strategy: "append_variant", "replace", "merge_sections"
        """
        try:
            # Get current article from index
            article = self.db.query(KBArticleIndex).filter(
                KBArticleIndex.outline_document_id == existing_doc_id
            ).first()
            
            if not article:
                return KBUpdateResult(
                    success=False,
                    error=f"Article {existing_doc_id} not found in index"
                )
            
            # Get latest revision
            latest_revision = self.db.query(KBArticleRevision).filter(
                KBArticleRevision.outline_document_id == existing_doc_id
            ).order_by(KBArticleRevision.revision_number.desc()).first()
            
            revision_number = (latest_revision.revision_number + 1) if latest_revision else 1
            old_content = latest_revision.content if latest_revision else ""
            
            # Merge content based on strategy
            if merge_strategy == "append_variant":
                merged_content = f"{old_content}\n\n---\n\n## New Variant / Troubleshooting\n\n{new_content}"
            elif merge_strategy == "replace":
                merged_content = new_content
            elif merge_strategy == "merge_sections":
                # Try to intelligently merge sections
                merged_content = await self._merge_article_sections(old_content, new_content)
            else:
                merged_content = f"{old_content}\n\n---\n\n{new_content}"
            
            # Update in Outline (this would require an update API endpoint)
            # For now, we'll create a new revision record
            # In production, you'd call Outline's update API
            
            # Create revision record
            revision = KBArticleRevision(
                outline_document_id=existing_doc_id,
                article_id=article.id,
                revision_number=revision_number,
                title=new_title,
                content=merged_content,
                created_by="ai"
            )
            self.db.add(revision)
            
            # Update index
            article.title = new_title
            article.last_updated_at = datetime.utcnow()
            self.db.commit()
            
            return KBUpdateResult(
                success=True,
                outline_document_id=existing_doc_id,
                action="updated",
                revision_number=revision_number
            )
        except Exception as e:
            return KBUpdateResult(
                success=False,
                error=str(e)
            )
    
    async def _merge_article_sections(self, old_content: str, new_content: str) -> str:
        """Intelligently merge article sections using AI"""
        try:
            prompt = f"""Merge these two KB article versions, keeping the best information from both:

Old Version:
{old_content[:2000]}

New Version:
{new_content[:2000]}

Return the merged markdown content, maintaining structure and removing duplicates."""
            
            headers = {}
            if self.ai_client.api_key:
                headers["Authorization"] = f"Bearer {self.ai_client.api_key}"
            
            payload = {
                "prompt": prompt,
                "operation": "merge_kb_articles",
                "max_tokens": 2000,
                "temperature": 0.3
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
                merged = result.get("response", result.get("answer", old_content))
                
                # Extract markdown if wrapped
                if "```markdown" in merged:
                    start = merged.find("```markdown") + 11
                    end = merged.find("```", start)
                    merged = merged[start:end].strip()
                elif "```" in merged:
                    start = merged.find("```") + 3
                    end = merged.find("```", start)
                    merged = merged[start:end].strip()
                
                return merged
        except Exception as e:
            # Fallback to simple append
            return f"{old_content}\n\n---\n\n{new_content}"
    
    async def create_article(
        self,
        title: str,
        content: str,
        tenant_level: str = "global",
        tenant_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None
    ) -> KBCreateResult:
        """
        Create a new KB article and index it
        """
        try:
            # Create article in Outline
            kb_result = await self.kb_writer.create_kb_article(
                title=title,
                content=content,
                tags=tags or [],
                publish=False  # Always draft initially
            )
            
            if not kb_result.get("kb_created"):
                return KBCreateResult(
                    success=False,
                    error=kb_result.get("error", "Failed to create article in Outline")
                )
            
            outline_doc_id = kb_result.get("document_id")
            
            # Index the article
            article = KBArticleIndex(
                outline_document_id=outline_doc_id,
                title=title,
                tags=tags or [],
                tenant_level=tenant_level,
                tenant_id=tenant_id,
                is_active=True
            )
            self.db.add(article)
            self.db.flush()  # Get the ID
            
            # Create initial revision
            revision = KBArticleRevision(
                outline_document_id=outline_doc_id,
                article_id=article.id,
                revision_number=1,
                title=title,
                content=content,
                created_by="ai"
            )
            self.db.add(revision)
            self.db.commit()
            
            return KBCreateResult(
                success=True,
                outline_document_id=outline_doc_id,
                article_id=article.id
            )
        except Exception as e:
            self.db.rollback()
            return KBCreateResult(
                success=False,
                error=str(e)
            )
    
    def log_decision(
        self,
        support_log_id: Optional[uuid.UUID],
        decision: str,
        reason: str,
        similarity_score: Optional[Dict[str, Any]] = None,
        outline_document_id: Optional[str] = None
    ):
        """Log a decision made by the agent"""
        log = KBDecisionLog(
            support_log_id=support_log_id,
            decision=decision,
            reason=reason,
            similarity_score=json.dumps(similarity_score) if similarity_score else None,
            outline_document_id=outline_document_id
        )
        self.db.add(log)
        self.db.commit()

