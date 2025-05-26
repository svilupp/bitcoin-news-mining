#!/usr/bin/env python3
"""
Cryptocurrency Website Scraper

Main scraper class that orchestrates the extraction of cryptocurrency events from websites.
"""

import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from loguru import logger
from tqdm.asyncio import tqdm_asyncio

from .models import ExtractionConfig, ScrapingResult
from .downloader import WebDownloader, HTMLParser
from .chunker import ContentChunker
from .extractor import OpenAIExtractor
from .storage import StorageManager


class CryptocurrencyWebScraper:
    """Main scraper class that orchestrates the entire process"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.downloader = WebDownloader()
        self.parser = HTMLParser(deduplicate_images=config.deduplicate_images)
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
        """Setup loguru logging configuration"""
        # Remove default handler
        logger.remove()
        
        # Add console handler
        logger.add(
            lambda msg: print(msg, end=""),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            level="INFO"
        )
        
        # Add file handler
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        logger.add(
            log_dir / "scraper.log",
            rotation="10 MB",
            retention="10 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
    
    async def scrape_url(self, url: str, max_chunks: Optional[int] = None) -> ScrapingResult:
        """Scrape a single URL and extract events"""
        start_time = time.time()
        
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
            logger.info(f"Created {len(chunks)} chunks for processing")
            
            # Limit chunks if specified
            if max_chunks and len(chunks) > max_chunks:
                logger.info(f"Limiting to {max_chunks} chunks (total: {len(chunks)})")
                chunks = chunks[:max_chunks]
            
            # Step 4: Save raw data
            logger.info("Saving raw data...")
            await self.storage.save_raw_data(chunks, url)
            
            # Step 5: Extract events using OpenAI
            logger.info(f"Extracting events from {len(chunks)} chunks...")
            extraction_result = await self.extractor.extract_events_from_chunks(chunks)
            
            # Step 6: Calculate results
            processing_time = time.time() - start_time
            
            result = ScrapingResult(
                url=url,
                total_chunks=len(chunks),
                successful_extractions=extraction_result.successful_extractions,
                failed_extractions=extraction_result.failed_extractions,
                events=extraction_result.events,
                raw_chunks=chunks,
                processing_time=processing_time
            )
            
            # Step 7: Save processed events
            logger.info("Saving extracted events...")
            await self.storage.save_extracted_events(extraction_result.events, result)
            
            logger.info(f"Scraping completed in {processing_time:.2f}s")
            logger.info(f"Extracted {len(extraction_result.events)} events from {len(chunks)} chunks")
            
            # Log detailed extraction statistics
            text_chunks_count = len([c for c in chunks if c.content_type == 'text'])
            if extraction_result.failed_extractions > 0:
                logger.warning(f"Extraction failures: {extraction_result.failed_extractions}/{text_chunks_count} text chunks failed")
                if extraction_result.failure_types:
                    for error_type, count in extraction_result.failure_types.items():
                        logger.warning(f"  - {error_type}: {count} failures")
            else:
                logger.info(f"All {text_chunks_count} text chunks processed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            raise
    
    async def scrape_urls(self, urls: List[str], max_chunks_per_url: Optional[int] = None) -> List[ScrapingResult]:
        """Scrape multiple URLs in parallel"""
        logger.info(f"Starting batch scrape of {len(urls)} URLs")
        
        progress_desc = f"Scraping {len(urls)} URLs"
        
        # Create scraping tasks
        tasks = [self.scrape_url(url, max_chunks_per_url) for url in urls]
        
        # Execute with progress bar using tqdm_asyncio
        results = await tqdm_asyncio.gather(
            *tasks,
            desc=progress_desc,
            unit="URLs",
            ascii=True
        )
        
        # Process results
        successful_results = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to scrape {url}: {result}")
            else:
                successful_results.append(result)
        
        logger.info(f"Batch scrape completed: {len(successful_results)}/{len(urls)} successful")
        return successful_results