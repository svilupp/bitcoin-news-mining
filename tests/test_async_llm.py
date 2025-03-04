"""Tests for the async LLM functionality."""

import unittest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from src.llm import create_async_client, get_default_model
from src.llm.ranker import EventRanker, RankedEvents


@unittest.skip("For debugging only")
class TestLLMAsyncFunctionality(unittest.TestCase):
    """Test the async LLM functionality."""

    def test_client_creation(self):
        """Test creating clients for different providers."""
        # Test OpenAI client
        openai_client = create_async_client(api_key="test_key", provider="openai")
        self.assertEqual(openai_client.api_key, "test_key")
        self.assertIsNone(openai_client.base_url)

        # Test Google client
        google_client = create_async_client(api_key="test_key", provider="google")
        self.assertEqual(google_client.api_key, "test_key")
        self.assertEqual(
            google_client.base_url,
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        )

        # Test custom URL
        custom_client = create_async_client(
            api_key="test_key", provider="openai", base_url="https://example.com/v1"
        )
        self.assertEqual(custom_client.api_key, "test_key")
        self.assertEqual(custom_client.base_url, "https://example.com/v1")

    def test_default_models(self):
        """Test getting default models for different providers."""
        self.assertEqual(get_default_model("openai"), "gpt-4o-mini")
        self.assertEqual(get_default_model("google"), "gemini-1.5-pro")
        self.assertEqual(get_default_model("anthropic"), "claude-3-haiku-20240307")

        # Test unknown provider
        self.assertEqual(get_default_model("unknown"), "gpt-4o-mini")


class TestAsyncEventRanker(unittest.TestCase):
    """Test the async EventRanker class."""

    @patch("openai.AsyncOpenAI")
    def test_event_ranker_init(self, mock_openai):
        """Test initializing the EventRanker."""
        mock_client = AsyncMock()
        ranker = EventRanker(client=mock_client, model_name="test-model")

        self.assertEqual(ranker.client, mock_client)
        self.assertEqual(ranker.model, "test-model")

    @patch("openai.AsyncOpenAI")
    def test_rank_events_empty(self, mock_openai):
        """Test ranking empty events list."""
        mock_client = AsyncMock()
        ranker = EventRanker(client=mock_client, model_name="test-model")

        # Run in event loop
        result = asyncio.run(ranker.rank_events([], datetime.now()))

        self.assertEqual(result.rankings, [])
        self.assertEqual(result.reasoning, "No events to rank")

    @patch("openai.AsyncOpenAI")
    def test_rank_events_single(self, mock_openai):
        """Test ranking a single event."""
        mock_client = AsyncMock()
        ranker = EventRanker(client=mock_client, model_name="test-model")

        # Run in event loop
        result = asyncio.run(
            ranker.rank_events([{"title": "Test event"}], datetime.now())
        )

        self.assertEqual(result.rankings, [1])
        self.assertEqual(result.reasoning, "Only one event to rank")

    @patch("openai.AsyncOpenAI")
    def test_rank_events_multiple(self, mock_openai):
        """Test ranking multiple events."""
        # Setup mock response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.parsed = RankedEvents(
            rankings=[2, 1, 3],
            reasoning="Event 2 is most important, followed by Event 1, then Event 3",
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        # Setup AsyncMock for parse method
        mock_parse = AsyncMock(return_value=mock_response)
        mock_beta = MagicMock()
        mock_chat = MagicMock()
        mock_completions = MagicMock()
        mock_completions.parse = mock_parse
        mock_chat.completions = mock_completions
        mock_beta.chat = mock_chat

        # Setup client mock
        mock_client = MagicMock()
        mock_client.beta = mock_beta

        # Create ranker
        ranker = EventRanker(client=mock_client, model_name="test-model")

        # Test data
        events = [
            {"title": "Event 1", "description": "Description 1"},
            {"title": "Event 2", "description": "Description 2"},
            {"title": "Event 3", "description": "Description 3"},
        ]

        # Run in event loop
        result = asyncio.run(ranker.rank_events(events, datetime.now()))

        # Verify result
        self.assertEqual(result.rankings, [2, 1, 3])
        self.assertEqual(
            result.reasoning,
            "Event 2 is most important, followed by Event 1, then Event 3",
        )

        # Verify the call was made correctly
        mock_parse.assert_called_once()
        args, kwargs = mock_parse.call_args
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(len(kwargs["messages"]), 2)
        self.assertEqual(kwargs["response_format"], RankedEvents)


if __name__ == "__main__":
    unittest.main()
