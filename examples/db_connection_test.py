"""Example script for testing the database connection."""

import logging
import os
import sys
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db import MongoDB, MongoDBDaemon

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_db_connection():
    """Test the database connection."""
    logger.info("Testing database connection...")

    # Check if MongoDB is running
    is_running, _ = MongoDBDaemon.check_status()
    if not is_running:
        logger.error("MongoDB is not running.")
        logger.error("Please start MongoDB using 'python -m src.db_manager --start'")
        return False

    # Initialize MongoDB connection
    db = MongoDB()

    if db.client is None:
        logger.error("Failed to connect to MongoDB.")
        logger.error(
            "Make sure MongoDB is running using 'python -m src.db_manager --start'"
        )
        return False

    # Get database statistics
    try:
        # Get database stats
        stats = db.get_database_stats()
        logger.info(f"Connected to database: {stats['database']}")
        logger.info(f"Collections: {stats['collections']}")

        for collection, count in stats.get("collection_stats", {}).items():
            logger.info(f"  - {collection}: {count} documents")

        # Test search results collection
        search_results_count = db.search_results.count_documents({})
        logger.info(f"Search results: {search_results_count}")

        # Test events collection
        events_count = db.events.count_documents({})
        logger.info(f"Events: {events_count}")

        # Get events for a specific date
        test_date = datetime(2023, 1, 1)
        events = db.get_events_by_date(test_date)
        logger.info(f"Events for {test_date.strftime('%Y-%m-%d')}: {len(events)}")

        # Test database indexes
        indexes = db.search_results.index_information()
        logger.info(f"Search results indexes: {len(indexes)}")
        for index_name, index_info in indexes.items():
            logger.info(f"  - {index_name}: {index_info}")

        indexes = db.events.index_information()
        logger.info(f"Events indexes: {len(indexes)}")
        for index_name, index_info in indexes.items():
            logger.info(f"  - {index_name}: {index_info}")

        logger.info("Database connection test completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error testing database: {e}")
        return False


if __name__ == "__main__":
    success = test_db_connection()
    if not success:
        logger.error("Database connection test failed.")
        import sys

        sys.exit(1)
