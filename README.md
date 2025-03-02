# Bitcoin News Mining with Structured LLM Outputs

This project uses Large Language Models (LLMs) to process, rank, and filter Bitcoin and cryptocurrency news, linking them to Bitcoin price movements.

## Main Components

The project has been updated in several key areas:

1. **Event Ranker**: `src/llm/ranker.py` - Ranks cryptocurrency events by importance asynchronously
2. **Event Processor**: `src/llm/processor.py` - Cleans and formats event data asynchronously
3. **Event Judge**: `src/llm/judge.py` - Evaluates if search results are relevant asynchronously

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

2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export GOOGLE_API_KEY="your-google-api-key"  # If using Gemini models
export TAVILY_API_KEY="your-tavily-api-key"
export EXA_API_KEY="your-exa-api-key"
export MONGODB_URI="your-mongodb-connection-string"
```

## Usage

The project provides several scripts to perform different steps of the data collection and analysis process.

### Running the Structured Output Example

Try the example code to see structured outputs in action:

```bash
# Set your API keys
export OPENAI_API_KEY="your_openai_api_key"
export GOOGLE_API_KEY="your_google_api_key"

# Run the example
python examples/structured_output_example.py
```

### Evaluating Search Results

The evaluate_results.py script now supports parallel processing and multiple providers:

```bash
# Process using OpenAI (default)
python scripts/evaluate_results.py --input search_results.json --output evaluated_results.json --threshold 0.7

# Process using Google Gemini
python scripts/evaluate_results.py --input search_results.json --provider google --parallel 10

# Process using a specific model
python scripts/evaluate_results.py --input search_results.json --provider openai --model gpt-4o
```

### Testing

Run the unit tests to verify the async functionality:

```bash
python -m unittest tests/test_async_llm.py
```

## Overview

This project helps identify and rank the most significant events in Bitcoin and cryptocurrency history by:

1. Searching for relevant events using multiple search APIs (Tavily and Exa)
2. Evaluating search results with a Gemini LLM to determine relevance
3. Formatting and cleaning event information for consistency
4. Ranking events by historical significance
5. Storing everything in MongoDB for easy access and analysis

## Project Structure

```
bitcoin-news-mining/
├── data_processed/     # Processed data files
├── data_raw/           # Raw data files
├── scripts/            # Command-line scripts
│   ├── exa_search.py           # Exa search script
│   ├── tavily_search.py        # Tavily search script
│   ├── evaluate_results.py     # Result evaluation script
│   ├── process_events.py       # Event processing script
│   ├── rank_events.py          # Event ranking script
│   └── save_to_mongodb.py      # MongoDB saving script
├── src/                # Source code
│   ├── db.py                   # MongoDB database utilities
│   ├── models.py               # Data models
│   ├── search/                 # Search API utilities
│   │   ├── exa.py             # Exa search client
│   │   └── tavily.py          # Tavily search client
│   └── llm/                    # LLM utilities
│       ├── judge.py           # Relevance evaluation
│       ├── processor.py       # Event processing
│       └── ranker.py          # Event ranking
├── test/               # Tests
├── .env.example        # Example environment variables
├── README.md           # This file
└── pyproject.toml      # Project configuration
```

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
