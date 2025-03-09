"""End-to-end workflow for finding and storing crypto events."""

import logging
from datetime import datetime
from typing import List, Tuple, Optional

from openai import AsyncOpenAI

from src.db import MongoDB
from src.llm.judge import EventJudge, JUDGE_SYSTEM_PROMPT
from src.llm.ranker import EventRanker
from src.models import Event, SearchResult
from src.search.exa import ExaSearch


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CryptoEventPipeline:
    """End-to-end pipeline for finding and storing crypto events."""

    def __init__(
        self,
        exa_api_key: str,
        openai_api_key: str,
        openai_model: str = "gpt-4o-mini",
        db_path: str = "./db",
        log_path: str = "./logs/mongodb.log",
        db_port: int = 27017,
        db_name: str = "bitcoin_news",
        load_db: bool = True,
    ):
        """Initialize the pipeline.

        Args:
            exa_api_key: API key for Exa search
            openai_api_key: API key for OpenAI
            openai_model: OpenAI model to use for evaluation and ranking
            db_path: Path to store MongoDB data
            log_path: Path to store MongoDB logs
            db_port: MongoDB port
            db_name: MongoDB database name
            load_db: Whether to load the database
        """
        # Initialize search client
        self.search_client = ExaSearch(api_key=exa_api_key)

        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)

        # Initialize judge and ranker
        self.judge = EventJudge(client=self.openai_client, model_name=openai_model)
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

    async def process_date(
        self,
        date: datetime,
        base_query: str = "Bitcoin cryptocurrency news and developments",
        full_month: bool = False,
        max_results: int = 15,
        save_results: bool = True,
        judge_system_prompt: str = JUDGE_SYSTEM_PROMPT,
        judge_model: str = "gpt-4o-mini",
    ) -> Tuple[SearchResult, List[Event]]:
        """Process a specific date to find and store crypto events.

        Args:
            date: Date to process
            base_query: Base search query to use
            full_month: Whether to search for a full month or an exact date
            max_results: Maximum number of search results to retrieve
            save_results: Whether to save the search results to the database

        Returns:
            Tuple containing:
                - The SearchResult object with search results
                - List of Event objects that were found and stored
        """
        logger.info(f"Processing date: {date.strftime('%Y-%m-%d')}")

        # Step 1: Format query and run search
        formatted_query = self.search_client.format_crypto_query(
            base_query, date, full_month=full_month
        )
        # If we need exact date, limit to news for following 7 days // for month, pick 37
        published_window_days = 37 if full_month else 7
        search_result = self.search_client.search(
            query=formatted_query,
            search_date=date,
            max_results=max_results,
            published_window_days=published_window_days,
        )

        # Step 2: Save search result to database
        if save_results:
            search_result_id = self.db.save_search_result(search_result)
            search_result.id = search_result_id
            logger.info(f"Saved search result with ID: {search_result_id}")
        else:
            search_result_id = None

        # Step 3: Evaluate relevance with judge
        crypto_events = await self.judge.evaluate_relevance(
            search_result=search_result,
            query=formatted_query,
            query_date=date,
            model=judge_model,
            system_prompt=judge_system_prompt,
        )

        # Step 4: Convert judge results to Event objects
        events = []
        for i, crypto_event in enumerate(crypto_events.events):
            # Parse event date
            try:
                event_date = datetime.strptime(crypto_event.date, "%Y-%m-%d")
            except ValueError:
                logger.warning(
                    f"Invalid date format: {crypto_event.date}, using search date"
                )
                event_date = date

            # Create Event object
            event = Event(
                event_date=event_date,
                title=crypto_event.title,
                description=crypto_event.description,
                source_url=crypto_event.url,
                provider="exa",
                search_result_id=search_result_id,
                relevance_score=crypto_event.score,
                relevance_reasoning=crypto_event.reasoning,
            )
            events.append(event)

        # Step 5: Save events to database
        if save_results:
            logger.info(f"Saving {len(events)} events to database")
            for event in events:
                event_id = self.db.save_event(event)
                event.id = event_id
                logger.info(f"Saved event with ID: {event_id}")

        return search_result, events

    async def process_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        base_query: str = "Bitcoin cryptocurrency news and developments",
        full_month: bool = False,
        max_results: int = 15,
    ) -> List[Tuple[datetime, SearchResult, List[Event]]]:
        """Process a range of dates to find and store crypto events.

        Args:
            start_date: Start date to process
            end_date: End date to process
            base_query: Base search query to use
            full_month: Whether to search for a full month or an exact date
            max_results: Maximum number of search results to retrieve

        Returns:
            List of tuples containing:
                - The date processed
                - The SearchResult object with search results
                - List of Event objects that were found and stored
        """
        logger.info(
            f"Processing date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )

        results = []
        current_date = start_date

        while current_date <= end_date:
            search_result, events = await self.process_date(
                date=current_date,
                base_query=base_query,
                full_month=full_month,
                max_results=max_results,
            )

            results.append((current_date, search_result, events))

            # Move to next date
            current_date = current_date.replace(day=current_date.day + 1)

        return results
