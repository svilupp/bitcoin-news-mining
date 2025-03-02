"""Exa API search utility."""

import logging
from datetime import datetime
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
        text_max_chars: int = 1000,
        highlight_results: bool = True,
        use_autoprompt: bool = True,
        **kwargs,
    ) -> SearchResult:
        """Search for news articles using Exa.

        Args:
            query: Search query
            search_date: Date to use for the search (defaults to current date)
            max_results: Maximum number of results to return
            text_max_chars: Maximum characters to return in content
            highlight_results: Whether to highlight search results
            use_autoprompt: Whether to use autoprompt for better results
            **kwargs: Additional search parameters

        Returns:
            SearchResult object with search results
        """
        # Prepare search parameters
        search_params = {
            "num_results": max_results,
            "use_autoprompt": use_autoprompt,
            **kwargs,
        }

        text_params = {
            "max_characters": text_max_chars,
            "highlight_results": highlight_results,
        }

        try:
            # Execute search
            logger.info(f"Executing Exa search with query: {query}")
            response = self.client.search_and_contents(
                query, **search_params, text=text_params
            )

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
                        "highlight": (
                            result.highlight if hasattr(result, "highlight") else None
                        ),
                    }
                )

            # Create search result model
            result = SearchResult(
                query=query,
                search_date=search_date or datetime.utcnow(),
                provider="exa",
                params={**search_params, "text": text_params},
                results=results,
            )

            return result

        except Exception as e:
            logger.error(f"Exa search error: {str(e)}")
            raise

    def format_crypto_query(self, base_query: str, date: datetime) -> str:
        """Format query for crypto/bitcoin news on a specific date.

        Args:
            base_query: Base search query
            date: Date to search for

        Returns:
            Formatted query string
        """
        formatted_date = date.strftime("%Y-%m-%d")
        return f"{base_query} date:{formatted_date}"
