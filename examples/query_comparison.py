"""Example script for comparing different queries for the same date."""

import os
import asyncio
import logging
from datetime import datetime
import json

from src.pipeline import (
    CryptoEventPipeline,
    format_date_for_display,
    summarize_events,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def compare_queries():
    """Compare different queries for the same date."""
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

    # Define date - example: El Salvador adopting Bitcoin as legal tender
    date = datetime(2021, 6, 9)

    logger.info(f"Processing date: {format_date_for_display(date)}")

    # Define queries to compare
    queries = [
        "Bitcoin cryptocurrency news and developments",
        "Bitcoin adoption as legal tender",
        "El Salvador Bitcoin news",
        "Bitcoin regulatory developments",
    ]

    # Process each query
    results = {}
    for query in queries:
        logger.info(f"Running query: {query}")
        search_result, events = await pipeline.process_date(
            date=date,
            base_query=query,
            max_results=10,
        )

        logger.info(f"Found {len(events)} events")

        # Store results
        results[query] = {
            "search_result": search_result,
            "events": events,
        }

    # Compare results
    logger.info("\n=== Query Comparison ===")

    for query, result in results.items():
        events = result["events"]
        events_summary = summarize_events(events)

        logger.info(f"\nQuery: {query}")
        logger.info(f"Number of events: {events_summary['count']}")

        logger.info("Top events:")
        for i, event in enumerate(events_summary["top_events"]):
            logger.info(
                f"  {i+1}. {event['title']} (Rank: {event['rank']}, Score: {event['score']})"
            )

    # Find unique events across all queries
    all_events = []
    for query, result in results.items():
        for event in result["events"]:
            # Check if event is already in all_events
            is_duplicate = False
            for existing_event in all_events:
                if existing_event["title"] == event.title and existing_event[
                    "date"
                ] == format_date_for_display(event.event_date):
                    is_duplicate = True
                    # Add query to existing event
                    existing_event["queries"].append(query)
                    break

            if not is_duplicate:
                all_events.append(
                    {
                        "date": format_date_for_display(event.event_date),
                        "title": event.title,
                        "description": event.description,
                        "url": event.source_url,
                        "rank": event.rank,
                        "relevance_score": event.relevance_score,
                        "queries": [query],
                    }
                )

    # Sort events by number of queries (most common first)
    all_events.sort(
        key=lambda e: (len(e["queries"]), e["rank"] or float("inf")), reverse=True
    )

    # Print unique events
    logger.info("\n=== Unique Events Across All Queries ===")
    logger.info(f"Found {len(all_events)} unique events")

    for i, event in enumerate(all_events):
        logger.info(f"\nEvent {i+1}: {event['title']}")
        logger.info(f"Date: {event['date']}")
        logger.info(f"Found in queries: {', '.join(event['queries'])}")
        logger.info(f"Rank: {event['rank']}")
        logger.info(f"Score: {event['relevance_score']}")

    # Save unique events to a file
    output_file = f"bitcoin_events_comparison_{format_date_for_display(date)}.json"
    with open(output_file, "w") as f:
        json.dump(all_events, f, indent=2)

    logger.info(f"\nSaved {len(all_events)} unique events to {output_file}")


if __name__ == "__main__":
    asyncio.run(compare_queries())
