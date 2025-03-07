# Bitcoin News Mining with Structured LLM Outputs

This project uses Large Language Models (LLMs) to process, rank, and filter Bitcoin and cryptocurrency news, linking them to Bitcoin price movements.
Built for a friend to help him label his art.

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
uv sync
```

3. Set up environment variables:

You can set environment variables directly:
```bash
export EXA_API_KEY="your-exa-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

Or create a `.env` file in the project root directory:
```
EXA_API_KEY=your-exa-api-key
OPENAI_API_KEY=your-openai-api-key
```

## Database Management

The project uses MongoDB for storing search results and events. The database management system has been redesigned to be more robust and user-friendly.

### Starting MongoDB

You can start MongoDB as a daemon process using either of these commands:

```bash
# Using the module directly (recommended)
python -m src.db_manager --start
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
```

This will:
1. Find the MongoDB process
2. Send a termination signal
3. Verify that MongoDB has stopped

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
uv run app.py
```

This will start a web server and you can access the application by opening a browser and navigating to `http://localhost:8000` (or the URL shown in the terminal).

The interactive application allows you to:
1. Enter a search query for Bitcoin and cryptocurrency news
2. Specify a date in YYYY-MM-DD format
3. Optionally provide your own API keys (or use the ones from environment variables)
4. View search results and ranked events side by side

#### Setting up a .env file for the interactive application

For convenience, you can create a `.env` file in the project root directory with your API keys:

```
# API Keys
EXA_API_KEY=your-exa-api-key
OPENAI_API_KEY=your-openai-api-key
```

The application will automatically load these environment variables when it starts.

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
