"""Example script demonstrating how to use the MongoDB database in your code."""

import os
import sys
import logging
from datetime import datetime, timedelta
from pprint import pprint

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db import MongoDB, MongoDBDaemon
from src.models import SearchResult, Event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def demonstrate_db_usage():
    """Demonstrate how to use the MongoDB database in your code."""
    logger.info("=== MongoDB Usage Example ===")

    # Step 1: Check if MongoDB is running
    logger.info("Step 1: Checking if MongoDB is running...")
    is_running, _ = MongoDBDaemon.check_status()
    if not is_running:
        logger.error("MongoDB is not running.")
        logger.error("Please start MongoDB using 'python -m src.db_manager --start'")
        return False

    # Step 2: Connect to the database
    logger.info("Step 2: Connecting to the database...")
    db = MongoDB()
    if db.client is None:
        logger.error("Failed to connect to MongoDB.")
        return False

    # Step 3: Get database statistics
    logger.info("Step 3: Getting database statistics...")
    stats = db.get_database_stats()
    logger.info(f"Connected to database: {stats['database']}")
    logger.info(f"Collections: {stats['collections']}")
    for collection, count in stats.get("collection_stats", {}).items():
        logger.info(f"  - {collection}: {count} documents")

    # Step 4: Create a sample search result
    logger.info("Step 4: Creating a sample search result...")
    search_result = SearchResult(
        query="Example Bitcoin query",
        search_date=datetime.now(),
        provider="example",
        params={"max_results": 10, "full_month": False},
        results=[],
    )

    # Step 5: Save the search result to the database
    logger.info("Step 5: Saving the search result to the database...")
    search_result_id = db.save_search_result(search_result)
    logger.info(f"Saved search result with ID: {search_result_id}")

    # Step 6: Create a sample event
    logger.info("Step 6: Creating a sample event...")
    event = Event(
        event_date=datetime.now(),
        title="Example Bitcoin Event",
        description="This is an example Bitcoin event for demonstration purposes.",
        source_url="https://example.com",
        provider="example",
        search_result_id=search_result_id,
        relevance_score=95,
        relevance_reasoning="This is a highly relevant event.",
    )

    # Step 7: Save the event to the database
    logger.info("Step 7: Saving the event to the database...")
    event_id = db.save_event(event)
    logger.info(f"Saved event with ID: {event_id}")

    # Step 8: Retrieve the event from the database
    logger.info("Step 8: Retrieving the event from the database...")
    retrieved_event = db.get_event(event_id)
    if retrieved_event:
        logger.info("Retrieved event:")
        logger.info(f"  - Title: {retrieved_event.title}")
        logger.info(f"  - Date: {retrieved_event.event_date}")
        logger.info(f"  - Description: {retrieved_event.description}")
        logger.info(f"  - ID: {retrieved_event.id}")
    else:
        logger.error("Failed to retrieve event.")

    # Step 9: Update the event
    logger.info("Step 9: Updating the event...")
    if retrieved_event:
        retrieved_event.title = "Updated Example Bitcoin Event"
        retrieved_event.description = "This is an updated example Bitcoin event."
        retrieved_event.rank = 1
        if db.update_event(retrieved_event):
            logger.info("Event updated successfully.")
        else:
            logger.error("Failed to update event.")
    else:
        logger.error("Cannot update event: not retrieved.")

    # Step 10: Get events for today
    logger.info("Step 10: Getting events for today...")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    events = db.get_events_by_date(today)
    logger.info(f"Found {len(events)} events for today.")
    for i, event in enumerate(events):
        logger.info(f"Event {i+1}: {event.title}")

    logger.info("=== MongoDB Usage Example Completed ===")
    return True


if __name__ == "__main__":
    success = demonstrate_db_usage()
    if not success:
        logger.error("MongoDB usage example failed.")
        sys.exit(1)
