#!/usr/bin/env python3
"""
Cryptocurrency Website Scraper Script

A focused script for scraping cryptocurrency events from specific websites.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.scraper.models import ExtractionConfig
from src.scraper.scraper import CryptocurrencyWebScraper


async def main():
    """Main entry point for the scraper script"""
    parser = argparse.ArgumentParser(description="Cryptocurrency Website Scraper")
    parser.add_argument("url", nargs='?', help="URL to scrape")
    parser.add_argument("--urls", nargs='+', help="Multiple URLs to scrape")
    parser.add_argument("--max-chunks", type=int, help="Maximum number of chunks to process per URL")
    parser.add_argument("--max-concurrent", type=int, default=20, help="Maximum concurrent requests")
    parser.add_argument("--chunk-size", type=int, default=2000, help="Maximum tokens per chunk")
    parser.add_argument("--model", type=str, default="gpt-4.1-mini", help="OpenAI model to use")
    
    args = parser.parse_args()
    
    # Validate input
    if not args.url and not args.urls:
        parser.error("Either --url or --urls is required")
    
    # Collect all URLs
    urls = []
    if args.url:
        urls.append(args.url)
    if args.urls:
        urls.extend(args.urls)
    
    # Create configuration
    config = ExtractionConfig(
        max_concurrent_requests=args.max_concurrent,
        chunk_size_limit=args.chunk_size,
        include_images=True,
        model_name=args.model
    )
    
    # Initialize scraper
    try:
        scraper = CryptocurrencyWebScraper(config)
    except ValueError as e:
        logger.error(f"Failed to initialize scraper: {e}")
        sys.exit(1)
    
    # Execute scraping
    try:
        if len(urls) == 1:
            # Single URL
            result = await scraper.scrape_url(urls[0], args.max_chunks)
            print_summary(result)
        else:
            # Multiple URLs
            results = await scraper.scrape_urls(urls, args.max_chunks)
            for result in results:
                print_summary(result)
        
        logger.success("Scraping completed successfully")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)


def print_summary(result):
    """Print a summary of scraping results"""
    print(f"\n{'='*60}")
    print(f"URL: {result.url}")
    print(f"Total chunks: {result.total_chunks}")
    print(f"Successful extractions: {result.successful_extractions}")
    print(f"Failed extractions: {result.failed_extractions}")
    success_rate = (result.successful_extractions / max(result.total_chunks, 1)) * 100
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Total events: {len(result.events)}")
    avg_events_per_chunk = len(result.events) / max(result.successful_extractions, 1)
    print(f"Average events per successful chunk: {avg_events_per_chunk:.1f}")
    print(f"Processing time: {result.processing_time:.2f}s")
    chunks_per_second = result.total_chunks / max(result.processing_time, 0.1)
    print(f"Processing rate: {chunks_per_second:.1f} chunks/second")
    
    if result.events:
        print(f"\nSample events:")
        for i, event in enumerate(result.events[:3], 1):
            print(f"{i}. {event.brief_description}")


if __name__ == "__main__":
    asyncio.run(main())