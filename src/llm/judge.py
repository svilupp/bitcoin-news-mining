"""LLM-based judge for evaluating search results."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from src.models import SearchResult

logger = logging.getLogger(__name__)


class CryptoEvent(BaseModel):
    """
    Structured representation of a Bitcoin or cryptocurrency historical event.

    Date is the date of the event, in the format "YYYY-MM-DD".
    Published date is the date of publication of the article/source, in the format "YYYY-MM-DD", provide if different from the date of event.

    The score field indicates the historical significance for Bitcoin and date confidence:

    5 - Extremely significant event with definitive date confirmation
       - Major historical milestones (e.g. Bitcoin genesis block)
       - Well-documented price records or market events
       - Multiple reliable sources confirm exact date

    4 - Moderately significant event with strong date confidence
       - Important technical developments or upgrades
       - Notable price movements or market activity
       - Date is well-documented

    3 - Minor crypto event with reasonable date confidence
       - Interesting but not groundbreaking developments
       - Moderate market impact or adoption milestones
       - Date is reported but may have some ambiguity

    2 - Minor crypto event with uncertain date
       - Small technical updates or announcements, mentions, not real events
       - Date is reported but poorly documented

    1 - Not relevant for Bitcoin or cryptocurrency
       - General news, not about Bitcoin or cryptocurrency
    """

    reasoning: str
    title: str
    description: str
    date: str
    published_date: Optional[str]
    score: int
    url: str  # Using str instead of HttpUrl for BSON compatibility


class CryptoEvents(BaseModel):
    """List of the most relevant Bitcoin or cryptocurrency historical events. The list must be sorted by relevance score and unique events only."""

    reasoning: str
    events: List[CryptoEvent] = Field(default_factory=list)


JUDGE_SYSTEM_PROMPT = """I am researching significant geopolitical and social Bitcoin or cryptocurrency events. 
You will be presented search results for events that should have occurred around {{formatted_date}}, but pay attention to the published dates and the dates in the content.
I am based in London, UK, so include 1-2 events that relate to the UK and Europe if they are relevant for our topic.

### Task
Carefully analyze if the search results specifically mentions Bitcoin or cryptocurrency events.
Select the top 5 most relevant unique events from the search results.
Only select events from the provided search results, do not make up events.
If you're not sure if the event is relevant or not sure about its date, return empty values.
Even if you do not provide any results, you must include a reasoning why you haven't included any of the provided search results. 

### Relevance criteria
1. The content must be about Bitcoin or cryptocurrency.
2. The event must have occurred around the following date: {{formatted_date}} and we prioritize events on this date.
3. The information should be factual and contain actual events, not just speculation or opinion.
4. The event must be significant and have a clear impact on Bitcoin or cryptocurrency. Include also social and cultural reference that suggest the rising significance and adoption of crypto assets.
5. Prioritize reputable sources, such as Wikipedia, bitcoinwiki.org, coindesk.com, cointelegraph.com, blockchain.com, bitcoin.com, etc.

### Output format
Return a JSON object with these fields:
- reasoning: explanation of why this event is significant
- title: clear, factual title, maximum 80 characters, be concise, use proper capitalization for Bitcoin, Ethereum, and other crypto names
- description: clear, concise description that captures the key information, maximum 300 characters
- date: date of the event, in the format "YYYY-MM-DD"
- published_date: published date of the event, in the format "YYYY-MM-DD", provide if different from the date of event
- score: (1-5) based on historical significance and date confidence
- url: source URL for the event
"""


class EventJudge:
    """OpenAI-based judge for evaluating search results."""

    def __init__(self, client: AsyncOpenAI, model_name: str = "gpt-4o-mini"):
        """Initialize OpenAI judge.

        Args:
            client: AsyncOpenAI client
            model_name: OpenAI model name to use
        """
        self.client = client
        self.model = model_name
        self.system_prompt = JUDGE_SYSTEM_PROMPT

    async def evaluate_relevance(
        self,
        search_result: SearchResult,
        query: str,
        query_date: datetime,
    ) -> CryptoEvents:
        """Evaluate if a search result is relevant for Bitcoin/crypto on a specific date.

        Args:
            search_result: Search result to evaluate
            query_date: Date the search is about

        Returns:
            JudgeResponse object with evaluation results
        """
        formatted_date = query_date.strftime("%B %d, %Y")

        combined_content = search_result.format_results_for_prompt()

        try:
            # Generate response
            logger.info(f"Evaluating relevance with OpenAI for date: {formatted_date}")

            completion = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt.replace(
                            "{{formatted_date}}", formatted_date
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Please evaluate search results of this query: {query} focused on {formatted_date}.\nSearch results:\n------\n{combined_content}\n------\n",
                    },
                ],
                response_format=CryptoEvents,
            )

            events = completion.choices[0].message.parsed
            return events

        except Exception as e:
            logger.error(f"OpenAI evaluation error: {str(e)}")
            # Return default response in case of error
            return CryptoEvents(
                reasoning=f"Error during evaluation: {str(e)}",
                events=[],
            )
