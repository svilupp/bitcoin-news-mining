#!/usr/bin/env python
"""
Step-by-step walkthrough for using Exa API to search for Bitcoin news.
This script uses Exa directly without custom models.
"""

import os
import json
from datetime import datetime, timedelta
from exa_py import Exa


"""Interactive walkthrough for Exa search API."""
print("=== Exa Search Walkthrough ===\n")

exa_client = Exa(api_key=os.environ.get("EXA_API_KEY"))

# Step 3: Configure search parameters
print("\n=== Search Configuration ===")

# Date configuration
search_date = "2023-06-23"
parsed_date = datetime.strptime(search_date, "%Y-%m-%d")
formatted_date = parsed_date.strftime("%Y-%m-%d")
print(f"Using date: {formatted_date}")

# Topic configuration
default_topic = "bitcoin cryptocurrency news and developments"
# Format query
query = f"{default_topic} date:{formatted_date}"
print(f"\nFormatted query: {query}")

# Results configuration
max_results = 10

# Step 4: Execute search
print("\n=== Executing Search ===")
print(f"Searching for: {query}")
print(f"Max results: {max_results}")

# Configure search parameters
search_params = {
    "num_results": max_results,
    "use_autoprompt": True,
    "highlights": True,
    "text": True,
    "type": "auto",
    "category": "news",
    "start_published_date": formatted_date,
    "end_published_date": (parsed_date + timedelta(days=7)).strftime("%Y-%m-%d"),
}

# Execute search
print("\nSending request to Exa API...")
response = exa_client.search_and_contents(query, **search_params)

# Step 5: Process and display results
print(f"\n=== Search Results ({len(response.results)} found) ===")


def print_result(result, i):
    print(f"\n{i}. {result.title}")
    print(f"   Title: {result.title}")
    print(f"   URL: {result.url}")
    print(f"   Published: {result.published_date}")
    print(f"   Score: {result.score}")
    return None


[print_result(result, i) for i, result in enumerate(response.results)]

search_params2 = {
        "num_results": 10,
        "use_autoprompt": True,
        "highlights": True,
        "text": True,
        "category": "news",
        "type": "auto",
        "start_published_date": "2013-06-23",
        "end_published_date": "2013-06-30",
    }
response = exa_client.search_and_contents(
    "bitcoin cryptocurrency news and developments date:2013-06-23",
    **search_params2,
)
[print_result(result, i) for i, result in enumerate(response.results)]

print("\nComparing search parameters:")
for key in search_params:
    if key in search_params2:
        if search_params[key] == search_params2[key]:
            print(f"  {key}: values are the same ({search_params[key]})")
        else:
            print(
                f"  {key}: values differ - search_params: {search_params[key]}, search_params2: {search_params2[key]}"
            )
    else:
        print(f"  {key}: only in search_params ({search_params[key]})")

for key in search_params2:
    if key not in search_params:
        print(f"  {key}: only in search_params2 ({search_params2[key]})")

