# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev
```

### MongoDB Management
```bash
# Start MongoDB daemon
python -m src.db_manager --start

# Check MongoDB status
python -m src.db_manager --status

# Stop MongoDB daemon
python -m src.db_manager --stop
```

### Running the Pipeline
```bash
# Source events for a specific date
python main.py --date 2023-01-01

# Source events for a date range
python main.py --start-date 2023-01-01 --end-date 2023-01-07

# Rank events for a specific date
python ranking_events.py --date 2023-01-01

# Rank events for date range
python ranking_events.py --start-date 2023-01-01 --end-date 2023-01-07
```

### Web Application
```bash
# Start interactive web application
uv run app.py
```

### Testing
```bash
# Run tests (using pytest from dev dependencies)
uv run pytest tests/
```

## Architecture Overview

This is a Bitcoin/cryptocurrency news mining system that uses LLMs to process, rank, and filter news events. The system follows a pipeline architecture with three main stages:

### Core Pipeline Flow
1. **Search Stage**: Uses Exa search API to find cryptocurrency news for specific dates
2. **Judge Stage**: LLM evaluates search results for relevance and extracts structured events  
3. **Ranking Stage**: LLM ranks events by historical significance

### Key Components

#### Pipeline Classes (`src/pipeline/`)
- `CryptoEventPipeline`: Main sourcing pipeline that searches and processes events
- `CryptoEventRankingPipeline`: Ranking pipeline that evaluates stored events
- Both pipelines are async and use structured LLM outputs via Pydantic models

#### LLM Components (`src/llm/`)
- `EventJudge`: Evaluates search results and extracts structured events
- `EventProcessor`: Cleans and formats event data  
- `EventRanker`: Ranks events by historical significance
- All use OpenAI API with structured output patterns

#### Data Layer (`src/db.py`, `src/models.py`)
- `MongoDB`: Database interface with connection management
- `MongoDBDaemon`: Local MongoDB instance management
- `SearchResult`: Model for raw search data
- `Event`: Model for processed cryptocurrency events

#### Search Integration (`src/search/`)
- `ExaSearch`: Interface for Exa search API
- `TavilySearch`: Interface for Tavily search API (legacy)

### Application Entry Points

#### Command Line Scripts
- `main.py`: Batch processing script for sourcing events across date ranges
- `ranking_events.py`: Batch ranking script with filtering options
- Both support date ranges, custom queries, and progress tracking

#### Web Application (`app.py`)
- FastHTML-based interactive application for query discovery
- Real-time search and ranking with configurable models and prompts
- Supports custom API keys and judge prompts via UI

## Environment Variables

Required API keys:
- `EXA_API_KEY`: For search functionality
- `OPENAI_API_KEY`: For LLM processing
- `GOOGLE_API_KEY`: Optional, for Gemini models

## MongoDB Collections

- `search_results`: Raw search results with metadata
- `events`: Processed and ranked events with relevance scores

## Development Notes

- All LLM operations are async using `AsyncOpenAI`
- Database operations use connection pooling and proper error handling
- MongoDB daemon is managed automatically with proper cleanup
- Models use Pydantic for validation and structured outputs
- Date handling supports both string and datetime formats
- Progress tracking uses `tqdm` for long-running operations

## API Integration

The system integrates with:
- **Exa Search API**: Primary search provider for cryptocurrency news
- **OpenAI API**: LLM processing for judging and ranking
- **Google Generative AI**: Alternative LLM provider (Gemini models)

All API clients support async operations and proper error handling.