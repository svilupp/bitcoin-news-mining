"""Exa API search utility."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from exa_py import Exa

from src.models import SearchResult

logger = logging.getLogger(__name__)


class ExaSearch:
    """Exa API search client."""

    def __init__(self, api_key: str):
        """Initialize Exa client.

        Args:
            api_key: Exa API key
        """
        self.client = Exa(api_key=api_key)

    def search(
        self,
        query: str,
        search_date: Optional[datetime] = None,
        max_results: int = 10,
        highlights: bool = True,
        text: bool = True,
        category: str = "news",
        type: str = "auto",
        use_autoprompt: bool = True,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        published_window_days: int = 7,
        **kwargs,
    ) -> SearchResult:
        """Search for news articles using Exa.

        Args:
            query: Search query
            search_date: Date to use for the search (defaults to current date)
            max_results: Maximum number of results to return
            use_autoprompt: Whether to use autoprompt for better results
            **kwargs: Additional search parameters

        Returns:
            SearchResult object with search results
        """
        # Prepare search parameters
        start_published_date = (
            search_date.strftime("%Y-%m-%d")
            if start_published_date is None
            else start_published_date
        )
        end_published_date = (
            (search_date + timedelta(days=published_window_days)).strftime("%Y-%m-%d")
            if end_published_date is None
            else end_published_date
        )
        search_params = {
            "num_results": max_results,
            "text": text,
            "start_published_date": start_published_date,
            "end_published_date": end_published_date,
            "category": category,
            "type": type,
            "use_autoprompt": use_autoprompt,
            "highlights": highlights,
            **kwargs,
        }

        try:
            # Execute search
            logger.info(f"Executing Exa search with query: {query}")
            response = self.client.search_and_contents(query, **search_params)

            # Transform response into expected format
            results = []
            for result in response.results:
                results.append(
                    {
                        "url": result.url,
                        "title": result.title,
                        "content": result.text,
                        "score": result.score,
                        "published_date": result.published_date,
                        "highlights": (
                            result.highlights if hasattr(result, "highlights") else None
                        ),
                        "summary": (
                            result.summary if hasattr(result, "summary") else None
                        ),
                        "score": result.score,
                    }
                )

            # Create search result model
            result = SearchResult(
                query=query,
                search_date=search_date or datetime.utcnow(),
                provider="exa",
                params={**search_params},
                results=results,
            )

            return result

        except Exception as e:
            logger.error(f"Exa search error: {str(e)}")
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
