"""MongoDB database utility functions."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.models import Event, SearchResult

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB database connection and operations."""

    def __init__(self, connection_string: str, db_name: str = "bitcoin_news"):
        """Initialize MongoDB connection.

        Args:
            connection_string: MongoDB connection string
            db_name: Database name
        """
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]

        # Collections
        self.search_results: Collection = self.db.search_results
        self.events: Collection = self.db.events

        # Create indexes
        self._create_indexes()

    def _create_indexes(self):
        """Create necessary indexes for collections."""
        # Search results indexes
        self.search_results.create_index("provider")
        self.search_results.create_index("search_date")
        self.search_results.create_index([("query", "text")])

        # Events indexes
        self.events.create_index("event_date")
        self.events.create_index("provider")
        self.events.create_index("search_result_id")
        self.events.create_index([("title", "text"), ("description", "text")])

    def save_search_result(self, search_result: SearchResult) -> str:
        """Save search result to database.

        Args:
            search_result: SearchResult object

        Returns:
            str: ID of the inserted document
        """
        data = search_result.dict_for_db()
        result = self.search_results.insert_one(data)
        return str(result.inserted_id)

    def get_search_result(self, search_result_id: str) -> Optional[Dict[str, Any]]:
        """Get search result by ID.

        Args:
            search_result_id: Search result ID

        Returns:
            Dict: Search result document or None if not found
        """
        from bson.objectid import ObjectId

        result = self.search_results.find_one({"_id": ObjectId(search_result_id)})
        return result

    def save_event(self, event: Event) -> str:
        """Save event to database.

        Args:
            event: Event object

        Returns:
            str: ID of the inserted document
        """
        data = event.dict_for_db()
        result = self.events.insert_one(data)
        return str(result.inserted_id)

    def update_event(self, event_id: str, update_data: Dict[str, Any]) -> bool:
        """Update event by ID.

        Args:
            event_id: Event ID
            update_data: Data to update

        Returns:
            bool: True if update was successful
        """
        from bson.objectid import ObjectId

        result = self.events.update_one(
            {"_id": ObjectId(event_id)}, {"$set": update_data}
        )
        return result.modified_count > 0

    def get_events_by_date(
        self, date, sorted_by_rank: bool = True
    ) -> List[Dict[str, Any]]:
        """Get events for a specific date.

        Args:
            date: Datetime object or string in ISO format
            sorted_by_rank: Whether to sort events by rank

        Returns:
            List[Dict]: List of event documents
        """
        query = {"event_date": {"$gte": date, "$lt": date + timedelta(days=1)}}

        sort_options = [("rank", 1)] if sorted_by_rank else [("relevance_score", -1)]

        events = list(self.events.find(query).sort(sort_options))
        return events
