import asyncio
from datetime import datetime
from typing import List
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm_asyncio

from .models import RawChunk, CryptoEvent, ExtractionConfig, ExtractionResult


class EventExtraction(BaseModel):
    """Model for OpenAI structured extraction output"""
    events: List[CryptoEvent] = Field(description="List of cryptocurrency events found in the text")


class OpenAIExtractor:
    """Extract cryptocurrency events using OpenAI's structured output"""
    
    def __init__(self, api_key: str, config: ExtractionConfig):
        self.client = AsyncOpenAI(api_key=api_key)
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
    async def extract_events_from_chunks(self, chunks: List[RawChunk]) -> ExtractionResult:
        """Extract events from all chunks in parallel"""
        logger.info(f"Starting extraction from {len(chunks)} chunks")
        
        # Filter text chunks only for event extraction
        text_chunks = [chunk for chunk in chunks if chunk.content_type == 'text']
        
        # Log concurrency info
        logger.info(f"Using {self.config.max_concurrent_requests} concurrent requests")
        
        # Execute all tasks concurrently with progress bar
        progress_desc = f"Extracting events from {len(text_chunks)} text chunks"
        
        # Create extraction tasks
        tasks = [asyncio.create_task(self._extract_from_single_chunk(chunk)) for chunk in text_chunks]
        
        # Execute with progress bar using tqdm_asyncio
        results = await tqdm_asyncio.gather(
            *tasks,
            desc=progress_desc,
            unit="chunks",
            ascii=True
        )
        
        # Collect successful extractions and categorize failures
        all_events = []
        successful_extractions = 0
        failed_extractions = 0
        failure_types = {}
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                chunk = text_chunks[i]
                error_type = type(result).__name__
                failure_types[error_type] = failure_types.get(error_type, 0) + 1
                
                logger.error(f"Extraction failed for chunk {chunk.chunk_index} (URL: {chunk.url}): {error_type}: {result}")
                logger.error(f"Failed chunk content preview: {chunk.content[:100]}...")
                if chunk.section_heading:
                    logger.error(f"Failed chunk section: {chunk.section_heading}")
                failed_extractions += 1
            elif isinstance(result, list):
                all_events.extend(result)
                successful_extractions += 1
            else:
                chunk = text_chunks[i]
                logger.error(f"Unexpected result type for chunk {chunk.chunk_index}: {type(result)} - {result}")
                failed_extractions += 1
        
        # Deduplicate events within this extraction run
        deduplicated_events = self._deduplicate_events(all_events)
        
        logger.info(f"Extraction complete: {successful_extractions} successful, {failed_extractions} failed")
        logger.info(f"Total events extracted: {len(all_events)}, unique events: {len(deduplicated_events)}")
        
        # Log failure summary if there were failures
        if failed_extractions > 0:
            logger.warning(f"FAILURE SUMMARY: {failed_extractions} total failures")
            for error_type, count in failure_types.items():
                logger.warning(f"  - {error_type}: {count} failures")
        
        return ExtractionResult(
            events=deduplicated_events,
            successful_extractions=successful_extractions,
            failed_extractions=failed_extractions,
            failure_types=failure_types
        )
    
    async def _extract_from_single_chunk(self, chunk: RawChunk) -> List[CryptoEvent]:
        """Extract events from a single chunk with retry logic"""
        start_time = asyncio.get_event_loop().time()
        async with self.semaphore:
            acquired_time = asyncio.get_event_loop().time()
            wait_time = acquired_time - start_time
            if wait_time > 0.1:
                logger.debug(f"Chunk {chunk.chunk_index} waited {wait_time:.2f}s for semaphore")
            
            for attempt in range(self.config.max_retries):
                try:
                    # Add delay between retries
                    if attempt > 0:
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying chunk {chunk.chunk_index} after {wait_time}s (attempt {attempt + 1})")
                        await asyncio.sleep(wait_time)
                    
                    events = await self._call_openai_extraction(chunk)
                    
                    # Update events with chunk metadata
                    for event in events:
                        event.chunk_index = chunk.chunk_index
                        event.source_url = chunk.url
                        event.extraction_timestamp = datetime.now()
                        if chunk.section_heading:
                            event.section_heading = chunk.section_heading
                    
                    end_time = asyncio.get_event_loop().time()
                    total_time = end_time - start_time
                    logger.debug(f"Extracted {len(events)} events from chunk {chunk.chunk_index} in {total_time:.2f}s")
                    return events
                    
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for chunk {chunk.chunk_index}: {type(e).__name__}: {e}")
                    if chunk.section_heading:
                        logger.warning(f"Failed chunk section: {chunk.section_heading}")
                    logger.warning(f"Failed chunk content preview: {chunk.content[:150]}...")
                    if attempt == self.config.max_retries - 1:
                        logger.error(f"All {self.config.max_retries} attempts failed for chunk {chunk.chunk_index}")
                        logger.error(f"Final failure details - Section: {chunk.section_heading}, Content length: {len(chunk.content)}, Tokens estimate: {chunk.tokens_estimate}")
                        raise
        
        return []
    
    async def _call_openai_extraction(self, chunk: RawChunk) -> List[CryptoEvent]:
        """Make the actual OpenAI API call with structured output"""
        
        # Create the extraction prompt
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(chunk)
        
        try:
            # Use the .parse() method for structured output
            completion = await self.client.beta.chat.completions.parse(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=EventExtraction,
                temperature=0.1,  # Low temperature for consistency
                max_tokens=30000
            )
            
            # Extract the parsed response
            extraction_result = completion.choices[0].message.parsed
            
            if extraction_result and extraction_result.events:
                return extraction_result.events
            else:
                logger.debug(f"No events found in chunk {chunk.chunk_index}")
                return []
                
        except Exception as e:
            logger.error(f"OpenAI API call failed for chunk {chunk.chunk_index}: {type(e).__name__}: {e}")
            logger.error(f"API call details - Model: {self.config.model_name}, Chunk tokens: {chunk.tokens_estimate}")
            logger.error(f"System prompt length: {len(system_prompt)}, User prompt length: {len(user_prompt)}")
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                logger.error(f"HTTP status code: {e.response.status_code}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text[:500]}...")
            raise
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for event extraction"""
        return """Your task is to extract cryptocurrency events from scraped web pages and images.

Your goal is to identify significant events related to cryptocurrencies, blockchain technology, regulations, market movements, and technological developments.

For each event you find, extract:
1. **Date**: Parse any date mentioned (month, day, year). If no specific date is found, infer from context or use "unknown"
2. **Full text**: The complete description of the event as it appears in the source
3. **Brief description**: A concise summary in exactly 100-110 characters that captures the essence of the event

Guidelines:
- Only extract events that are factual and significant
- Focus on cryptocurrency, blockchain, DeFi, NFT, regulation, and market events
- Ignore general financial news unless directly related to crypto
- If dates are relative (e.g., "last week"), try to infer the actual date from context
- Brief descriptions should be informative and specific
- If the text is a continuation from a previous section, consider the context

Be precise and only extract events that are clearly relevant to cryptocurrency/blockchain space."""
    
    def _create_user_prompt(self, chunk: RawChunk) -> str:
        """Create the user prompt with chunk content"""
        prompt = ""
        
        # Add section heading for context if available
        if chunk.section_heading:
            prompt += f"Section Heading: {chunk.section_heading}\n\n"
        
        prompt += f"Text to analyze:\n\n{chunk.content}\n\n"
        
        prompt += """Please extract any cryptocurrency-related events from this text. 
        
Remember:
- Brief descriptions must be 100-110 characters
- Include specific dates when available
- Focus only on crypto/blockchain events
- Provide complete and accurate full text for each event"""
        
        return prompt
    
    def _deduplicate_events(self, events: List[CryptoEvent]) -> List[CryptoEvent]:
        """Remove duplicate events based on date, brief_description, and source_url"""
        seen_events = set()
        unique_events = []
        
        for event in events:
            # Create a unique key for each event
            event_key = (event.date, event.brief_description, event.source_url)
            
            if event_key not in seen_events:
                seen_events.add(event_key)
                unique_events.append(event)
            else:
                logger.debug(f"Skipping duplicate event: {event.brief_description[:50]}...")
        
        if len(events) != len(unique_events):
            logger.info(f"Deduplicated {len(events)} events to {len(unique_events)} unique events")
        
        return unique_events