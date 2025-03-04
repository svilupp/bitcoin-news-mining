"""Example script for batch processing multiple dates."""

import os
import asyncio
import logging
from datetime import datetime, timedelta
import json

from src.pipeline import (
    CryptoEventPipeline,
    generate_date_range,
    format_date_for_display,
    summarize_events,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def process_historical_dates():
    """Process a range of historical dates."""
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

    # Define date range - example: Bitcoin price crash in May 2021
    start_date = datetime(2021, 5, 10)
    end_date = datetime(2021, 5, 20)

    # Generate date range
    dates = generate_date_range(start_date, end_date)

    logger.info(
        f"Processing {len(dates)} dates from {format_date_for_display(start_date)} to {format_date_for_display(end_date)}"
    )

    # Process each date
    all_events = []
    for date in dates:
        logger.info(f"Processing date: {format_date_for_display(date)}")

        # Process date with two different queries
        queries = [
            "Bitcoin price crash news and market sentiment",
            "Bitcoin cryptocurrency regulations and government actions",
        ]

        for query in queries:
            logger.info(f"Running query: {query}")
            search_result, events = await pipeline.process_date(
                date=date,
                base_query=query,
                max_results=10,
            )

            logger.info(f"Found {len(events)} events")

            # Store events with metadata
            for event in events:
                all_events.append(
                    {
                        "date": format_date_for_display(event.event_date),
                        "query_date": format_date_for_display(date),
                        "query": query,
                        "title": event.title,
                        "description": event.description,
                        "url": event.source_url,
                        "rank": event.rank,
                        "relevance_score": event.relevance_score,
                    }
                )

    # Save all events to a file
    output_file = f"bitcoin_events_{format_date_for_display(start_date)}_to_{format_date_for_display(end_date)}.json"
    with open(output_file, "w") as f:
        json.dump(all_events, f, indent=2)

    logger.info(f"Saved {len(all_events)} events to {output_file}")

    # Print summary
    logger.info(f"Processed {len(dates)} dates with {len(queries)} queries each")
    logger.info(f"Total events found: {len(all_events)}")


if __name__ == "__main__":
    asyncio.run(process_historical_dates())
