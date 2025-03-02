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
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def dict_for_db(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for MongoDB storage."""
        data = self.model_dump(exclude={"id"})
        return data


class Event(BaseModel):
    """Model for Bitcoin/crypto relevant events."""

    id: Optional[str] = None
    event_date: datetime
    title: str
    description: str
    source_url: HttpUrl
    source_title: Optional[str] = None
    search_result_id: Optional[str] = None  # reference to the SearchResult
    provider: str  # which search provider found this event
    relevance_score: Optional[float] = None  # score from LLM judge (0-1)
    relevance_reasoning: Optional[str] = None  # reasoning from LLM judge
    rank: Optional[int] = None  # rank among other events for the same date
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def dict_for_db(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for MongoDB storage."""
        data = self.model_dump(exclude={"id"})
        return data
