import httpx
import json
from datetime import datetime
import os
import pandas as pd

# os.environ["TAVILY_API_KEY"] = "your-api-key"
# os.environ["OPENAI_API_KEY"] = "your-key"


def search_bitcoin_history(date_query):
    """
    Search for Bitcoin-related information for a specific date using Tavily API

    Args:
        date_query (str): The date or event to search for

    Returns:
        dict: Formatted response containing the search results
    """
    # Get API key from environment variables
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        raise ValueError("Please set TAVILY_API_KEY in your environment variables")

    # API endpoint
    url = "https://api.tavily.com/search"

    # Format the search query
    search_query = f"Significant events in the world of Bitcoin and other cryptocurrencies on {date_query}?"

    # Request parameters
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
        # Make the API request using httpx
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=params)
            response.raise_for_status()

            # Parse the response
            result = response.json()
            ## Show us the raw response
            print(json.dumps(result, indent=2))

            # Format the output
            formatted_result = {
                "query_date": date_query,
                "search_query": search_query,
                "results": [],
            }

            # Extract relevant information from each result
            for item in result.get("results", []):
                formatted_result["results"].append(
                    {
                        "title": item.get("title"),
                        "content": item.get("content"),
                        "url": item.get("url"),
                        "published_date": item.get("published_date"),
                    }
                )

            return formatted_result

    except httpx.HTTPError as e:
        return {"error": f"HTTP error occurred: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


def save_to_csv(result, filename="bitcoin_history.csv"):
    """
    Save the search results to a CSV file using pandas

    Args:
        result (dict): The formatted search results
        filename (str): Name of the CSV file to save to
    """
    # Create a list of dictionaries for pandas DataFrame
    rows = []
    for item in result["results"]:
        rows.append(
            {
                "query_date": result["query_date"],
                "title": item["title"],
                "content": item["content"],
                "url": item["url"],
                "published_date": item["published_date"],
            }
        )

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Check if file exists to determine mode
    mode = "a" if pd.io.common.file_exists(filename) else "w"
    header = not pd.io.common.file_exists(filename)

    # Save to CSV
    df.to_csv(filename, mode=mode, header=header, index=False)


def main():
    # Example usage
    date_query = "January 3, 2009"  # Example date (Bitcoin genesis block)
    result = search_bitcoin_history(date_query)

    # Save results to CSV
    save_to_csv(result, f"bitcoin_history_{date_query}.csv")

    # Pretty print the results
    print(json.dumps(result, indent=2))
    print(f"\nResults have been saved to bitcoin_history_{date_query}.csv")


if __name__ == "__main__":
    main()
