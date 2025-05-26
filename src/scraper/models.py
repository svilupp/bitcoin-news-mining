from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field


class CryptoEvent(BaseModel):
    """Model for extracted cryptocurrency events"""
    date: str = Field(description="Date in YYYY-MM-DD format")
    month: int = Field(description="Month number (1-12)")
    day: int = Field(description="Day of month (1-31)")
    year: int = Field(description="Full year (e.g., 2023)")
    full_text: str = Field(description="Complete event description")
    brief_description: str = Field(description="Brief description (100-110 characters)")
    source_url: str = Field(description="Source URL where event was found")
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
    chunk_index: int = Field(description="Index of the chunk this event was extracted from")
    section_heading: Optional[str] = Field(None, description="Section heading for context")


class RawChunk(BaseModel):
    """Model for raw content chunks before processing"""
    url: str = Field(description="Source URL")
    chunk_index: int = Field(description="Sequential index of this chunk")
    content_type: str = Field(description="Type of content: 'text' or 'image'")
    content: str = Field(description="Raw HTML/text content")
    image_path: Optional[str] = Field(None, description="Path to downloaded image file")
    section_heading: Optional[str] = Field(None, description="Section heading if available")
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens_estimate: Optional[int] = Field(None, description="Estimated token count for this chunk")


class ExtractionConfig(BaseModel):
    """Configuration for the extraction process"""
    max_concurrent_requests: int = Field(5, description="Maximum concurrent OpenAI requests")
    chunk_size_limit: int = Field(2000, description="Maximum tokens per chunk")
    include_images: bool = Field(False, description="Whether to process images")
    deduplicate_images: bool = Field(True, description="Whether to deduplicate images with different sizes")
    model_name: str = Field("gpt-4o-mini", description="OpenAI model to use")
    max_retries: int = Field(3, description="Maximum retries for failed requests")


class ExtractionResult(BaseModel):
    """Results from the extraction process"""
    events: list[CryptoEvent] = Field(description="Extracted cryptocurrency events")
    successful_extractions: int = Field(description="Number of chunks successfully processed")
    failed_extractions: int = Field(description="Number of chunks that failed processing")
    failure_types: Dict[str, int] = Field(default_factory=dict, description="Types of failures and their counts")


class ScrapingResult(BaseModel):
    """Results from a complete scraping operation"""
    url: str = Field(description="Scraped URL")
    total_chunks: int = Field(description="Total number of chunks processed")
    successful_extractions: int = Field(description="Number of successful event extractions")
    failed_extractions: int = Field(description="Number of failed extractions")
    events: list[CryptoEvent] = Field(description="Extracted cryptocurrency events")
    raw_chunks: list[RawChunk] = Field(description="Raw content chunks")
    processing_time: float = Field(description="Total processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now)