# db.py
from pymongo import MongoClient
import os
import subprocess
import atexit
import time
import signal


class LocalMongoDB:
    def __init__(self, data_path="./db", log_path="./logs/mongodb.log", port=27017):
        # Create directories if they don't exist
        os.makedirs(data_path, exist_ok=True)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        self.data_path = os.path.abspath(data_path)
        self.log_path = os.path.abspath(log_path)
        self.port = port
        self.process = None
        self.client = None

    def start(self):
        """Start a local MongoDB instance"""
        try:
            # Check if MongoDB is already running on this port
            existing_client = MongoClient(
                f"mongodb://localhost:{self.port}", serverSelectionTimeoutMS=1000
            )
            existing_client.admin.command("ping")
            print(f"MongoDB already running on port {self.port}")
        except:
            # Start MongoDB with our custom path
            print(f"Starting MongoDB with data path: {self.data_path}")
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
            time.sleep(2)
            print("MongoDB started successfully")

        # Connect to the database
        self.client = MongoClient(f"mongodb://localhost:{self.port}")
        return self.client

    def stop(self):
        """Stop the MongoDB instance"""
        if self.process:
            print("Shutting down MongoDB...")
            self.process.send_signal(signal.SIGTERM)
            self.process.wait()
            self.process = None
            print("MongoDB stopped")

    def get_client(self):
        """Get a MongoDB client connection"""
        if not self.client:
            self.start()
        return self.client


# Usage example
if __name__ == "__main__":
    mongo = LocalMongoDB()
    client = mongo.start()

    # Check if MongoDB is running and connected
    try:
        # Send a ping to confirm connection
        client.admin.command("ping")
        print("Successfully connected to MongoDB")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise

    # Get database
    # db = client.ResearchAssistant

    # Example operations
    # db.events.insert_one({"title": "Test Event", "date": datetime.datetime.now()})

    # print(f"Event count: {db.events.count_documents({})}")

    # MongoDB will be automatically stopped when the program exits
