#!/usr/bin/env python3
"""
Cryptocurrency Website Scraper

A self-standing script that extracts cryptocurrency events from websites using OpenAI's parse extraction.
Downloads websites, strips HTML, chunks content, and processes in parallel to extract key events.
"""

import asyncio
import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.models import ExtractionConfig, ScrapingResult
from src.scraper.downloader import WebDownloader, HTMLParser
from src.scraper.chunker import ContentChunker
from src.scraper.extractor import OpenAIExtractor
from src.scraper.storage import StorageManager


class CryptocurrencyWebScraper:
    """Main scraper class that orchestrates the entire process"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.downloader = WebDownloader()
        self.parser = HTMLParser()
        self.chunker = ContentChunker(config.chunk_size_limit)
        self.storage = StorageManager()
        
        # Initialize OpenAI extractor
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.extractor = OpenAIExtractor(api_key, config)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/scraper.log', mode='a')
            ]
        )
        
        # Create logs directory if it doesn't exist
        Path('logs').mkdir(exist_ok=True)
    
    async def scrape_url(self, url: str, max_chunks: int = None) -> ScrapingResult:
        """Scrape a single URL and extract events"""
        start_time = time.time()
        logger = logging.getLogger(__name__)
        
        logger.info(f"Starting scrape of {url}")
        
        try:
            # Step 1: Download HTML content
            logger.info("Downloading HTML content...")
            html_content = await self.downloader.download_url(url)
            if not html_content:
                raise ValueError(f"Failed to download content from {url}")
            
            # Step 2: Parse HTML and extract sections
            logger.info("Parsing HTML content...")
            parsed_content = self.parser.parse_html(html_content, url)
            logger.info(f"Found {parsed_content['total_sections']} sections")
            
            # Step 3: Create chunks
            logger.info("Creating content chunks...")
            chunks = self.chunker.create_chunks(parsed_content, url)
            chunks = self.chunker.optimize_chunks(chunks)
            
            # Limit chunks if specified
            if max_chunks and len(chunks) > max_chunks:
                logger.info(f"Limiting to {max_chunks} chunks (total: {len(chunks)})")
                chunks = chunks[:max_chunks]
            
            # Step 4: Save raw data
            logger.info("Saving raw data...")
            await self.storage.save_raw_data(chunks, url)
            
            # Step 5: Extract events using OpenAI
            logger.info(f"Extracting events from {len(chunks)} chunks...")
            events = await self.extractor.extract_events_from_chunks(chunks)
            
            # Step 6: Calculate results
            processing_time = time.time() - start_time
            text_chunks = [c for c in chunks if c.content_type == 'text']
            successful_extractions = len([e for e in events if e])
            failed_extractions = len(text_chunks) - successful_extractions
            
            result = ScrapingResult(
                url=url,
                total_chunks=len(chunks),
                successful_extractions=successful_extractions,
                failed_extractions=failed_extractions,
                events=events,
                raw_chunks=chunks,
                processing_time=processing_time
            )
            
            # Step 7: Save processed events
            logger.info("Saving extracted events...")
            await self.storage.save_extracted_events(events, result)
            
            logger.info(f"Scraping completed in {processing_time:.2f}s")
            logger.info(f"Extracted {len(events)} events from {len(chunks)} chunks")
            
            return result
            
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            raise
    
    async def test_small_extraction(self, sample_text: str):
        """Test extraction with a small sample for debugging"""
        logger = logging.getLogger(__name__)
        logger.info("Testing small extraction...")
        
        events = await self.extractor.test_extraction(sample_text)
        
        logger.info(f"Test extraction completed: {len(events)} events found")
        for i, event in enumerate(events):
            logger.info(f"Event {i+1}: {event.brief_description}")
        
        return events


async def main():
    """Main entry point for the scraper"""
    parser = argparse.ArgumentParser(description="Cryptocurrency Website Scraper")
    parser.add_argument("--url", type=str, help="URL to scrape")
    parser.add_argument("--max-chunks", type=int, help="Maximum number of chunks to process")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Maximum concurrent requests")
    parser.add_argument("--chunk-size", type=int, default=2000, help="Maximum tokens per chunk")
    parser.add_argument("--include-images", action="store_true", help="Process images")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="OpenAI model to use")
    parser.add_argument("--dry-run", action="store_true", help="Show extraction plan without executing")
    parser.add_argument("--test", type=str, help="Test extraction with provided text")
    parser.add_argument("--list-domains", action="store_true", help="List saved domains")
    
    args = parser.parse_args()
    
    # Create configuration
    config = ExtractionConfig(
        max_concurrent_requests=args.max_concurrent,
        chunk_size_limit=args.chunk_size,
        include_images=args.include_images,
        model_name=args.model
    )
    
    # Initialize scraper
    scraper = CryptocurrencyWebScraper(config)
    
    # Handle different operations
    if args.list_domains:
        domains = scraper.storage.list_saved_domains()
        print(f"Found {len(domains)} domains with saved data:")
        for domain, files in domains.items():
            print(f"  {domain}:")
            if 'raw_files' in files:
                print(f"    Raw files: {len(files['raw_files'])}")
            if 'output_files' in files:
                print(f"    Output files: {len(files['output_files'])}")
        return
    
    if args.test:
        events = await scraper.test_small_extraction(args.test)
        print(f"\nExtracted {len(events)} events:")
        for i, event in enumerate(events, 1):
            print(f"{i}. {event.brief_description}")
            print(f"   Date: {event.date}")
            print(f"   Full text: {event.full_text[:100]}...")
            print()
        return
    
    if not args.url:
        print("Error: --url is required (or use --test or --list-domains)")
        parser.print_help()
        return
    
    if args.dry_run:
        print(f"Dry run for URL: {args.url}")
        print(f"Configuration:")
        print(f"  Model: {config.model_name}")
        print(f"  Max concurrent: {config.max_concurrent_requests}")
        print(f"  Chunk size: {config.chunk_size_limit}")
        print(f"  Include images: {config.include_images}")
        print(f"  Max chunks: {args.max_chunks or 'unlimited'}")
        print("\nWould execute scraping with these settings.")
        return
    
    # Execute scraping
    try:
        result = await scraper.scrape_url(args.url, args.max_chunks)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"SCRAPING SUMMARY")
        print(f"{'='*60}")
        print(f"URL: {result.url}")
        print(f"Total chunks processed: {result.total_chunks}")
        print(f"Successful extractions: {result.successful_extractions}")
        print(f"Failed extractions: {result.failed_extractions}")
        print(f"Total events extracted: {len(result.events)}")
        print(f"Processing time: {result.processing_time:.2f} seconds")
        print(f"Success rate: {(result.successful_extractions/result.total_chunks*100):.1f}%")
        
        if result.events:
            print(f"\nSample events:")
            for i, event in enumerate(result.events[:3], 1):
                print(f"{i}. {event.brief_description}")
        
        print(f"\nData saved to data_raw/ and data_output/ directories")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Set event loop policy for Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())