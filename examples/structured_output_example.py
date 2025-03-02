#!/usr/bin/env python
"""Example script demonstrating the use of structured outputs with both OpenAI and Google Gemini."""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from src.llm import create_async_client, get_default_model


class CalendarEvent(BaseModel):
    """Calendar event model for structured output demo."""

    name: str
    date: str
    participants: List[str]
    location: Optional[str] = None
    description: Optional[str] = Field(
        None, description="Detailed description of the event"
    )


async def process_with_provider(provider: str, api_key: str, text: str) -> None:
    """Process text with a specific provider.

    Args:
        provider: The provider to use (openai or google)
        api_key: API key for the provider
        text: Text to extract event from
    """
    # Create client and get default model for the provider
    client = create_async_client(api_key=api_key, provider=provider)
    model = get_default_model(provider)

    provider_name = provider.capitalize()
    print(f"\nProcessing with {provider_name} model ({model})...")

    try:
        completion = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": "Extract the event information."},
                {"role": "user", "content": text},
            ],
            response_format=CalendarEvent,
        )

        event = completion.choices[0].message.parsed
        print(f"\n{provider_name} Result:")
        print(f"Event: {event.name}")
        print(f"Date: {event.date}")
        print(f"Participants: {', '.join(event.participants)}")
        if event.location:
            print(f"Location: {event.location}")
        if event.description:
            print(f"Description: {event.description}")
    except Exception as e:
        print(f"{provider_name} processing error: {str(e)}")


async def main():
    """Demonstrate structured output parsing with both OpenAI and Google Gemini models."""
    # Get API keys from environment
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")

    if not openai_api_key or not google_api_key:
        print(
            "Error: Both OPENAI_API_KEY and GOOGLE_API_KEY must be set in environment"
        )
        sys.exit(1)

    # Example text to extract events from
    text = "Alice and Bob are going to a science fair on Friday. On Saturday, John, Mary, and Lisa will meet for a coding workshop at the public library."

    print("Demonstrating structured outputs with multiple providers...")

    # Process with both providers in parallel
    await asyncio.gather(
        process_with_provider("openai", openai_api_key, text),
        process_with_provider("google", google_api_key, text),
    )

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
