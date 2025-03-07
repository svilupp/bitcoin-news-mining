#!/usr/bin/env python
"""Script to experiment with Exa search API for Bitcoin news."""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import SearchResult
from src.search.exa import ExaSearch

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run Exa search experiment."""
    parser = argparse.ArgumentParser(
        description="Search for Bitcoin news using Exa API"
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
        default="bitcoin cryptocurrency news and developments",
        # default="The most significant world events for Bitcoin and other cryptocurrencies on",
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
        default="data_raw/exa_results.json",
        help="Output file for search results (default: exa_results.json)",
    )

    args = parser.parse_args()

    # Get Exa API key from environment variable
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        logger.error("EXA_API_KEY environment variable not set")
        sys.exit(1)

    # Parse the date
    try:
        search_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD format.")
        sys.exit(1)

    # Initialize search client
    exa = ExaSearch(api_key=api_key)

    # Format the query
    query = exa.format_crypto_query(args.topic, search_date)
    logger.info(f"Searching Exa with query: {query}")

    # Execute the search
    result = exa.search(
        query=query,
        search_date=search_date,
        max_results=args.max_results,
        category="news",
        type="auto",
        start_published_date=datetime.strftime(search_date, "%Y-%m-%d"),
        end_published_date=datetime.strftime(
            search_date + timedelta(days=7), "%Y-%m-%d"
        ),
    )

    # Save results to file
    with open(args.output, "w") as f:
        json.dump(result.model_dump(), f, indent=2, default=str)

    logger.info(f"Search results saved to {args.output}")

    # Print a summary
    print(f"\nSearch Query: {query}")
    print(f"Results found: {len(result.results)}")
    print("\nTop results:")

    for i, item in enumerate(result.results, 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   URL: {item.get('url', 'No URL')}")
        content = item.get("content", "No content")
        print(f"   Content: {content[:300]}...")


if __name__ == "__main__":
    main()
