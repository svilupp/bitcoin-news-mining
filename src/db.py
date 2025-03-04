"""MongoDB database utility functions and management."""

import logging
import os
import subprocess
import atexit
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.models import Event, SearchResult

logger = logging.getLogger(__name__)


class MongoDBDaemon:
    """MongoDB daemon manager for starting and stopping a local MongoDB instance."""

    def __init__(
        self,
        data_path: str = "./db",
        log_path: str = "./logs/mongodb.log",
        port: int = 27017,
    ):
        """Initialize MongoDB daemon manager.

        Args:
            data_path: Path to the MongoDB data directory
            log_path: Path to the MongoDB log file
            port: Port number for the MongoDB instance
        """
        # Create directories if they don't exist
        os.makedirs(data_path, exist_ok=True)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        self.data_path = os.path.abspath(data_path)
        self.log_path = os.path.abspath(log_path)
        self.port = port
        self.process = None
        self.client = None

    def start(self) -> MongoClient:
        """Start a local MongoDB instance.

        Returns:
            MongoDB client connected to the running instance
        """
        try:
            # Check if MongoDB is already running on this port
            existing_client = MongoClient(
                f"mongodb://localhost:{self.port}", serverSelectionTimeoutMS=1000
            )
            existing_client.admin.command("ping")
            logger.info(f"MongoDB already running on port {self.port}")
            self.client = existing_client
            return self.client
        except Exception as e:
            # Start MongoDB with our custom path
            logger.info(f"Starting MongoDB with data path: {self.data_path}")
            self.process = subprocess.Popen(
                [
                    "mongod",
                    "--dbpath",
                    self.data_path,
                    "--logpath",
                    self.log_path,
                    "--port",
                    str(self.port),
                    "--bind_ip",
                    "127.0.0.1",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )

            # Register shutdown handler
            atexit.register(self.stop)

            # Wait for MongoDB to start up
            max_retries = 10
            for i in range(max_retries):
                try:
                    time.sleep(1)
                    self.client = MongoClient(
                        f"mongodb://localhost:{self.port}",
                        serverSelectionTimeoutMS=2000,
                    )
                    self.client.admin.command("ping")
                    logger.info("MongoDB started successfully")
                    return self.client
                except Exception as e:
                    if i == max_retries - 1:
                        logger.error(
                            f"Failed to start MongoDB after {max_retries} attempts: {e}"
                        )
                        self.stop()
                        raise
                    logger.info(
                        f"Waiting for MongoDB to start (attempt {i+1}/{max_retries})..."
                    )

    def stop(self) -> None:
        """Stop the MongoDB instance."""
        if self.process:
            logger.info("Shutting down MongoDB...")
            self.process.send_signal(signal.SIGTERM)
            self.process.wait()
            self.process = None
            logger.info("MongoDB stopped")

    def get_client(self) -> MongoClient:
        """Get a MongoDB client connection.

        Returns:
            MongoDB client
        """
        if not self.client:
            self.start()
        return self.client

    @staticmethod
    def check_status(port: int = 27017) -> Tuple[bool, Optional[MongoClient]]:
        """Check if MongoDB is running on the specified port.

        Args:
            port: Port number to check

        Returns:
            Tuple of (is_running, client)
        """
        try:
            client = MongoClient(
                f"mongodb://localhost:{port}", serverSelectionTimeoutMS=1000
            )
            client.admin.command("ping")
            return True, client
        except Exception:
            return False, None

    @staticmethod
    def find_and_stop_mongodb(port: int = 27017) -> bool:
        """Find and stop a running MongoDB instance.

        Args:
            port: Port number of the MongoDB instance

        Returns:
            True if MongoDB was stopped, False otherwise
        """
        is_running, _ = MongoDBDaemon.check_status(port)
        if not is_running:
            logger.info("MongoDB is not running.")
            return False

        logger.info("Stopping MongoDB...")

        # Find MongoDB process
        if os.name == "posix":  # Unix/Linux/Mac
            try:
                # Find mongod process
                ps_output = subprocess.check_output(["ps", "aux"]).decode()
                for line in ps_output.split("\n"):
                    if "mongod" in line and f"--port {port}" in line:
                        pid = int(line.split()[1])
                        os.kill(pid, signal.SIGTERM)
                        logger.info(
                            f"Sent termination signal to MongoDB process (PID: {pid})"
                        )
                        time.sleep(2)

                        # Check if it's still running
                        is_still_running, _ = MongoDBDaemon.check_status(port)
                        if not is_still_running:
                            logger.info("MongoDB stopped successfully.")
                            return True
                        else:
                            logger.warning(
                                "MongoDB is still running. You may need to stop it manually."
                            )
                            return False

                # Also check for python start_db.py process
                for line in ps_output.split("\n"):
                    if "python" in line and "start_db.py" in line:
                        pid = int(line.split()[1])
                        os.kill(pid, signal.SIGTERM)
                        logger.info(
                            f"Sent termination signal to start_db.py process (PID: {pid})"
                        )
                        time.sleep(2)

                        # Check if MongoDB is still running
                        is_still_running, _ = MongoDBDaemon.check_status(port)
                        if not is_still_running:
                            logger.info("MongoDB stopped successfully.")
                            return True
                        else:
                            logger.warning(
                                "MongoDB is still running. You may need to stop it manually."
                            )
                            return False

                logger.warning(
                    "Could not find MongoDB process. It may be running in a different way."
                )
                return False
            except Exception as e:
                logger.error(f"Error stopping MongoDB: {e}")
                return False
        else:  # Windows
            try:
                # On Windows, use taskkill
                subprocess.run(["taskkill", "/F", "/IM", "mongod.exe"], check=False)
                logger.info("Sent termination signal to MongoDB process")
                time.sleep(2)

                # Check if it's still running
                is_still_running, _ = MongoDBDaemon.check_status(port)
                if not is_still_running:
                    logger.info("MongoDB stopped successfully.")
                    return True
                else:
                    logger.warning(
                        "MongoDB is still running. You may need to stop it manually."
                    )
                    return False
            except Exception as e:
                logger.error(f"Error stopping MongoDB: {e}")
                return False


class MongoDB:
    """MongoDB database connection and operations."""

    def __init__(
        self,
        data_path: str = "./db",
        log_path: str = "./logs/mongodb.log",
        port: int = 27017,
        db_name: str = "bitcoin_news",
    ):
        """Initialize MongoDB connection.

        Args:
            data_path: Path to the MongoDB data directory
            log_path: Path to the MongoDB log file
            port: Port number for the MongoDB instance
            db_name: Database name
        """
        self.data_path = os.path.abspath(data_path)
        self.log_path = os.path.abspath(log_path)
        self.port = port
        self.db_name = db_name
        self.client = None
        self.db = None
        self.search_results = None
        self.events = None

        # Connect to the database
        if self.connect():
            # Collections
            self.search_results = self.db.search_results
            self.events = self.db.events

            # Create indexes
            self._create_indexes()

    def connect(self) -> bool:
        """Connect to the MongoDB database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to connect to MongoDB
            self.client = MongoClient(
                f"mongodb://localhost:{self.port}", serverSelectionTimeoutMS=2000
            )
            self.client.admin.command("ping")
            logger.info(f"Connected to MongoDB on port {self.port}")
            self.db = self.client[self.db_name]
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.error(
                "Make sure MongoDB is running using 'python -m src.db_manager --start'"
            )
            self.client = None
            self.db = None
            return False

    def get_client(self) -> Optional[MongoClient]:
        """Get a MongoDB client connection.

        Returns:
            MongoDB client or None if connection failed
        """
        if not self.client:
            self.connect()
        return self.client

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        if self.db is None:
            return {"error": "Not connected to database"}

        try:
            collections = self.db.list_collection_names()
            stats = {
                "database": self.db_name,
                "collections": len(collections),
                "collection_stats": {},
            }

            for collection in collections:
                try:
                    count = self.db[collection].count_documents({})
                    stats["collection_stats"][collection] = count
                except Exception as e:
                    stats["collection_stats"][collection] = f"Error: {str(e)}"

            return stats
        except Exception as e:
            return {"error": str(e)}

    def _create_indexes(self) -> None:
        """Create indexes for collections."""
        if self.search_results is None or self.events is None:
            logger.warning("Cannot create indexes: collections not initialized")
            return

        try:
            # Create indexes for search_results collection
            self.search_results.create_index("search_date")
            self.search_results.create_index("query")
            self.search_results.create_index("provider")
            self.search_results.create_index([("query", "text")])

            # Create indexes for events collection
            self.events.create_index("event_date")
            self.events.create_index("search_result_id")
            self.events.create_index("provider")
            self.events.create_index("rank")
            self.events.create_index("relevance_score")
            self.events.create_index([("title", "text"), ("description", "text")])

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    def save_search_result(self, search_result: SearchResult) -> str:
        """Save a search result to the database.

        Args:
            search_result: SearchResult object to save

        Returns:
            ID of the saved search result
        """
        # Convert to dict
        search_result_dict = search_result.model_dump()

        # Insert into database
        result = self.search_results.insert_one(search_result_dict)

        return str(result.inserted_id)

    def get_search_result(self, search_result_id: str) -> Optional[SearchResult]:
        """Get a search result from the database.

        Args:
            search_result_id: ID of the search result to get

        Returns:
            SearchResult object or None if not found
        """
        from bson.objectid import ObjectId

        # Get from database
        result = self.search_results.find_one({"_id": ObjectId(search_result_id)})

        if result:
            # Convert to SearchResult object
            search_result = SearchResult.model_validate(result)
            # Set the ID
            search_result.id = str(result["_id"])
            return search_result

        return None

    def get_search_results_by_query_and_date(
        self, query: str, date: datetime
    ) -> List[SearchResult]:
        """Get search results by query and date.

        Args:
            query: Query to search for
            date: Date to search for

        Returns:
            List of SearchResult objects
        """
        # Get from database
        start_date = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_date = datetime(date.year, date.month, date.day, 23, 59, 59)

        results = self.search_results.find(
            {
                "query": {"$regex": query, "$options": "i"},
                "search_date": {"$gte": start_date, "$lte": end_date},
            }
        )

        # Convert to SearchResult objects
        search_results = []
        for result in results:
            search_result = SearchResult.model_validate(result)
            search_result.id = str(result["_id"])
            search_results.append(search_result)

        return search_results

    def save_event(self, event: Event) -> str:
        """Save an event to the database.

        Args:
            event: Event object to save

        Returns:
            ID of the saved event
        """
        # Convert to dict
        event_dict = event.model_dump()

        # Insert into database
        result = self.events.insert_one(event_dict)

        return str(result.inserted_id)

    def update_event(self, event: Event) -> bool:
        """Update an event in the database.

        Args:
            event: Event object to update

        Returns:
            True if update was successful, False otherwise
        """
        from bson.objectid import ObjectId

        if not event.id:
            logger.error("Cannot update event without ID")
            return False

        # Convert to dict
        event_dict = event.model_dump()

        # Remove ID from dict
        event_id = event_dict.pop("id")

        # Update in database
        result = self.events.update_one(
            {"_id": ObjectId(event_id)}, {"$set": event_dict}
        )

        return result.modified_count > 0

    def get_event(self, event_id: str) -> Optional[Event]:
        """Get an event from the database.

        Args:
            event_id: ID of the event to get

        Returns:
            Event object or None if not found
        """
        from bson.objectid import ObjectId

        # Get from database
        result = self.events.find_one({"_id": ObjectId(event_id)})

        if result:
            # Convert to Event object
            event = Event.model_validate(result)
            # Set the ID
            event.id = str(result["_id"])
            return event

        return None

    def get_events_by_date(
        self, date: datetime, sorted_by_rank: bool = True
    ) -> List[Event]:
        """Get events by date.

        Args:
            date: Date to get events for
            sorted_by_rank: Whether to sort events by rank

        Returns:
            List of Event objects
        """
        # Get from database
        start_date = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_date = datetime(date.year, date.month, date.day, 23, 59, 59)

        query = {"event_date": {"$gte": start_date, "$lte": end_date}}

        if sorted_by_rank:
            results = self.events.find(query).sort("rank", 1)
        else:
            results = self.events.find(query)

        # Convert to Event objects
        events = []
        for result in results:
            event = Event.model_validate(result)
            event.id = str(result["_id"])
            events.append(event)

        return events


def run_mongodb_daemon() -> None:
    """Run MongoDB as a daemon process."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, mongo))
    signal.signal(signal.SIGTERM, lambda sig, frame: signal_handler(sig, frame, mongo))

    logger.info("=== MongoDB Daemon Manager ===")
    logger.info("Starting MongoDB server. Press Ctrl+C to stop.")

    # Initialize and start MongoDB
    mongo = MongoDBDaemon()
    client = mongo.start()

    # Check if MongoDB is running and connected
    try:
        # Send a ping to confirm connection
        client.admin.command("ping")
        logger.info("Successfully connected to MongoDB")

        # Print connection information
        db_name = "bitcoin_news"
        logger.info(f"MongoDB is running on port {mongo.port}")
        logger.info(f"Connection string: mongodb://localhost:{mongo.port}")
        logger.info(f"Data path: {mongo.data_path}")
        logger.info(f"Log path: {mongo.log_path}")
        logger.info(f"Default database: {db_name}")

        # Keep the process running until interrupted
        logger.info("\nMongoDB is now running in the background.")
        logger.info("This window will keep the database alive.")
        logger.info("Press Ctrl+C to stop the database and exit.")

        # Keep the script running
        while True:
            time.sleep(1)

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        mongo.stop()
        sys.exit(1)


def signal_handler(sig: int, frame, mongo: Optional[MongoDBDaemon] = None) -> None:
    """Handle Ctrl+C and other termination signals.

    Args:
        sig: Signal number
        frame: Current stack frame
        mongo: MongoDB daemon instance
    """
    logger.info("\nReceived termination signal. Shutting down MongoDB...")
    if mongo and hasattr(mongo, "stop"):
        mongo.stop()
    sys.exit(0)


if __name__ == "__main__":
    run_mongodb_daemon()
