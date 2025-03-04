import httpx
import json
from datetime import datetime
import os
from typing import List, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
import csv
from pathlib import Path
from tqdm.asyncio import tqdm

# os.environ["TAVILY_API_KEY"] = "your-api-key"


class SearchResult(BaseModel):
    """
    Structured representation of a Bitcoin historical event.

    The score field indicates the historical significance and date confidence:

    5 - Extremely significant event with definitive date confirmation
       - Major historical milestones (e.g. Bitcoin genesis block)
       - Well-documented price records or market events
       - Multiple reliable sources confirm exact date

    4 - Very significant event with strong date confidence
       - Important technical developments or upgrades
       - Notable price movements or market activity
       - Date is well-documented but may have some ambiguity

    3 - Moderately significant event with reasonable date confidence
       - Interesting but not groundbreaking developments
       - Moderate market impact or adoption milestones
       - Date is reported but may have conflicting sources

    2 - Minor event with uncertain date
       - Small technical updates or announcements
       - Limited market impact
       - Date is mentioned but poorly documented

    1 - Minimal significance or highly uncertain date
       - Trivial events or developments
       - Negligible market impact
       - Date is speculative or contradicted by sources
    """

    reasoning: Optional[str]
    title: Optional[str]
    description: Optional[str]
    score: Optional[int]
    url: Optional[str]


async def tavily_search(date_query: str) -> dict:
    """
    Search for Bitcoin-related information using Tavily API (async version)
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("Please set TAVILY_API_KEY in your environment variables")

    url = "https://api.tavily.com/search"
    search_query = f"Significant events in the world of Bitcoin and other cryptocurrencies on {date_query}?"

    params = {
        "api_key": api_key,
        "query": search_query,
        "search_depth": "advanced",
        "include_domains": [
            "coindesk.com",
            "cointelegraph.com",
            "bitcoin.com",
            "blockchain.com",
        ],
        "max_results": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


async def parse_with_openai(raw_results: List[dict], date_query: str) -> SearchResult:
    """
    Parse search results using OpenAI to extract structured information (async version)
    """
    client = AsyncOpenAI()

    combined_content = "\n\n\n".join(
        [
            f"Title: {item.get('title', '')}\n"
            f"Content: {item.get('content', '')}\n"
            f"URL: {item.get('url', '')}\n"
            f"Published Date: {item.get('published_date', '')}"
            for item in raw_results
        ]
    )

    response = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        response_format=SearchResult,
        messages=[
            {
                "role": "system",
                "content": f"""Your task is to identify the most significant event that influenced Bitcoin's price on {date_query}.
                You will be given several search results, pick the most relevant one.
                Only select events from the provided search results, do not make up events.
                The event must occur exactly on {date_query} - if unsure, provide empty values.
                
                Return a JSON object with these fields:
                - reasoning: explanation of why this event is significant
                - title: main event or title
                - description: detailed description
                - score: (1-5) based on historical significance and date confidence
                - url: source URL for the event

                Even if you do not provide any results, you must include a reasoning why you haven't included any of the provided search results. 
                
                If no content matches the date or is relevant, return empty values.""",
            },
            {
                "role": "user",
                "content": f"Here are the Bitcoin-related search results for {date_query}:\n{combined_content}",
            },
        ],
    )

    return response.choices[0].message.parsed


def save_raw_results(results: dict, date_query: str, filename="raw_search_results.csv"):
    """Save raw search results to CSV"""
    file_exists = Path(filename).exists()

    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["query_date", "title", "content", "url", "published_date"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for item in results.get("results", []):
            writer.writerow(
                {
                    "query_date": date_query,
                    "title": item.get("title"),
                    "content": item.get("content"),
                    "url": item.get("url"),
                    "published_date": item.get("published_date"),
                }
            )


def save_parsed_result(
    parsed_result: SearchResult, date_query: str, filename="parsed_events.csv"
):
    """Save parsed OpenAI result to CSV"""
    file_exists = Path(filename).exists()

    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["query_date", "title", "description", "reasoning", "score", "url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "query_date": date_query,
                "title": parsed_result.title,
                "description": parsed_result.description,
                "reasoning": parsed_result.reasoning,
                "score": parsed_result.score,
                "url": parsed_result.url,
            }
        )


async def process_date(date_query: str, progress_bar: tqdm = None):
    """Process a single date through the entire workflow"""
    if progress_bar:
        progress_bar.set_description(f"Processing {date_query}")

    # Step 1: Perform Tavily search
    raw_results = await tavily_search(date_query)
    if progress_bar:
        progress_bar.set_postfix_str("Completed Tavily search")

    # Step 2: Parse results with OpenAI
    parsed_result = await parse_with_openai(raw_results.get("results", []), date_query)
    if progress_bar:
        progress_bar.set_postfix_str("Completed OpenAI parsing")

    # Step 3: Save both raw results and parsed result
    save_raw_results(raw_results, date_query)
    save_parsed_result(parsed_result, date_query)

    return parsed_result


async def main():
    from datetime import datetime, timedelta
    import asyncio

    # Generate dates between Jan 1 and Jan 15, 2012
    start_date = datetime(2012, 1, 1)
    dates = [(start_date + timedelta(days=i)).strftime("%B %d, %Y") for i in range(5)]

    # Create tasks for all dates
    tasks = [process_date(date) for date in dates]

    # Process all dates with progress bar
    for result in tqdm(
        asyncio.as_completed(tasks), total=len(dates), desc="Processing dates"
    ):
        await result

    print("\nProcessing complete!")
    print("Raw results saved to raw_search_results.csv")
    print("Parsed events saved to parsed_events.csv")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
