#!/usr/bin/env python
"""Script to save events to MongoDB."""

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

from src.db import MongoDB
from src.models import Event, SearchResult

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Save events to MongoDB."""
    parser = argparse.ArgumentParser(description="Save events to MongoDB")

    parser.add_argument(
        "--input", type=str, required=True, help="Input JSON file with ranked events"
    )
    parser.add_argument(
        "--search-results",
        action="store_true",
        help="Also save the original search results to MongoDB",
    )
    parser.add_argument(
        "--connection-string",
        type=str,
        help="MongoDB connection string (overrides MONGODB_URI environment variable)",
    )
    parser.add_argument(
        "--db-name",
        type=str,
        default="bitcoin_news",
        help="MongoDB database name (default: bitcoin_news)",
    )

    args = parser.parse_args()

    # Get MongoDB connection string
    connection_string = args.connection_string or os.environ.get("MONGODB_URI")
    if not connection_string:
        logger.error(
            "MongoDB connection string not provided. Use --connection-string or set MONGODB_URI environment variable"
        )
        sys.exit(1)

    # Load events
    try:
        with open(args.input, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load events: {str(e)}")
        sys.exit(1)

    # Get events
    events = (
        data.get("ranked_events", [])
        or data.get("processed_events", [])
        or data.get("relevant_events", [])
    )
    if not events:
        logger.error("No events found in input file")
        sys.exit(1)

    # Connect to MongoDB
    try:
        db = MongoDB(connection_string=connection_string, db_name=args.db_name)
        logger.info(f"Connected to MongoDB database: {args.db_name}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        sys.exit(1)

    # Process search results if requested
    if args.search_results and data.get("query"):
        try:
            # Create search result object
            search_result = SearchResult(
                query=data.get("query", ""),
                search_date=(
                    datetime.fromisoformat(
                        data.get("search_date", "").replace("Z", "+00:00")
                    )
                    if data.get("search_date")
                    else datetime.utcnow()
                ),
                provider=data.get("provider", "unknown"),
                params=data.get("params", {}),
                results=data.get("evaluated_results", []) or data.get("results", []),
                summary=data.get("summary", None),
            )

            # Save to MongoDB
            search_id = db.save_search_result(search_result)
            logger.info(f"Saved search result to MongoDB with ID: {search_id}")

            # Add search_result_id to events
            for event in events:
                event["search_result_id"] = search_id

        except Exception as e:
            logger.error(f"Failed to save search result: {str(e)}")

    # Save events to MongoDB
    saved_events = 0
    for i, event_data in enumerate(events):
        try:
            # Parse event date
            event_date = None
            if "event_date" in event_data:
                try:
                    event_date = datetime.fromisoformat(
                        event_data["event_date"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            if not event_date and "date" in event_data:
                try:
                    event_date = datetime.fromisoformat(
                        event_data["date"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            if not event_date and data.get("search_date"):
                try:
                    event_date = datetime.fromisoformat(
                        data["search_date"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            if not event_date:
                logger.warning(
                    f"Could not determine date for event {i+1}, using current date"
                )
                event_date = datetime.utcnow()

            # Create event object
            event = Event(
                event_date=event_date,
                title=event_data.get("title", "Untitled"),
                description=event_data.get("description", ""),
                source_url=event_data.get("source_url", ""),
                source_title=event_data.get("source_title", None),
                search_result_id=event_data.get("search_result_id", None),
                provider=event_data.get("provider", data.get("provider", "unknown")),
                relevance_score=event_data.get("relevance_score", None),
                relevance_reasoning=event_data.get("relevance_reasoning", None),
                rank=event_data.get("rank", None),
            )

            # Save to MongoDB
            event_id = db.save_event(event)
            saved_events += 1

            if i < 5 or i % 10 == 0:  # Log first 5 and then every 10th
                logger.info(
                    f"Saved event {i+1}/{len(events)} to MongoDB with ID: {event_id}"
                )

        except Exception as e:
            logger.error(f"Failed to save event {i+1}: {str(e)}")

    logger.info(f"Saved {saved_events} of {len(events)} events to MongoDB")


if __name__ == "__main__":
    main()
