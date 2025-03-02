"""LLM-based ranker for reordering events by importance."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RankedEvents(BaseModel):
    """Result of event ranking."""

    rankings: List[int]
    reasoning: str


class EventRanker:
    """OpenAI-based ranker for ordering events by importance."""

    def __init__(self, client: AsyncOpenAI, model_name: str = "gpt-4o-mini"):
        """Initialize OpenAI event ranker.

        Args:
            client: AsyncOpenAI client
            model_name: OpenAI model name to use
        """
        self.client = client
        self.model = model_name

    async def rank_events(
        self, events: List[Dict[str, Any]], event_date: datetime
    ) -> RankedEvents:
        """Rank events by their importance for Bitcoin/crypto history.

        Args:
            events: List of events to rank
            event_date: Date of the events

        Returns:
            RankedEvents with rankings and reasoning
        """
        if not events:
            return RankedEvents(rankings=[], reasoning="No events to rank")

        if len(events) == 1:
            return RankedEvents(rankings=[1], reasoning="Only one event to rank")

        formatted_date = event_date.strftime("%B %d, %Y")

        # Format events for the prompt
        event_list = []
        for i, event in enumerate(events):
            event_list.append(
                f"Event {i+1}:\nTitle: {event.get('title', '')}\nDescription: {event.get('description', '')}"
            )

        event_text = "\n\n".join(event_list)

        # System prompt
        system_prompt = f"""
        You are an expert historian of Bitcoin and cryptocurrency. Your task is to rank the following events from {formatted_date} by their historical significance and impact on the cryptocurrency world.
        
        Consider these factors:
        - Long-term impact on Bitcoin/cryptocurrency
        - Market impact or price movements
        - Technical innovation or milestone
        - Regulatory significance
        - Mainstream adoption implications
        """

        try:
            # Generate response using structured output
            logger.info(f"Ranking events with OpenAI for date: {formatted_date}")

            completion = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Here are the events to rank:\n\n{event_text}\n\nPlease analyze each event and rank them from most significant (1) to least significant ({len(events)}).",
                    },
                ],
                response_format=RankedEvents,
            )

            rankings = completion.choices[0].message.parsed
            return rankings

        except Exception as e:
            logger.error(f"OpenAI ranking error: {str(e)}")
            # Return default rankings in case of error
            return RankedEvents(
                rankings=list(range(1, len(events) + 1)),
                reasoning=f"Error during ranking: {str(e)}",
            )
