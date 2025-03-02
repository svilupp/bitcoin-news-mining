#!/usr/bin/env python
"""Script to evaluate search results with LLM judge."""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm import create_async_client, get_default_model
from src.llm.judge import EventJudge, JudgeResponse
from src.models import Event

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def evaluate_search_result(
    judge: EventJudge, search_result: Dict[str, Any], query_date: datetime
) -> Dict[str, Any]:
    """Evaluate a single search result.

    Args:
        judge: EventJudge instance
        search_result: The search result to evaluate
        query_date: The date to evaluate against

    Returns:
        The search result with evaluation data
    """
    evaluation = await judge.evaluate_relevance(search_result, query_date)

    # Add evaluation data to the result
    result_with_eval = search_result.copy()
    result_with_eval["is_relevant"] = evaluation.is_relevant
    result_with_eval["confidence"] = evaluation.confidence
    result_with_eval["reasoning"] = evaluation.reasoning

    logger.info(
        f"Result: {result_with_eval.get('title', 'No title')[:50]}... "
        f"Relevant: {evaluation.is_relevant} "
        f"Confidence: {evaluation.confidence:.2f}"
    )

    return result_with_eval


async def main():
    """Run evaluation of search results."""
    parser = argparse.ArgumentParser(
        description="Evaluate search results with LLM judge"
    )

    parser.add_argument(
        "--input", type=str, required=True, help="Input JSON file with search results"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluated_results.json",
        help="Output file for evaluated results (default: evaluated_results.json)",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date to evaluate for in YYYY-MM-DD format (overrides date in search results)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Relevance confidence threshold (0.0-1.0) for accepting results (default: 0.7)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "google", "anthropic", "azure"],
        default="openai",
        help="LLM provider to use (default: openai)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name to use (if not provided, uses provider default)",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=5,
        help="Number of parallel evaluations to run (default: 5)",
    )

    args = parser.parse_args()

    # Get API key based on provider
    api_key_var = f"{args.provider.upper()}_API_KEY"
    api_key = os.environ.get(api_key_var)
    if not api_key:
        logger.error(f"{api_key_var} environment variable not set")
        sys.exit(1)

    # Load search results
    try:
        with open(args.input, "r") as f:
            search_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load search results: {str(e)}")
        sys.exit(1)

    # Parse the date from arguments or search results
    if args.date:
        try:
            query_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD format.")
            sys.exit(1)
    else:
        # Try to get date from search results
        search_date_str = search_data.get("search_date")
        if not search_date_str:
            logger.error("No date provided in command line or search results")
            sys.exit(1)

        try:
            query_date = datetime.fromisoformat(search_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            logger.error(f"Invalid date format in search results: {search_date_str}")
            sys.exit(1)

    # Create async client for the specified provider
    client = create_async_client(api_key=api_key, provider=args.provider)

    # Get model name (command line arg or provider default)
    model_name = args.model or get_default_model(args.provider)

    # Initialize LLM judge
    judge = EventJudge(client=client, model_name=model_name)

    # Evaluate search results
    provider = search_data.get("provider", "unknown")
    results = search_data.get("results", [])

    logger.info(
        f"Evaluating {len(results)} results from {provider} for date {query_date.strftime('%Y-%m-%d')} "
        f"using {args.provider.upper()} {model_name}"
    )

    # Process results in batches for parallel execution
    evaluated_results = []

    # Use asyncio.Semaphore to limit the number of concurrent evaluations
    semaphore = asyncio.Semaphore(args.parallel)

    async def evaluate_with_semaphore(result):
        async with semaphore:
            return await evaluate_search_result(judge, result, query_date)

    # Process all results in parallel (with concurrency limit)
    tasks = [evaluate_with_semaphore(result) for result in results]
    evaluated_results = await asyncio.gather(*tasks)

    # Filter relevant results based on threshold
    relevant_results = [
        result
        for result in evaluated_results
        if result.get("is_relevant", False)
        and result.get("confidence", 0) >= args.threshold
    ]

    logger.info(
        f"Found {len(relevant_results)} relevant results out of {len(results)} "
        f"with confidence >= {args.threshold}"
    )

    # Create output data
    output_data = {
        "search_date": search_data.get("search_date"),
        "query": search_data.get("query"),
        "provider": search_data.get("provider"),
        "total_results": len(results),
        "relevant_results": len(relevant_results),
        "threshold": args.threshold,
        "results": relevant_results,
        "evaluation_time": datetime.now().isoformat(),
        "evaluation_model": f"{args.provider}:{model_name}",
    }

    # Save output file
    try:
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Saved evaluated results to {args.output}")
    except Exception as e:
        logger.error(f"Failed to save output file: {str(e)}")
        sys.exit(1)

    logger.info("Evaluation complete")


if __name__ == "__main__":
    asyncio.run(main())
