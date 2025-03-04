#!/usr/bin/env python
"""Script to process event titles and descriptions."""

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

from src.llm.processor import EventProcessor, ProcessedEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run event processing."""
    parser = argparse.ArgumentParser(
        description="Process event titles and descriptions"
    )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input JSON file with evaluated search results",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="processed_events.json",
        help="Output file for processed events (default: processed_events.json)",
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

    # Load evaluated results
    try:
        with open(args.input, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load evaluated results: {str(e)}")
        sys.exit(1)

    # Get relevant events
    events = data.get("relevant_events", [])
    if not events:
        logger.error("No relevant events found in input file")
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

    # Initialize event processor
    processor = EventProcessor(api_key=api_key)

    logger.info(
        f"Processing {len(events)} events for date {event_date.strftime('%Y-%m-%d')}"
    )

    # Process each event
    processed_events = []

    for i, event in enumerate(events):
        logger.info(f"Processing event {i+1}/{len(events)}")

        try:
            # Process event
            processed = processor.process_event(event, event_date)

            # Create updated event with processed data
            updated_event = {
                **event,
                "title": processed.title,
                "description": processed.description,
                "processed": True,
            }

            processed_events.append(updated_event)

        except Exception as e:
            logger.error(f"Error processing event {i+1}: {str(e)}")
            # Add event without processing
            processed_events.append(
                {**event, "processed": False, "processing_error": str(e)}
            )

    # Save processed events
    output_data = {
        "query": data.get("query", ""),
        "search_date": data.get("search_date", ""),
        "provider": data.get("provider", "unknown"),
        "processed_events": processed_events,
        "summary": {
            "total_events": len(events),
            "processed_events": len(
                [e for e in processed_events if e.get("processed", False)]
            ),
            "processing_date": datetime.utcnow().isoformat(),
        },
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2, default=str)

    logger.info(f"Processing complete. Processed {len(processed_events)} events.")
    logger.info(f"Results saved to {args.output}")

    # Print summary of processed events
    if processed_events:
        print(f"\nProcessed {len(processed_events)} events:")
        for i, event in enumerate(processed_events, 1):
            if event.get("processed", False):
                print(f"\n{i}. {event['title']}")
                print(f"   {event['description'][:150]}...")
            else:
                print(f"\n{i}. [PROCESSING ERROR] {event['title']}")
    else:
        print("\nNo events were processed.")


if __name__ == "__main__":
    main()
