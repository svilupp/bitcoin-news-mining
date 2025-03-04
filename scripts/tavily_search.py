#!/usr/bin/env python
"""Script to experiment with Tavily search API for Bitcoin news."""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import SearchResult
from src.search.tavily import TavilySearch

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run Tavily search experiment."""
    parser = argparse.ArgumentParser(
        description="Search for Bitcoin news using Tavily API"
    )

    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date to search for in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="Bitcoin cryptocurrency news",
        # default="The most significant world events for Bitcoin and other cryptocurrencies",
        help="Base topic to search for (default: 'bitcoin cryptocurrency')",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of results to retrieve (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data_raw/tavily_results.json",
        help="Output file for search results (default: tavily_results.json)",
    )
    parser.add_argument(
        "--time-range",
        type=str,
        choices=["day", "week", "month"],
        default="day",
        help="Time range for search (default: day)",
    )

    args = parser.parse_args()

    # Get Tavily API key from environment variable
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        logger.error("TAVILY_API_KEY environment variable not set")
        sys.exit(1)

    # Parse the date
    try:
        search_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD format.")
        sys.exit(1)

    # Initialize search client
    tavily = TavilySearch(api_key=api_key)

    # Format the query
    query = tavily.format_crypto_query(args.topic, search_date)
    logger.info(f"Searching Tavily with query: {query}")

    # Execute the search
    result = tavily.search(
        query=query,
        search_date=search_date,
        # topic="news",
        max_results=args.max_results,
    )

    # Save results to file
    with open(args.output, "w") as f:
        json.dump(result.model_dump(), f, indent=2, default=str)

    logger.info(f"Search results saved to {args.output}")

    # Print a summary
    print(f"\nSearch Query: {query}")
    print(f"Results found: {len(result.results)}")
    print("\nTop results:")

    # print(json.dumps(result.results[1], indent=2))

    for i, item in enumerate(result.results, 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   URL: {item.get('url', 'No URL')}")
        content = item.get("content")
        if content:
            print(f"   Content: {content[:400]}...")


if __name__ == "__main__":
    main()
