import asyncio
from datetime import datetime
from typing import List, Optional
import logging
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .models import RawChunk, CryptoEvent, ExtractionConfig

logger = logging.getLogger(__name__)


class EventExtraction(BaseModel):
    """Model for OpenAI structured extraction output"""
    events: List[CryptoEvent] = Field(description="List of cryptocurrency events found in the text")


class OpenAIExtractor:
    """Extract cryptocurrency events using OpenAI's structured output"""
    
    def __init__(self, api_key: str, config: ExtractionConfig):
        self.client = AsyncOpenAI(api_key=api_key)
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
    async def extract_events_from_chunks(self, chunks: List[RawChunk]) -> List[CryptoEvent]:
        """Extract events from all chunks in parallel"""
        logger.info(f"Starting extraction from {len(chunks)} chunks")
        
        # Filter text chunks only for event extraction
        text_chunks = [chunk for chunk in chunks if chunk.content_type == 'text']
        
        # Create extraction tasks
        tasks = []
        for chunk in text_chunks:
            task = self._extract_from_single_chunk(chunk)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful extractions
        all_events = []
        successful_extractions = 0
        failed_extractions = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Extraction failed: {result}")
                failed_extractions += 1
            elif isinstance(result, list):
                all_events.extend(result)
                successful_extractions += 1
            else:
                failed_extractions += 1
        
        logger.info(f"Extraction complete: {successful_extractions} successful, {failed_extractions} failed")
        logger.info(f"Total events extracted: {len(all_events)}")
        
        return all_events
    
    async def _extract_from_single_chunk(self, chunk: RawChunk) -> List[CryptoEvent]:
        """Extract events from a single chunk with retry logic"""
        async with self.semaphore:
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
                    
                    logger.debug(f"Extracted {len(events)} events from chunk {chunk.chunk_index}")
                    return events
                    
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for chunk {chunk.chunk_index}: {e}")
                    if attempt == self.config.max_retries - 1:
                        logger.error(f"All attempts failed for chunk {chunk.chunk_index}")
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
                max_tokens=2000
            )
            
            # Extract the parsed response
            extraction_result = completion.choices[0].message.parsed
            
            if extraction_result and extraction_result.events:
                return extraction_result.events
            else:
                logger.debug(f"No events found in chunk {chunk.chunk_index}")
                return []
                
        except Exception as e:
            logger.error(f"OpenAI API call failed for chunk {chunk.chunk_index}: {e}")
            raise
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for event extraction"""
        return """You are a cryptocurrency news analyst tasked with extracting key cryptocurrency events from text content.

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
    
    async def test_extraction(self, sample_text: str) -> List[CryptoEvent]:
        """Test the extraction with a small sample text"""
        test_chunk = RawChunk(
            url="test://example.com",
            chunk_index=0,
            content_type="text",
            content=sample_text,
            section_heading="Test Section"
        )
        
        return await self._extract_from_single_chunk(test_chunk)