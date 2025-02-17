import httpx
import json
from datetime import datetime
import os
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI
import csv
from pathlib import Path

# os.environ["TAVILY_API_KEY"] = "your-api-key"


class SearchResult(BaseModel):
    """
    Structured representation of a Bitcoin historical event.
    """

    reasoning: Optional[str]
    title: Optional[str]
    description: Optional[str]
    score: Optional[int]
    url: Optional[str]


def tavily_search(date_query: str) -> dict:
    """
    Search for Bitcoin-related information using Tavily API
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
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


def parse_with_openai(raw_results: List[dict], date_query: str) -> SearchResult:
    """
    Parse search results using OpenAI to extract structured information
    """
    client = OpenAI()

    combined_content = "\n\n\n".join(
        [
            f"Title: {item.get('title', '')}\n"
            f"Content: {item.get('content', '')}\n"
            f"URL: {item.get('url', '')}\n"
            f"Published Date: {item.get('published_date', '')}"
            for item in raw_results
        ]
    )

    response = client.beta.chat.completions.parse(
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


def main():
    date_query = "January 3, 2009"  # Example date (Bitcoin genesis block)

    # Step 1: Perform Tavily search
    raw_results = tavily_search(date_query)

    # Step 2: Parse results with OpenAI
    parsed_result = parse_with_openai(raw_results.get("results", []), date_query)

    # Step 3: Save both raw results and parsed result to separate CSV files
    save_raw_results(raw_results, date_query)
    save_parsed_result(parsed_result, date_query)

    print(f"Raw results saved to raw_search_results.csv")
    print(f"Parsed event saved to parsed_events.csv")
    print("\nParsed Result:")
    print(parsed_result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
