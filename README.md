# Bitcoin News Mining with Structured LLM Outputs

This project uses Large Language Models (LLMs) to process, rank, and filter Bitcoin and cryptocurrency news, linking them to Bitcoin price movements.

## Main Components

The project has been updated in several key areas:

1. **Event Ranker**: `src/llm/ranker.py` - Ranks cryptocurrency events by importance asynchronously
2. **Event Processor**: `src/llm/processor.py` - Cleans and formats event data asynchronously
3. **Event Judge**: `src/llm/judge.py` - Evaluates if search results are relevant asynchronously
4. **Database Manager**: `src/db.py` and `src/db_manager.py` - Manages MongoDB database operations

All components now use async methods and structured output patterns.

## Requirements

- Python 3.12+
- MongoDB instance (local or cloud)
- API keys for:
  - OpenAI (or alternative provider)
  - Tavily
  - Exa
  - Google Generative AI (optional, if using Gemini models)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bitcoin-news-mining.git
cd bitcoin-news-mining
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up environment variables:
```bash
export EXA_API_KEY="your-exa-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

## Database Management

The project uses MongoDB for storing search results and events. The database management system has been redesigned to be more robust and user-friendly.

### Starting MongoDB

You can start MongoDB as a daemon process using either of these commands:

```bash
# Using the module directly (recommended)
python -m src.db_manager --start

# Or using the compatibility wrapper
python db_manager.py --start
```

This will:
1. Check if MongoDB is already running
2. Start MongoDB as a background process if it's not running
3. Create necessary data and log directories if they don't exist
4. Wait for MongoDB to start and verify the connection

### Checking MongoDB Status

To check if MongoDB is running and view database statistics:

```bash
# Using the module directly (recommended)
python -m src.db_manager --status

# Or using the compatibility wrapper
python db_manager.py --status
```

This will show:
- Whether MongoDB is running
- The database name
- Number of collections
- Document count for each collection

### Stopping MongoDB

When you're done, you can stop MongoDB using:

```bash
# Using the module directly (recommended)
python -m src.db_manager --stop

# Or using the compatibility wrapper
python db_manager.py --stop
```

This will:
1. Find the MongoDB process
2. Send a termination signal
3. Verify that MongoDB has stopped

### Testing the Database Connection

You can test the database connection using the provided example script:

```bash
python examples/db_connection_test.py
```

This script will:
1. Check if MongoDB is running
2. Connect to the database
3. Display database statistics
4. Test specific collections
5. Show information about database indexes

### Using the Database in Your Code

You can use the database in your own code by importing the `MongoDB` class:

```python
from src.db import MongoDB

# Initialize the database connection
db = MongoDB()

# Get database statistics
stats = db.get_database_stats()
print(f"Connected to database: {stats['database']}")
print(f"Collections: {stats['collections']}")

# Get events for a specific date
from datetime import datetime
date = datetime(2023, 1, 1)
events = db.get_events_by_date(date)
print(f"Found {len(events)} events for {date.strftime('%Y-%m-%d')}")
```

For a complete example of how to use the database in your code, see the `examples/db_usage_example.py` script:

```bash
# Start MongoDB if it's not already running
python -m src.db_manager --start

# Run the example script
python examples/db_usage_example.py
```

This script demonstrates:
1. Checking if MongoDB is running
2. Connecting to the database
3. Getting database statistics
4. Creating and saving search results and events
5. Retrieving and updating events
6. Querying events by date

## Project Structure

The project is organized as follows:

- `src/`: Source code directory
  - `db.py`: Database interface and daemon management for MongoDB
  - `db_manager.py`: Command-line interface for database management
  - `models.py`: Data models for the application
  - `llm/`: LLM-related components
    - `judge.py`: Evaluates if search results are relevant
    - `processor.py`: Cleans and formats event data
    - `ranker.py`: Ranks cryptocurrency events by importance
  - `search/`: Search-related components
    - `exa.py`: Interface for Exa search API
    - `tavily.py`: Interface for Tavily search API
  - `pipeline/`: Pipeline components
    - `crypto_event_pipeline.py`: Main pipeline for finding and storing crypto events
    - `ranking_pipeline.py`: Pipeline for ranking stored events
    - `utils.py`: Utility functions for the pipeline

- `main.py`: Command-line interface for running the sourcing pipeline
- `rank_events.py`: Command-line interface for running the ranking pipeline
- `app.py`: Interactive application for query discovery
- `db_manager.py`: Compatibility wrapper for database management
- `db/`: MongoDB data directory
- `logs/`: Log files directory
- `data_raw/`: Raw data directory
- `data_processed/`: Processed data directory
- `examples/`: Example scripts
  - `db_connection_test.py`: Test database connection
  - `single_date.py`: Process a single date
  - `batch_processing.py`: Process multiple dates
  - `query_comparison.py`: Compare different queries
  - `ranking_example.py`: Rank events
  - `db_usage_example.py`: Demonstrate database usage in code

## Usage

### Sourcing Pipeline

You can run the sourcing pipeline from the command line using `main.py`:

```bash
# Process a specific date
python main.py --date 2023-01-01

# Process a date range
python main.py --start-date 2023-01-01 --end-date 2023-01-07

# Customize the search query
python main.py --date 2023-01-01 --query "Bitcoin price movements and market trends"

# Search for a full month
python main.py --date 2023-01-01 --full-month
```

### Ranking Pipeline

You can run the ranking pipeline from the command line using `rank_events.py`:

```bash
# Rank events for a specific date
python rank_events.py --date 2023-01-01

# Rank events for a date range
python rank_events.py --start-date 2023-01-01 --end-date 2023-01-07

# Filter events by query
python rank_events.py --date 2023-01-01 --query "Bitcoin price movements"

# Compare multiple queries
python rank_events.py --date 2023-01-01 --queries "Bitcoin price,Bitcoin adoption,Bitcoin regulation"

# Set minimum relevance score
python rank_events.py --date 2023-01-01 --min-score 0.8
```

### Interactive Query Discovery

You can use the interactive application for query discovery:

```bash
python app.py
```

This will start an interactive session where you can:
1. Run different queries for a specific date
2. Compare results from different queries
3. Save and load query results
4. Change the date to search for

### Using the Pipelines in Your Code

You can also use the pipelines in your own code:

```python
import asyncio
from datetime import datetime
from src.pipeline import CryptoEventPipeline, CryptoEventRankingPipeline

async def example():
    # Initialize the sourcing pipeline
    sourcing_pipeline = CryptoEventPipeline(
        exa_api_key="your-exa-api-key",
        openai_api_key="your-openai-api-key",
    )
    
    # Process a specific date
    date = datetime(2023, 1, 1)
    search_result, events = await sourcing_pipeline.process_date(date)
    
    # Print results
    print(f"Found {len(events)} events for {date.strftime('%Y-%m-%d')}")
    
    # Initialize the ranking pipeline
    ranking_pipeline = CryptoEventRankingPipeline(
        openai_api_key="your-openai-api-key",
    )
    
    # Rank events for the same date
    ranked_events = await ranking_pipeline.rank_events_for_date(date)
    
    # Print ranked events
    print(f"Ranked {len(ranked_events)} events")
    for i, event in enumerate(ranked_events[:5]):
        print(f"Event {i+1}: {event.title} (Rank: {event.rank})")

if __name__ == "__main__":
    asyncio.run(example())

## Overview

This project helps identify and rank the most significant events in Bitcoin and cryptocurrency history by:

1. Searching for relevant events using multiple search APIs (Tavily and Exa)
2. Evaluating search results with a Gemini LLM to determine relevance
3. Formatting and cleaning event information for consistency
4. Ranking events by historical significance
5. Storing everything in MongoDB for easy access and analysis

## Data Flow

1. Search APIs retrieve potential events
2. LLM judge evaluates relevance of search results
3. Relevant results become events
4. Events are processed to clean titles and descriptions
5. Events are ranked by historical significance
6. Everything is stored in MongoDB for analysis

## MongoDB Collections

The project uses two MongoDB collections:

1. `search_results` - Raw search results with metadata
2. `events` - Processed and ranked events

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
