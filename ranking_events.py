"""Script for ranking cryptocurrency events stored in the database."""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime

from src.pipeline import (
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


async def run_ranking_pipeline(args):
    """Run the ranking pipeline with the given arguments."""
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
        openai_model=args.model,
    )

    # Process single date
    if args.date:
        date = parse_date_string(args.date)
        if not date:
            return

        # Rank events for date
        ranked_events = await pipeline.rank_events_for_date(
            date=date,
            query=args.query,
            min_relevance_score=args.min_score,
        )

        # Print results
        logger.info(
            f"Ranked {len(ranked_events)} events for {format_date_for_display(date)}"
        )
        logger.info("Top 5 events:")
        for i, event in enumerate(ranked_events[:5]):
            logger.info(
                f"  {i+1}. {event.title} (Rank: {event.rank}, Score: {event.relevance_score})"
            )

    # Process date range
    elif args.start_date and args.end_date:
        start_date = parse_date_string(args.start_date)
        end_date = parse_date_string(args.end_date)

        if not start_date or not end_date:
            return

        if start_date > end_date:
            logger.error("Start date must be before end date")
            return

        # Rank events for date range
        results = await pipeline.rank_events_for_date_range(
            start_date=start_date,
            end_date=end_date,
            query=args.query,
            min_relevance_score=args.min_score,
        )

        # Print summary
        logger.info(
            f"Processed {len(results)} dates from {format_date_for_display(start_date)} to {format_date_for_display(end_date)}"
        )

        # Print top events for each date
        for date_str, events in results.items():
            if events:
                logger.info(f"Date: {date_str} - {len(events)} events")
                for i, event in enumerate(events[:3]):
                    logger.info(f"  {i+1}. {event.title} (Rank: {event.rank})")
            else:
                logger.info(f"Date: {date_str} - No events found")

    # Process multiple queries
    elif args.queries:
        date = parse_date_string(args.date or datetime.now().strftime("%Y-%m-%d"))
        if not date:
            return

        # Split queries by comma
        queries = [q.strip() for q in args.queries.split(",")]

        # Rank events for queries
        results = await pipeline.rank_events_for_queries(
            date=date,
            queries=queries,
            min_relevance_score=args.min_score,
        )

        # Print summary
        logger.info(
            f"Processed {len(queries)} queries for {format_date_for_display(date)}"
        )

        # Print top events for each query
        for query, events in results.items():
            if events:
                logger.info(f"Query: '{query}' - {len(events)} events")
                for i, event in enumerate(events[:3]):
                    logger.info(f"  {i+1}. {event.title} (Rank: {event.rank})")
            else:
                logger.info(f"Query: '{query}' - No events found")

    # Default to current date
    else:
        date = datetime.now()

        # Rank events for date
        ranked_events = await pipeline.rank_events_for_date(
            date=date,
            query=args.query,
            min_relevance_score=args.min_score,
        )

        # Print results
        logger.info(
            f"Ranked {len(ranked_events)} events for {format_date_for_display(date)}"
        )
        logger.info("Top 5 events:")
        for i, event in enumerate(ranked_events[:5]):
            logger.info(
                f"  {i+1}. {event.title} (Rank: {event.rank}, Score: {event.relevance_score})"
            )


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Bitcoin News Ranking Pipeline")

    # Date arguments
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--date", help="Date to rank events for (YYYY-MM-DD)")
    date_group.add_argument("--start-date", help="Start date for range (YYYY-MM-DD)")

    parser.add_argument("--end-date", help="End date for range (YYYY-MM-DD)")

    # Query arguments
    parser.add_argument(
        "--query",
        help="Query to filter events by",
    )
    parser.add_argument(
        "--queries",
        help="Comma-separated list of queries to compare",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=1,
        help="Minimum relevance score for events to be ranked",
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
    await run_ranking_pipeline(args)


if __name__ == "__main__":
    asyncio.run(main())
