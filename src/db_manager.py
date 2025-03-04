#!/usr/bin/env python

"""MongoDB database manager for Bitcoin News Mining.

This script provides commands to start, stop, and check the status of the MongoDB server.
It uses the MongoDB functionality from src.db module.
"""

import os
import sys
import argparse
import logging
from pymongo import MongoClient

from src.db import MongoDBDaemon, MongoDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_DB_PATH = "./db"
DEFAULT_LOG_PATH = "./logs/mongodb.log"
DEFAULT_PORT = 27017
DEFAULT_DB_NAME = "bitcoin_news"


def check_mongodb_status(port=DEFAULT_PORT):
    """Check if MongoDB is running on the specified port.

    Args:
        port: Port number to check

    Returns:
        True if MongoDB is running, False otherwise
    """
    is_running, client = MongoDBDaemon.check_status(port)

    if is_running:
        logger.info(f"MongoDB is running on port {port}")

        # Get database statistics
        try:
            db = MongoDB(port=port)
            stats = db.get_database_stats()

            if "error" in stats:
                logger.error(f"Error getting database statistics: {stats['error']}")
            else:
                logger.info(f"Database: {stats['database']}")
                logger.info(f"Collections: {stats['collections']}")

                for collection, count in stats.get("collection_stats", {}).items():
                    logger.info(f"  - {collection}: {count} documents")

        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
    else:
        logger.info(f"MongoDB is not running on port {port}")

    return is_running


def start_mongodb_daemon():
    """Start MongoDB as a daemon process.

    Returns:
        True if MongoDB was started successfully, False otherwise
    """
    # Check if MongoDB is already running
    is_running, _ = MongoDBDaemon.check_status(DEFAULT_PORT)
    if is_running:
        logger.info(f"MongoDB is already running on port {DEFAULT_PORT}")
        return True

    # Import the run_mongodb_daemon function from src.db
    from src.db import run_mongodb_daemon

    # Start MongoDB in a new process
    import subprocess
    import sys

    cmd = [sys.executable, "-m", "src.db"]

    if os.name == "posix":  # Unix/Linux/Mac
        # Use nohup to keep the process running after the terminal is closed
        cmd = ["nohup"] + cmd + ["&"]

        try:
            # Start the process
            logger.info("Starting MongoDB daemon...")
            subprocess.Popen(
                " ".join(cmd),
                shell=True,
                stdout=open(os.devnull, "w"),
                stderr=open(os.devnull, "w"),
                start_new_session=True,
            )

            # Wait for MongoDB to start
            import time

            for i in range(10):
                time.sleep(1)
                is_running, _ = MongoDBDaemon.check_status(DEFAULT_PORT)
                if is_running:
                    logger.info("MongoDB daemon started successfully")
                    return True
                logger.info(f"Waiting for MongoDB to start (attempt {i+1}/10)...")

            logger.error("Failed to start MongoDB daemon after 10 attempts")
            return False

        except Exception as e:
            logger.error(f"Error starting MongoDB daemon: {e}")
            return False
    else:  # Windows
        # On Windows, use pythonw.exe to run without a console window
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw):
            cmd[0] = pythonw

        try:
            # Start the process
            logger.info("Starting MongoDB daemon...")
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait for MongoDB to start
            import time

            for i in range(10):
                time.sleep(1)
                is_running, _ = MongoDBDaemon.check_status(DEFAULT_PORT)
                if is_running:
                    logger.info("MongoDB daemon started successfully")
                    return True
                logger.info(f"Waiting for MongoDB to start (attempt {i+1}/10)...")

            logger.error("Failed to start MongoDB daemon after 10 attempts")
            return False

        except Exception as e:
            logger.error(f"Error starting MongoDB daemon: {e}")
            return False


def stop_mongodb():
    """Stop MongoDB.

    Returns:
        True if MongoDB was stopped successfully, False otherwise
    """
    return MongoDBDaemon.find_and_stop_mongodb(DEFAULT_PORT)


def show_status():
    """Show MongoDB status."""
    check_mongodb_status(DEFAULT_PORT)


def parse_arguments():
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="MongoDB database manager for Bitcoin News Mining"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--start", action="store_true", help="Start MongoDB as a daemon process"
    )
    group.add_argument("--stop", action="store_true", help="Stop MongoDB")
    group.add_argument("--status", action="store_true", help="Check MongoDB status")

    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()

    if args.start:
        if start_mongodb_daemon():
            sys.exit(0)
        else:
            sys.exit(1)
    elif args.stop:
        if stop_mongodb():
            sys.exit(0)
        else:
            sys.exit(1)
    elif args.status:
        if check_mongodb_status():
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
