"""Data models for search results and events."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl


class SearchResult(BaseModel):
    """Model for storing search query results."""

    id: Optional[str] = None
    query: str
    search_date: datetime = Field(default_factory=datetime.utcnow)
    provider: str  # 'tavily' or 'exa'
    params: Dict[str, Any]  # any search parameters used
    results: List[Dict[str, Any]]  # raw results from the provider
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def dict_for_db(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for MongoDB storage."""
        data = self.model_dump(exclude={"id"})
        return data

    def format_results_for_prompt(self) -> str:
        """Format search results into a combined content string for LLM prompting."""
        combined_content = ""
        for i, item in enumerate(self.results):
            combined_content += f"News Item {i+1}:\n"
            combined_content += f"Title: {item.get('title', 'No title')}\n"
            combined_content += (
                f"Published date: {item.get('published_date', 'No published date')}\n"
            )
            combined_content += f"URL: {item.get('url', 'No URL')}\n"
            highlights = item.get("highlights")
            if highlights is None:
                highlights = item.get("summary")
                if highlights is None:
                    highlights = "No highlights"
            combined_content += f"Highlights: {highlights}\n"
            combined_content += f"Content: {item.get('content', 'No content')}\n\n---\n"
        return combined_content


class Event(BaseModel):
    """Model for Bitcoin/crypto relevant events."""

    id: Optional[str] = None
    event_date: datetime
    title: str
    description: str
    source_url: str  # Changed from HttpUrl to str for BSON compatibility
    source_title: Optional[str] = None
    search_result_id: Optional[str] = None  # reference to the SearchResult
    provider: str  # which search provider found this event
    relevance_score: Optional[int] = None  # score from LLM judge
    relevance_reasoning: Optional[str] = None  # reasoning from LLM judge
    rank: Optional[int] = None  # rank among other events for the same date
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def dict_for_db(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for MongoDB storage."""
        data = self.model_dump(exclude={"id"})
        return data
