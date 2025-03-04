"""Main script for running the Bitcoin news mining pipeline."""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime, timedelta

from src.pipeline import (
    CryptoEventPipeline,
    parse_date_string,
    generate_date_range,
    summarize_events,
    summarize_search_results,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_pipeline(args):
    """Run the pipeline with the given arguments."""
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
        openai_model=args.model,
    )

    # Process single date
    if args.date:
        date = parse_date_string(args.date)
        if not date:
            return

        search_result, events = await pipeline.process_date(
            date=date,
            base_query=args.query,
            full_month=args.full_month,
            max_results=args.max_results,
        )

        # Print results
        logger.info(f"Found {len(events)} events for {date.strftime('%Y-%m-%d')}")
        for i, event in enumerate(events):
            logger.info(f"Event {i+1}: {event.title} (Rank: {event.rank})")

    # Process date range
    elif args.start_date and args.end_date:
        start_date = parse_date_string(args.start_date)
        end_date = parse_date_string(args.end_date)

        if not start_date or not end_date:
            return

        if start_date > end_date:
            logger.error("Start date must be before end date")
            return

        results = await pipeline.process_date_range(
            start_date=start_date,
            end_date=end_date,
            base_query=args.query,
            full_month=args.full_month,
            max_results=args.max_results,
        )

        # Print summary
        logger.info(
            f"Processed {len(results)} dates from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )
        total_events = sum(len(events) for _, _, events in results)
        logger.info(f"Found {total_events} events in total")

        # Print top events for each date
        for date, _, events in results:
            if events:
                logger.info(f"Date: {date.strftime('%Y-%m-%d')} - {len(events)} events")
                for i, event in enumerate(
                    sorted(events, key=lambda e: e.rank or float("inf"))[:3]
                ):
                    logger.info(f"  Event {i+1}: {event.title} (Rank: {event.rank})")

    # Default to current date
    else:
        date = datetime.now()
        search_result, events = await pipeline.process_date(
            date=date,
            base_query=args.query,
            full_month=args.full_month,
            max_results=args.max_results,
        )

        # Print results
        logger.info(f"Found {len(events)} events for {date.strftime('%Y-%m-%d')}")
        for i, event in enumerate(events):
            logger.info(f"Event {i+1}: {event.title} (Rank: {event.rank})")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Bitcoin News Mining Pipeline")

    # Date arguments
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--date", help="Date to process (YYYY-MM-DD)")
    date_group.add_argument("--start-date", help="Start date for range (YYYY-MM-DD)")

    parser.add_argument("--end-date", help="End date for range (YYYY-MM-DD)")

    # Query arguments
    parser.add_argument(
        "--query",
        default="Bitcoin cryptocurrency news and developments",
        help="Base search query",
    )
    parser.add_argument(
        "--full-month",
        action="store_true",
        help="Search for a full month instead of an exact date",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=15,
        help="Maximum number of search results to retrieve",
    )

    # Model arguments
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use",
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()
    await run_pipeline(args)


if __name__ == "__main__":
    asyncio.run(main())
