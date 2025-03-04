"""Example script for processing a single date."""

import os
import asyncio
import logging
from datetime import datetime
import json

from src.pipeline import (
    CryptoEventPipeline,
    format_date_for_display,
    summarize_events,
    summarize_search_results,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def process_single_date():
    """Process a single date."""
    # Get API keys from environment variables
    exa_api_key = os.environ.get("EXA_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    # Check if API keys are available
    if not exa_api_key or not openai_api_key:
        logger.error(
            "Missing required API keys. Set EXA_API_KEY and OPENAI_API_KEY environment variables."
        )
        return

    # Initialize pipeline
    pipeline = CryptoEventPipeline(
        exa_api_key=exa_api_key,
        openai_api_key=openai_api_key,
    )

    # Define date - example: Bitcoin halving in May 2020
    date = datetime(2020, 5, 11)

    logger.info(f"Processing date: {format_date_for_display(date)}")

    # Process date with a specific query
    query = "Bitcoin halving event and price impact"

    logger.info(f"Running query: {query}")
    search_result, events = await pipeline.process_date(
        date=date,
        base_query=query,
        max_results=15,
    )

    logger.info(f"Found {len(events)} events")

    # Print search results summary
    search_summary = summarize_search_results(search_result)
    logger.info(f"Search query: {search_summary['query']}")
    logger.info(f"Search date: {search_summary['date']}")
    logger.info(f"Number of search results: {search_summary['result_count']}")

    logger.info("Top search results:")
    for i, result in enumerate(search_summary["top_results"]):
        logger.info(f"  {i+1}. {result['title']} ({result['published_date']})")

    # Print events summary
    events_summary = summarize_events(events)
    logger.info(f"Number of events: {events_summary['count']}")

    if events_summary["date_range"]:
        logger.info(
            f"Event date range: {events_summary['date_range']['start']} to {events_summary['date_range']['end']}"
        )

    logger.info("Top events:")
    for i, event in enumerate(events_summary["top_events"]):
        logger.info(
            f"  {i+1}. {event['title']} (Rank: {event['rank']}, Score: {event['score']})"
        )

    # Save events to a file
    output_file = f"bitcoin_events_{format_date_for_display(date)}.json"

    # Format events for output
    output_events = []
    for event in events:
        output_events.append(
            {
                "date": format_date_for_display(event.event_date),
                "title": event.title,
                "description": event.description,
                "url": event.source_url,
                "rank": event.rank,
                "relevance_score": event.relevance_score,
                "relevance_reasoning": event.relevance_reasoning,
            }
        )

    with open(output_file, "w") as f:
        json.dump(output_events, f, indent=2)

    logger.info(f"Saved {len(output_events)} events to {output_file}")


if __name__ == "__main__":
    asyncio.run(process_single_date())
