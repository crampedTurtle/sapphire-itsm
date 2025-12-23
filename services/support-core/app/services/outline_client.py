"""
Outline KB adapter for knowledge retrieval
"""
import httpx
from typing import List, Dict, Optional, Any
from app.core.config import settings


class OutlineClient:
    """Client for Outline knowledge base"""
    
    def __init__(self):
        self.base_url = settings.OUTLINE_API_URL.rstrip("/")
        self.api_key = settings.OUTLINE_API_KEY
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search Outline content
        
        Returns:
            List of {
                "id": str,
                "title": str,
                "url": str,
                "snippet": str,
                "content": str (optional)
            }
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Outline API search endpoint
            response = await self.client.post(
                f"{self.base_url}/api/documents.search",
                json={"query": query, "limit": limit},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for doc in data.get("data", []):
                results.append({
                    "id": doc.get("id"),
                    "title": doc.get("title", ""),
                    "url": f"{self.base_url}/doc/{doc.get('urlId', '')}",
                    "snippet": doc.get("text", "")[:200] + "..." if len(doc.get("text", "")) > 200 else doc.get("text", ""),
                    "content": doc.get("text", "")
                })
            
            return results
        except Exception as e:
            # Fallback: return empty results
            return []
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/documents.info",
                params={"id": document_id},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            doc = data.get("data", {})
            return {
                "id": doc.get("id"),
                "title": doc.get("title", ""),
                "url": f"{self.base_url}/doc/{doc.get('urlId', '')}",
                "content": doc.get("text", "")
            }
        except Exception as e:
            return None
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance
_outline_client: Optional[OutlineClient] = None


def get_outline_client() -> OutlineClient:
    """Get singleton Outline client instance"""
    global _outline_client
    if _outline_client is None:
        _outline_client = OutlineClient()
    return _outline_client

