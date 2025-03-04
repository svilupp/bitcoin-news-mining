"""Pipeline for ranking cryptocurrency events stored in the database."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from src.db import MongoDB
from src.llm.ranker import EventRanker
from src.models import Event
from src.pipeline.utils import format_date_for_display

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CryptoEventRankingPipeline:
    """Pipeline for ranking cryptocurrency events stored in the database."""

    def __init__(
        self,
        openai_api_key: str,
        openai_model: str = "gpt-4o-mini",
        db_path: str = "./db",
        log_path: str = "./logs/mongodb.log",
        db_port: int = 27017,
        db_name: str = "bitcoin_news",
        load_db: bool = True,
    ):
        """Initialize the ranking pipeline.

        Args:
            openai_api_key: API key for OpenAI
            openai_model: OpenAI model to use for ranking
            db_path: Path to store MongoDB data
            log_path: Path to store MongoDB logs
            db_port: MongoDB port
            db_name: MongoDB database name
            load_db: Whether to load the database
        """
        from openai import AsyncOpenAI

        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)

        # Initialize ranker
        self.ranker = EventRanker(client=self.openai_client, model_name=openai_model)

        # Initialize database
        if load_db:
            self.db = MongoDB(
                data_path=db_path,
                log_path=log_path,
                port=db_port,
                db_name=db_name,
            )
        else:
            self.db = None

    async def rank_events_for_date(
        self,
        date: datetime,
        query: Optional[str] = None,
        min_relevance_score: int = 0,
    ) -> List[Event]:
        """Rank events for a specific date.

        Args:
            date: Date to rank events for
            query: Optional query to filter events by search query
            min_relevance_score: Minimum relevance score for events to be ranked

        Returns:
            List of ranked events
        """
        logger.info(f"Ranking events for date: {format_date_for_display(date)}")

        # Step 1: Retrieve events from database
        events = self.db.get_events_by_date(date)

        if query:
            # Filter events by search query if provided
            search_results = self.db.get_search_results_by_query_and_date(query, date)
            search_result_ids = [sr.id for sr in search_results]
            events = [e for e in events if e.search_result_id in search_result_ids]

            logger.info(f"Filtered events by query '{query}': {len(events)} events")

        # Filter events by relevance score
        events = [e for e in events if e.relevance_score >= min_relevance_score]
        logger.info(
            f"Found {len(events)} events with relevance score >= {min_relevance_score}"
        )

        if not events:
            logger.warning(f"No events found for date {format_date_for_display(date)}")
            return []

        # Step 2: Prepare events for ranking
        events_for_ranking = [
            {
                "title": event.title,
                "description": event.description,
                "url": event.source_url,
            }
            for event in events
        ]

        # Step 3: Rank events
        logger.info(f"Ranking {len(events)} events")
        rankings = await self.ranker.rank_events(
            events=events_for_ranking,
            event_date=date,
        )

        # Step 4: Apply rankings to events
        ranked_events = self.ranker.apply_rankings(events, rankings)

        # Update event in database
        for event in ranked_events:
            self.db.update_event(event)
            logger.info(f"Updated event rank: {event.title} (Rank: {event.rank})")

        # Log ranking results
        logger.info(f"Ranking complete for {format_date_for_display(date)}")
        logger.info(f"Ranking reasoning: {rankings.reasoning}")

        for i, event in enumerate(ranked_events[:5]):
            logger.info(f"Top event {i+1}: {event.title} (Rank: {event.rank})")

        return ranked_events

    async def rank_events_for_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        query: Optional[str] = None,
        min_relevance_score: int = 0,
    ) -> Dict[str, List[Event]]:
        """Rank events for a range of dates.

        Args:
            start_date: Start date to rank events for
            end_date: End date to rank events for
            query: Optional query to filter events by search query
            min_relevance_score: Minimum relevance score for events to be ranked

        Returns:
            Dictionary mapping date strings to lists of ranked events
        """
        logger.info(
            f"Ranking events for date range: {format_date_for_display(start_date)} to {format_date_for_display(end_date)}"
        )

        # Get all dates in range
        current_date = start_date
        results = {}

        while current_date <= end_date:
            date_str = format_date_for_display(current_date)
            logger.info(f"Processing date: {date_str}")

            ranked_events = await self.rank_events_for_date(
                date=current_date,
                query=query,
                min_relevance_score=min_relevance_score,
            )

            results[date_str] = ranked_events

            # Move to next date
            current_date = current_date.replace(day=current_date.day + 1)

        return results

    async def rank_events_for_queries(
        self,
        date: datetime,
        queries: List[str],
        min_relevance_score: int = 0,
    ) -> Dict[str, List[Event]]:
        """Rank events for multiple queries for the same date.

        Args:
            date: Date to rank events for
            queries: List of queries to rank events for
            min_relevance_score: Minimum relevance score for events to be ranked

        Returns:
            Dictionary mapping queries to lists of ranked events
        """
        logger.info(
            f"Ranking events for {len(queries)} queries on {format_date_for_display(date)}"
        )

        results = {}

        for query in queries:
            logger.info(f"Processing query: '{query}'")

            ranked_events = await self.rank_events_for_date(
                date=date,
                query=query,
                min_relevance_score=min_relevance_score,
            )

            results[query] = ranked_events

        return results

    def get_top_events(
        self,
        events: List[Event],
        top_n: int = 5,
    ) -> List[Event]:
        """Get the top N ranked events.

        Args:
            events: List of events to get top N from
            top_n: Number of top events to return

        Returns:
            List of top N ranked events
        """
        # Sort events by rank
        sorted_events = sorted(events, key=lambda e: e.rank or float("inf"))

        # Return top N events
        return sorted_events[:top_n]
