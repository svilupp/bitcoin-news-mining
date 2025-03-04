"""Example script for ranking cryptocurrency events."""

import os
import asyncio
import logging
from datetime import datetime
import json

from src.pipeline import (
    CryptoEventRankingPipeline,
    format_date_for_display,
)

# Configure logging with colorful output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - \033[1;34m%(levelname)s\033[0m - %(message)s",
)
logger = logging.getLogger(__name__)


async def rank_bitcoin_halving_events():
    """Rank events related to Bitcoin halving."""
    # Get API key from environment variable
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    # Check if API key is available
    if not openai_api_key:
        logger.error(
            "Missing required API key. Set OPENAI_API_KEY environment variable."
        )
        return

    # Initialize pipeline
    pipeline = CryptoEventRankingPipeline(
        openai_api_key=openai_api_key,
    )

    # Define date - Bitcoin halving in May 2020
    date = datetime(2020, 5, 11)

    logger.info(
        f"\033[1;32m=== Ranking events for Bitcoin halving on {format_date_for_display(date)} ===\033[0m"
    )

    # Define queries to compare
    queries = [
        "Bitcoin halving event",
        "Bitcoin price impact",
        "Cryptocurrency market news",
    ]

    # Rank events for each query
    results = await pipeline.rank_events_for_queries(
        date=date,
        queries=queries,
    )

    # Print results for each query
    for query, events in results.items():
        if events:
            logger.info(
                f"\033[1;33m=== Query: '{query}' - {len(events)} events ===\033[0m"
            )

            # Get top 5 events
            top_events = pipeline.get_top_events(events, top_n=5)

            # Print top events
            for i, event in enumerate(top_events):
                logger.info(f"\033[1;36mEvent {i+1}:\033[0m {event.title}")
                logger.info(f"  Rank: {event.rank}")
                logger.info(f"  Score: {event.relevance_score}")
                logger.info(f"  URL: {event.source_url}")
                logger.info(f"  Description: {event.description[:100]}...")
                logger.info("")
        else:
            logger.warning(f"No events found for query: '{query}'")

    # Save results to file
    output_file = f"ranked_bitcoin_halving_events_{format_date_for_display(date)}.json"

    # Format results for output
    output_data = {
        "date": format_date_for_display(date),
        "queries": {},
    }

    for query, events in results.items():
        output_data["queries"][query] = [
            {
                "title": event.title,
                "rank": event.rank,
                "score": event.relevance_score,
                "url": event.source_url,
                "description": event.description,
            }
            for event in events
        ]

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"Saved results to {output_file}")


async def rank_events_for_date_range():
    """Rank events for a date range."""
    # Get API key from environment variable
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    # Check if API key is available
    if not openai_api_key:
        logger.error(
            "Missing required API key. Set OPENAI_API_KEY environment variable."
        )
        return

    # Initialize pipeline
    pipeline = CryptoEventRankingPipeline(
        openai_api_key=openai_api_key,
    )

    # Define date range - Bitcoin price crash in May 2021
    start_date = datetime(2021, 5, 10)
    end_date = datetime(2021, 5, 20)

    logger.info(
        f"\033[1;32m=== Ranking events from {format_date_for_display(start_date)} to {format_date_for_display(end_date)} ===\033[0m"
    )

    # Define query
    query = "Bitcoin price crash"

    # Rank events for date range
    results = await pipeline.rank_events_for_date_range(
        start_date=start_date,
        end_date=end_date,
        query=query,
    )

    # Print results for each date
    for date_str, events in results.items():
        if events:
            logger.info(
                f"\033[1;33m=== Date: {date_str} - {len(events)} events ===\033[0m"
            )

            # Get top 3 events
            top_events = pipeline.get_top_events(events, top_n=3)

            # Print top events
            for i, event in enumerate(top_events):
                logger.info(f"\033[1;36mEvent {i+1}:\033[0m {event.title}")
                logger.info(f"  Rank: {event.rank}")
                logger.info(f"  Score: {event.relevance_score}")
                logger.info("")
        else:
            logger.warning(f"No events found for date: {date_str}")

    # Save results to file
    output_file = f"ranked_events_{format_date_for_display(start_date)}_to_{format_date_for_display(end_date)}.json"

    # Format results for output
    output_data = {
        "query": query,
        "date_range": {
            "start": format_date_for_display(start_date),
            "end": format_date_for_display(end_date),
        },
        "dates": {},
    }

    for date_str, events in results.items():
        output_data["dates"][date_str] = [
            {
                "title": event.title,
                "rank": event.rank,
                "score": event.relevance_score,
                "url": event.source_url,
                "description": event.description,
            }
            for event in events
        ]

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"Saved results to {output_file}")


async def main():
    """Run the examples."""
    logger.info("\033[1;35m=== Bitcoin News Ranking Examples ===\033[0m")

    # Example 1: Rank events for Bitcoin halving
    await rank_bitcoin_halving_events()

    logger.info("\n")

    # Example 2: Rank events for a date range
    await rank_events_for_date_range()


if __name__ == "__main__":
    asyncio.run(main())
