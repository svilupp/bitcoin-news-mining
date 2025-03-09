"""Simplified test for the EventJudge and CryptoEventPipeline."""

import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, Field

# Import the CryptoEventPipeline
from src.pipeline.crypto_event_pipeline import CryptoEventPipeline
from src.llm.judge import JUDGE_SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchResultItem(BaseModel):
    """Model for a single search result item."""

    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None


class SearchResult(BaseModel):
    """Model for storing search query results."""

    query: str
    items: List[SearchResultItem]
    total_results: int

    def format_results_for_prompt(self) -> str:
        """Format search results into a combined content string for LLM prompting."""
        combined_content = ""
        for i, item in enumerate(self.items):
            combined_content += f"News Item {i+1}:\n"
            combined_content += f"Title: {item.title}\n"
            combined_content += (
                f"Published date: {item.published_date or 'No published date'}\n"
            )
            combined_content += f"URL: {item.url}\n"
            combined_content += f"Content: {item.snippet}\n\n---\n"
        return combined_content


class CryptoEvent(BaseModel):
    """
    Structured representation of a Bitcoin or cryptocurrency historical event.

    Date is the date of the event, in the format "YYYY-MM-DD".
    Published date is the date of publication of the article/source, in the format "YYYY-MM-DD", provide if different from the date of event.

    The score field indicates the historical significance for Bitcoin and date confidence.
    """

    reasoning: str
    title: str
    description: str
    date: str
    published_date: Optional[str]
    score: int
    url: str


class CryptoEvents(BaseModel):
    """List of the most relevant Bitcoin or cryptocurrency historical events. The list must be sorted by relevance score and unique events only."""

    reasoning: str
    events: List[CryptoEvent] = Field(default_factory=list)


class EventJudge:
    """OpenAI-based judge for evaluating search results."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        """Initialize OpenAI judge.

        Args:
            api_key: OpenAI API key
            model_name: OpenAI model name to use
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model_name
        self.system_prompt = JUDGE_SYSTEM_PROMPT

    async def evaluate_relevance(
        self,
        search_result: SearchResult,
        query: str,
        query_date: datetime,
    ) -> CryptoEvents:
        """Evaluate if a search result is relevant for Bitcoin/crypto on a specific date.

        Args:
            search_result: Search result to evaluate
            query: The search query
            query_date: Date the search is about

        Returns:
            CryptoEvents object with evaluation results
        """
        formatted_date = query_date.strftime("%B %d, %Y")
        combined_content = search_result.format_results_for_prompt()

        try:
            # Generate response
            logger.info(f"Evaluating relevance with OpenAI for date: {formatted_date}")

            system_prompt = self.system_prompt.replace(
                "{{formatted_date}}", formatted_date
            )

            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": f"Please evaluate search results of this query: {query} focused on {formatted_date}.\nSearch results:\n------\n{combined_content}\n------\n",
                    },
                ],
                response_format={"type": "json_object"},
            )

            response_text = completion.choices[0].message.content
            logger.debug(f"Raw response: {response_text}")

            # Parse the JSON response
            response_data = json.loads(response_text)

            # Create a CryptoEvents object
            if "reasoning" not in response_data:
                response_data["reasoning"] = "No reasoning provided"

            if "events" not in response_data:
                # Check if the response has a different structure
                if "event_data" in response_data:
                    response_data["events"] = response_data.pop("event_data")
                else:
                    response_data["events"] = []

            # Create the CryptoEvents object
            events = CryptoEvents(reasoning=response_data["reasoning"], events=[])

            # Add each event
            for event_data in response_data["events"]:
                # Ensure all required fields are present
                if "reasoning" not in event_data:
                    event_data["reasoning"] = "No reasoning provided"

                try:
                    event = CryptoEvent(**event_data)
                    events.events.append(event)
                except Exception as e:
                    logger.error(
                        f"Error parsing event: {str(e)}, event data: {event_data}"
                    )

            return events

        except Exception as e:
            logger.error(f"OpenAI evaluation error: {str(e)}")
            # Return default response in case of error
            return CryptoEvents(
                reasoning=f"Error during evaluation: {str(e)}",
                events=[],
            )


async def test_direct_judge():
    """Test the EventJudge directly."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")

    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    # Create mock search results
    mock_items = [
        SearchResultItem(
            title="Bitcoin Surpasses $60,000 for First Time",
            url="https://example.com/bitcoin-60k",
            snippet="Bitcoin reached a new all-time high above $60,000 on Saturday, March 13, 2021, as stimulus checks and institutional interest boosted the cryptocurrency.",
            published_date="2021-03-13",
        ),
        SearchResultItem(
            title="UK Financial Regulator Issues Crypto Warning",
            url="https://example.com/uk-fca-warning",
            snippet="The UK's Financial Conduct Authority (FCA) issued a warning to consumers about the risks of investing in cryptocurrencies on March 12, 2021.",
            published_date="2021-03-12",
        ),
        SearchResultItem(
            title="Major European Bank Announces Bitcoin Custody Service",
            url="https://example.com/euro-bank-bitcoin",
            snippet="A leading European financial institution announced plans to offer Bitcoin custody services to institutional clients starting April 2021.",
            published_date="2021-03-15",
        ),
    ]

    mock_search_result = SearchResult(
        query="Bitcoin news March 2021",
        items=mock_items,
        total_results=3,
    )

    # Create judge and run evaluation
    judge = EventJudge(api_key=api_key, model_name="gemini-2.0-flash")
    judge.client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=google_api_key,
    )

    query_date = datetime(2021, 3, 13)
    query = "Bitcoin news and developments"

    print(
        f"Running direct judge evaluation for query: {query} on date: {query_date.strftime('%B %d, %Y')}"
    )

    judge.model = "gemini-2.0-flash"
    events = await judge.evaluate_relevance(
        search_result=mock_search_result,
        query=query,
        query_date=query_date,
    )

    print("\nDirect Judge Evaluation Results:")
    print(f"Reasoning: {events.reasoning}")
    print(f"Number of events found: {len(events.events)}")

    print("\nEvents:")
    for i, event in enumerate(events.events, 1):
        print(f"\n--- Event {i} ---")
        print(f"Title: {event.title}")
        print(f"Description: {event.description}")
        print(f"Date: {event.date}")
        print(f"Published Date: {event.published_date or 'Same as event date'}")
        print(f"Score: {event.score}")
        print(f"URL: {event.url}")
        print(f"Reasoning: {event.reasoning}")


async def test_pipeline_rank():
    """Test the _rank_search_results method of CryptoEventPipeline."""
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    exa_api_key = os.environ.get("EXA_API_KEY", "")
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")

    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    if not exa_api_key:
        raise ValueError("EXA_API_KEY environment variable not set")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    # Create mock search results
    mock_items = [
        SearchResultItem(
            title="Bitcoin Surpasses $60,000 for First Time",
            url="https://example.com/bitcoin-60k",
            snippet="Bitcoin reached a new all-time high above $60,000 on Saturday, March 13, 2021, as stimulus checks and institutional interest boosted the cryptocurrency.",
            published_date="2021-03-13",
        ),
        SearchResultItem(
            title="UK Financial Regulator Issues Crypto Warning",
            url="https://example.com/uk-fca-warning",
            snippet="The UK's Financial Conduct Authority (FCA) issued a warning to consumers about the risks of investing in cryptocurrencies on March 12, 2021.",
            published_date="2021-03-12",
        ),
        SearchResultItem(
            title="Major European Bank Announces Bitcoin Custody Service",
            url="https://example.com/euro-bank-bitcoin",
            snippet="A leading European financial institution announced plans to offer Bitcoin custody services to institutional clients starting April 2021.",
            published_date="2021-03-15",
        ),
    ]

    mock_search_result = SearchResult(
        query="Bitcoin news March 2021",
        items=mock_items,
        total_results=3,
    )

    # Initialize pipeline
    pipeline = CryptoEventPipeline(
        exa_api_key=exa_api_key,
        openai_api_key=openai_api_key,
        load_db=False,
    )

    # Set up for Gemini
    model = "gemini-2.0-flash"
    pipeline.judge.client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=google_api_key,
    )
    pipeline.judge.model = model

    query_date = datetime(2021, 3, 13)
    query = "Bitcoin news and developments"

    print(
        f"Running pipeline._rank_search_results for query: {query} on date: {query_date.strftime('%B %d, %Y')}"
    )

    # Call the _rank_search_results method
    events = await pipeline._rank_search_results(
        search_result=mock_search_result,
        formatted_query=query,
        date=query_date,
        judge_system_prompt=JUDGE_SYSTEM_PROMPT,
        judge_model=model,
    )

    print("\nPipeline Ranking Results:")
    print(f"Number of events found: {len(events)}")

    print("\nEvents:")
    for i, event in enumerate(events, 1):
        print(f"\n--- Event {i} ---")
        print(f"Title: {event.title}")
        print(f"Description: {event.description}")
        print(f"Date: {event.event_date}")
        print(f"Score: {event.relevance_score}")
        print(f"URL: {event.source_url}")
        print(f"Reasoning: {event.relevance_reasoning}")


async def main():
    """Run both tests."""
    print("=== Testing Direct Judge ===")
    await test_direct_judge()

    print("\n\n=== Testing Pipeline Rank ===")
    await test_pipeline_rank()


if __name__ == "__main__":
    asyncio.run(main())
