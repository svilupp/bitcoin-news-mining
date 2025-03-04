"""
Main script for running the Bitcoin news mining pipeline.

This script:
1. Sources events for dates 2023-06-01 to 2023-06-30
2. Sources events for 2023-06-01 with full_month=True to get monthly news
3. Ranks events for every date in the window 2023-06-01 to 2023-06-30
4. Exports top 5 ranked events for each date to CSV

The dates are hard-coded and progress is tracked with tqdm.
"""

import os
import asyncio
import logging
import csv
from datetime import datetime, timedelta
from tqdm import tqdm
import argparse

from src.pipeline import (
    CryptoEventPipeline,
    CryptoEventRankingPipeline,
    parse_date_string,
    format_date_for_display,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Hard-coded date range
START_DATE = "2013-06-01"
END_DATE = "2013-06-30"


async def source_events(pipeline, date, full_month=False):
    """Source events for a specific date."""
    try:
        search_result, events = await pipeline.process_date(
            date=date,
            base_query="Bitcoin cryptocurrency news and developments",
            full_month=full_month,
            max_results=15,
        )
        return date, events
    except Exception as e:
        logger.error(
            f"Error sourcing events for {format_date_for_display(date)}: {str(e)}"
        )
        return date, []


async def rank_events(pipeline, date):
    """Rank events for a specific date."""
    try:
        ranked_events = await pipeline.rank_events_for_date(
            date=date,
            query=None,  # No specific query filter
            min_relevance_score=1,
        )
        return date, ranked_events
    except Exception as e:
        logger.error(
            f"Error ranking events for {format_date_for_display(date)}: {str(e)}"
        )
        return date, []


async def export_ranked_events_to_csv(
    pipeline,
    start_date,
    end_date,
    output_file="data_processed/ranked_events_20250304.csv",
):
    """Export top 5 ranked events for each date to CSV."""
    logger.info(
        f"Exporting ranked events from {format_date_for_display(start_date)} to {format_date_for_display(end_date)}"
    )

    # Get all dates in range
    current_date = start_date
    all_events = []

    while current_date <= end_date:
        date_str = format_date_for_display(current_date)
        logger.info(f"Getting ranked events for: {date_str}")

        # Get events for this date
        events = pipeline.db.get_events_by_date(current_date, sorted_by_rank=True)

        # Get top 5 events
        top_events = pipeline.get_top_events(events, top_n=5)

        # Add to all events
        for event in top_events:
            all_events.append(
                {
                    "date": date_str,
                    "rank": event.rank,
                    "title": event.title,
                    "description": event.description,
                    "url": event.source_url,
                    "relevance_score": event.relevance_score,
                    "relevance_reasoning": event.relevance_reasoning,
                }
            )

        # Move to next date
        current_date = current_date + timedelta(days=1)

    # Write to CSV
    if all_events:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "date",
                "rank",
                "title",
                "description",
                "url",
                "relevance_score",
                "relevance_reasoning",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for event in all_events:
                writer.writerow(event)

        logger.info(f"Exported {len(all_events)} events to {output_file}")
    else:
        logger.warning("No events to export")


async def main():
    """Main entry point."""
    # Get API keys from environment variables
    exa_api_key = os.environ.get("EXA_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    # Check if API keys are available
    if not exa_api_key or not openai_api_key:
        logger.error(
            "Missing required API keys. Set EXA_API_KEY and OPENAI_API_KEY environment variables."
        )
        return

    # Parse dates
    start_date = parse_date_string(START_DATE)
    end_date = parse_date_string(END_DATE)

    if not start_date or not end_date:
        logger.error("Invalid date format")
        return

    # Initialize pipelines
    sourcing_pipeline = CryptoEventPipeline(
        exa_api_key=exa_api_key,
        openai_api_key=openai_api_key,
        openai_model="gpt-4o-mini",
    )

    ranking_pipeline = CryptoEventRankingPipeline(
        openai_api_key=openai_api_key,
        openai_model="gpt-4o-mini",
    )

    # Step 1: Source events for each date in the range
    logger.info(f"Sourcing events for dates {START_DATE} to {END_DATE}")

    # Generate list of dates
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date = current_date + timedelta(days=1)

    # Source events in parallel with progress tracking
    tasks = [source_events(sourcing_pipeline, date) for date in dates]

    results = []
    for f in tqdm(
        asyncio.as_completed(tasks), total=len(tasks), desc="Sourcing events"
    ):
        date, events = await f
        results.append((date, events))
        logger.info(f"Sourced {len(events)} events for {format_date_for_display(date)}")

    # Step 2: Source monthly events
    logger.info(f"Sourcing monthly events for {START_DATE}")
    monthly_date, monthly_events = await source_events(
        sourcing_pipeline, start_date, full_month=True
    )
    logger.info(
        f"Sourced {len(monthly_events)} monthly events for {format_date_for_display(monthly_date)}"
    )

    # Step 3: Rank events for each date in the range
    logger.info(f"Ranking events for dates {START_DATE} to {END_DATE}")

    # Rank events in parallel with progress tracking
    ranking_tasks = [rank_events(ranking_pipeline, date) for date in dates]

    ranking_results = []
    for f in tqdm(
        asyncio.as_completed(ranking_tasks),
        total=len(ranking_tasks),
        desc="Ranking events",
    ):
        date, ranked_events = await f
        ranking_results.append((date, ranked_events))
        logger.info(
            f"Ranked {len(ranked_events)} events for {format_date_for_display(date)}"
        )

    # Step 4: Export top 5 ranked events for each date to CSV
    await export_ranked_events_to_csv(
        ranking_pipeline,
        start_date,
        end_date,
        output_file=f"data_processed/bitcoin_top_events_{START_DATE}_to_{END_DATE}.csv",
    )

    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
