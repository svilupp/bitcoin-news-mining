#!/usr/bin/env python
"""Script to rank events by their importance."""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.ranker import EventRanker

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run event ranking."""
    parser = argparse.ArgumentParser(description="Rank events by historical importance")

    parser.add_argument(
        "--input", type=str, required=True, help="Input JSON file with processed events"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ranked_events.json",
        help="Output file for ranked events (default: ranked_events.json)",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date for events in YYYY-MM-DD format (overrides date in input file)",
    )

    args = parser.parse_args()

    # Get Google API key from environment variable
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set")
        sys.exit(1)

    # Load processed events
    try:
        with open(args.input, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load processed events: {str(e)}")
        sys.exit(1)

    # Get events
    events = data.get("processed_events", [])
    if not events:
        logger.error("No events found in input file")
        sys.exit(1)

    # Parse the date from arguments or input file
    if args.date:
        try:
            event_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD format.")
            sys.exit(1)
    else:
        # Try to get date from input file
        search_date_str = data.get("search_date")
        if not search_date_str:
            logger.error("No date provided in command line or input file")
            sys.exit(1)

        try:
            event_date = datetime.fromisoformat(search_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            logger.error(f"Invalid date format in input file: {search_date_str}")
            sys.exit(1)

    # Initialize event ranker
    ranker = EventRanker(api_key=api_key)

    logger.info(
        f"Ranking {len(events)} events for date {event_date.strftime('%Y-%m-%d')}"
    )

    try:
        # Rank events
        ranked = ranker.rank_events(events, event_date)

        # Apply rankings to events
        for i, rank in enumerate(ranked.rankings):
            if i < len(events):
                events[i]["rank"] = rank

        # Sort events by rank
        ranked_events = sorted(events, key=lambda e: e.get("rank", 999))

        # Save ranked events
        output_data = {
            "query": data.get("query", ""),
            "search_date": data.get("search_date", ""),
            "provider": data.get("provider", "unknown"),
            "ranked_events": ranked_events,
            "ranking_reasoning": ranked.reasoning,
            "summary": {
                "total_events": len(events),
                "ranking_date": datetime.utcnow().isoformat(),
            },
        }

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

        logger.info(f"Ranking complete. Ranked {len(events)} events.")
        logger.info(f"Results saved to {args.output}")

        # Print summary of ranked events
        if ranked_events:
            print(f"\nRanked {len(ranked_events)} events:")
            print(f"\nRanking reasoning: {ranked.reasoning}\n")
            for event in ranked_events:
                print(f"\nRank {event.get('rank', 'N/A')}: {event['title']}")
                print(f"   {event['description'][:150]}...")
        else:
            print("\nNo events were ranked.")

    except Exception as e:
        logger.error(f"Error ranking events: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
