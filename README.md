# Tavily Bitcoin Miner

Mine significant events in the world of Bitcoin and other cryptocurrencies for any given date using Tavily's AI search capabilities.

## Prerequisites

Before you begin, ensure you have:
- Python 3.12 or higher
- Git

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tavily-bitcoin-miner
   ```

2. **Install UV (Python package installer)**
   
   UV is a modern, fast Python package installer. Here's how to install it:

   For macOS/Linux:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   For Windows (PowerShell):
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Create and activate a virtual environment**

   Create a new virtual environment:
   ```bash
   uv venv
   ```

   Activate the virtual environment:

   On macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```

   On Windows:
   ```bash
   .venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   uv sync
   ```

   This will install all required packages:
   - httpx
   - openai
   - pandas
   - pydantic
   - tqdm

## Configuration

1. **Set up API keys**

   Create a `.env` file in the project root directory:
   ```
   TAVILY_API_KEY=your_tavily_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

   Required API keys:
   - TAVILY_API_KEY: Get this from [Tavily AI](https://tavily.com)
   - OPENAI_API_KEY: Get this from [OpenAI](https://platform.openai.com/api-keys)

## Usage

1. **Load your environment variables**

   On macOS/Linux:
   ```bash
   source .env
   ```

   On Windows:
   ```bash
   set -a; source .env; set +a
   ```

2. **Run the miner**
   Run any file with `uv run <filename>.py`
   ```bash
   uv run final.py 
   ```