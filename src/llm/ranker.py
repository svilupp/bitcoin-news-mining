"""LLM-based ranker for reordering events by importance."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RankedEvents(BaseModel):
    """Ranking of events in order of importance for a given date."""

    reasoning: str
    ranking: List[int]


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
                f"Event {i+1}:\nTitle: {event.get('title', '')}\nDescription: {event.get('description', '')}\nURL: {event.get('url', '')}"
            )

        event_text = "\n--------------\n".join(event_list)

        # System prompt
        system_prompt = f"""
        Your task is to rank the following events from {formatted_date} by their historical significance and impact on the cryptocurrency world.
        I am based in London, UK, so include 1-2 events that relate to the UK and Europe if they are relevant for our topic.
        
        Consider these factors:
        - Long-term impact on Bitcoin/cryptocurrency
        - Market impact or price movements
        - Technical innovation or milestone
        - Regulatory significance
        - Mainstream adoption implications

        Prioritize reputable sources, such as Wikipedia, bitcoinwiki.org, coindesk.com, cointelegraph.com, blockchain.com, bitcoin.com, etc.
        Deduplicate the same events and return the IDs of the same events only once. Skip any duplicates.
        
        Output a list of IDs of the events in the order of importance, starting from the most significant (1) to the least significant ({len(events)}).
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
                        "content": f"Here are the events to rank:\n\n{event_text}\n\n\n\nPlease analyze each event and rank them from most significant (1) to least significant ({len(events)}).",
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

    def deduplicate_events(
        self, events: List[Any], rankings: RankedEvents
    ) -> List[Any]:
        """Deduplicate events based on rankings.

        If an event is missing from the rankings (likely a duplicate),
        it will be added to the end of the rankings.

        Args:
            events: List of events to deduplicate
            rankings: Rankings from the LLM

        Returns:
            List of deduplicated events
        """
        # Create a list to store the deduplicated events
        deduplicated_events = []

        # Create a set to track which events have been processed
        processed_indices = set()

        # First, add all events that have rankings
        for rank in rankings.ranking:
            # Adjust for 0-based indexing if the ranking is 1-based
            idx = rank - 1 if rank > 0 else rank

            # Ensure the index is valid
            if 0 <= idx < len(events):
                deduplicated_events.append(events[idx])
                processed_indices.add(idx)

        # Then add any events that were missed (likely duplicates)
        for i, event in enumerate(events):
            if i not in processed_indices:
                deduplicated_events.append(event)

        logger.info(
            f"Deduplicated {len(events)} events to {len(deduplicated_events)} unique events"
        )

        return deduplicated_events

    def apply_rankings(self, events: List[Any], rankings: RankedEvents) -> List[Any]:
        """Apply rankings to events.

        Args:
            events: List of events to apply rankings to
            rankings: Rankings from the LLM

        Returns:
            List of events with rankings applied
        """
        # First deduplicate events based on rankings
        deduplicated_events = self.deduplicate_events(events, rankings)

        # Add rank to each event based on its position (1-based)
        for i, event in enumerate(deduplicated_events):
            event.rank = i + 1  # 1-based ranking

        logger.info(f"Ranked {len(deduplicated_events)} events")
        return deduplicated_events
