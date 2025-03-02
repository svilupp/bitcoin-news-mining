"""LLM-based judge for evaluating search results."""

import logging
from datetime import datetime
from typing import Any, Dict

from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class JudgeResponse(BaseModel):
    """Response from the LLM judge."""

    is_relevant: bool
    confidence: float  # 0.0 to 1.0
    reasoning: str


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

    async def evaluate_relevance(
        self, search_result: Dict[str, Any], query_date: datetime
    ) -> JudgeResponse:
        """Evaluate if a search result is relevant for Bitcoin/crypto on a specific date.

        Args:
            search_result: Search result to evaluate
            query_date: Date the search is about

        Returns:
            JudgeResponse object with evaluation results
        """
        formatted_date = query_date.strftime("%B %d, %Y")

        # System prompt
        system_prompt = f"""
        You are an expert judge evaluating if the following search result is relevant to Bitcoin or cryptocurrency events that occurred specifically on {formatted_date}.
        
        Carefully analyze if this result specifically mentions events that happened on {formatted_date}. 
        Consider these criteria:
        1. The content must be about Bitcoin or cryptocurrency.
        2. The event must have occurred on {formatted_date} specifically.
        3. The information should be factual and contain actual events, not just speculation or opinion.
        """

        try:
            # Generate response
            logger.info(f"Evaluating relevance with OpenAI for date: {formatted_date}")

            completion = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Please evaluate this search result:\nTitle: {search_result.get('title', 'No title')}\nURL: {search_result.get('url', 'No URL')}\nContent: {search_result.get('content', 'No content')}",
                    },
                ],
                response_format=JudgeResponse,
            )

            judge_response = completion.choices[0].message.parsed
            return judge_response

        except Exception as e:
            logger.error(f"OpenAI evaluation error: {str(e)}")
            # Return default response in case of error
            return JudgeResponse(
                is_relevant=False,
                confidence=0.0,
                reasoning=f"Error during evaluation: {str(e)}",
            )
