"""LLM-based processor for formatting and cleaning event data."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProcessedEvent(BaseModel):
    """Processed event data."""

    title: str
    description: str
    date: datetime
    source_url: str
    source_title: Optional[str] = None


class EventProcessor:
    """OpenAI-based processor for formatting event data."""

    def __init__(self, client: AsyncOpenAI, model_name: str = "gpt-4o-mini"):
        """Initialize OpenAI event processor.

        Args:
            client: AsyncOpenAI client
            model_name: OpenAI model name to use
        """
        self.client = client
        self.model = model_name

    async def process_event(
        self, event_data: Dict[str, Any], event_date: datetime
    ) -> ProcessedEvent:
        """Process event data to clean and format title and description.

        Args:
            event_data: Raw event data to process
            event_date: Date the event occurred

        Returns:
            ProcessedEvent object with processed data
        """
        formatted_date = event_date.strftime("%B %d, %Y")

        # Extract content from event_data
        title = event_data.get("title", "")
        content = event_data.get("content", "")
        url = event_data.get("url", "")

        # Define a Pydantic model for the structured output
        class FormattedContent(BaseModel):
            title: str
            description: str

        # System prompt
        system_prompt = f"""
        You are an expert editor formatting Bitcoin and cryptocurrency event information for a historical database.
        
        Guidelines:
        - Focus only on Bitcoin/crypto events that happened on {formatted_date}
        - Remove any speculation, opinion, or irrelevant information
        - Maintain factual accuracy
        - Format dates consistently as Month Day, Year (e.g., January 3, 2009)
        - Use proper capitalization for Bitcoin, Ethereum, and other crypto names
        - Create a clear, factual title (max 100 characters)
        - Write a concise description (100-200 words) that captures the key information
        """

        try:
            # Generate response
            logger.info(f"Processing event data with OpenAI for date: {formatted_date}")

            completion = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Here is information about an event that occurred on {formatted_date}:\nTitle: {title}\nContent: {content}\nURL: {url}\n\nPlease format this into a clean, concise entry for our database.",
                    },
                ],
                response_format=FormattedContent,
            )

            processed_data = completion.choices[0].message.parsed

            # Create processed event object
            processed_event = ProcessedEvent(
                title=processed_data.title,
                description=processed_data.description,
                date=event_date,
                source_url=url,
                source_title=title,
            )

            return processed_event

        except Exception as e:
            logger.error(f"OpenAI processing error: {str(e)}")
            # Return default processed event in case of error
            return ProcessedEvent(
                title=title,
                description=content[:500] + "...",
                date=event_date,
                source_url=url,
                source_title=title,
            )
