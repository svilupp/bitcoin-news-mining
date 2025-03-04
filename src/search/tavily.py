"""Tavily API search utility."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tavily import TavilyClient

from src.models import SearchResult

logger = logging.getLogger(__name__)


class TavilySearch:
    """Tavily API search client."""

    def __init__(self, api_key: str):
        """Initialize Tavily client.

        Args:
            api_key: Tavily API key
        """
        self.client = TavilyClient(api_key=api_key)

    def search(
        self,
        query: str,
        search_date: Optional[datetime] = None,
        topic: str = "news",
        max_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        **kwargs,
    ) -> SearchResult:
        """Search for news articles using Tavily.

        Args:
            query: Search query
            search_date: Date to use for the search (defaults to current date)
            topic: Search topic category
            max_results: Maximum number of results to return
            include_domains: List of domains to include in the search
            exclude_domains: List of domains to exclude from the search
            **kwargs: Additional search parameters

        Returns:
            SearchResult object with search results
        """
        # Prepare search parameters
        search_params = {
            # "topic": topic,
            "max_results": max_results,
            "include_raw_content": True,
            **kwargs,
        }

        if include_domains:
            search_params["include_domains"] = include_domains

        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains

        try:
            # Execute search
            logger.info(f"Executing Tavily search with query: {query}")
            response = self.client.search(query, **search_params)

            results = []
            for result in response.get("results", []):
                results.append(
                    {
                        "url": result.get("url"),
                        "title": result.get("title"),
                        "summary": result.get("content"),
                        "content": result.get("raw_content"),
                        "score": result.get("score"),
                        "published_date": result.get("published_date"),
                        "score": result.get("score"),
                    }
                )

            # Create search result model
            result = SearchResult(
                query=query,
                search_date=search_date or datetime.utcnow(),
                provider="tavily",
                params=search_params,
                results=results,
                summary=response.get("answer"),
            )

            return result

        except Exception as e:
            logger.error(f"Tavily search error: {str(e)}")
            raise

    def format_crypto_query(
        self, base_query: str, date: datetime, full_month: bool = True
    ) -> str:
        """Format query for crypto/bitcoin news on a specific date or month/year.

        Args:
            base_query: Base search query
            date: Date to search for
            full_month: Whether to include month-level search (default: True)

        Returns:
            Formatted query string
        """

        formatted_date = (
            date.strftime("%Y-%m") if full_month else date.strftime("%Y-%m-%d")
        )
        return f"{base_query} date:{formatted_date}"
