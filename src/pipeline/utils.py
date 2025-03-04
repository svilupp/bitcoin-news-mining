"""Utility functions for the crypto event pipeline."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.models import Event, SearchResult

logger = logging.getLogger(__name__)


def format_date_for_display(date: datetime) -> str:
    """Format a date for display.

    Args:
        date: The date to format

    Returns:
        Formatted date string
    """
    return date.strftime("%Y-%m-%d")


def parse_date_string(
    date_str: str, format_str: str = "%Y-%m-%d"
) -> Optional[datetime]:
    """Parse a date string into a datetime object.

    Args:
        date_str: The date string to parse
        format_str: The format string to use for parsing

    Returns:
        Parsed datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        logger.error(f"Invalid date format: {date_str}, expected {format_str}")
        return None


def generate_date_range(start_date: datetime, end_date: datetime) -> List[datetime]:
    """Generate a list of dates between start_date and end_date, inclusive.

    Args:
        start_date: The start date
        end_date: The end date

    Returns:
        List of datetime objects
    """
    date_range = []
    current_date = start_date

    while current_date <= end_date:
        date_range.append(current_date)
        current_date = current_date + timedelta(days=1)

    return date_range


def summarize_events(events: List[Event]) -> Dict[str, Any]:
    """Summarize a list of events.

    Args:
        events: List of events to summarize

    Returns:
        Dictionary with summary information
    """
    if not events:
        return {
            "count": 0,
            "date_range": None,
            "top_events": [],
        }

    # Sort events by rank
    sorted_events = sorted(
        events, key=lambda e: e.rank if e.rank is not None else float("inf")
    )

    # Get date range
    dates = [event.event_date for event in events]
    min_date = min(dates)
    max_date = max(dates)

    # Get top 5 events
    top_events = sorted_events[:5]

    return {
        "count": len(events),
        "date_range": {
            "start": format_date_for_display(min_date),
            "end": format_date_for_display(max_date),
        },
        "top_events": [
            {
                "title": event.title,
                "date": format_date_for_display(event.event_date),
                "rank": event.rank,
                "score": event.relevance_score,
            }
            for event in top_events
        ],
    }


def summarize_search_results(search_result: SearchResult) -> Dict[str, Any]:
    """Summarize a search result.

    Args:
        search_result: The search result to summarize

    Returns:
        Dictionary with summary information
    """
    return {
        "query": search_result.query,
        "date": format_date_for_display(search_result.search_date),
        "result_count": len(search_result.results),
        "top_results": [
            {
                "title": result.title,
                "url": result.url,
                "published_date": (
                    format_date_for_display(result.published_date)
                    if result.published_date
                    else None
                ),
            }
            for result in search_result.results[:5]
        ],
    }
