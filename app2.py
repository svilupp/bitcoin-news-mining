from fasthtml.common import *

# MonsterUI shadows fasthtml components with the same name
from monsterui.all import *

import os
import logging
from datetime import datetime
import dotenv

from src.llm.judge import JUDGE_SYSTEM_PROMPT
from src.pipeline import CryptoEventPipeline

# Get frankenui and tailwind headers via CDN using Theme.blue.headers()
hdrs = Theme.blue.headers()

# fast_app is shadowed by MonsterUI to make it default to no Pico, and add body classes
# needed for frankenui theme styling
app, rt = fast_app(hdrs=hdrs, live=True)

# Default values for the search form
current_query = "Bitcoin cryptocurrency news and developments"
current_date = datetime.now().strftime("%Y-%m-%d")
current_model = "gpt-4o-mini"
current_judge_prompt = JUDGE_SYSTEM_PROMPT


def Accordion(title, content):
    """Create an accordion component with a title and collapsible content"""
    return Details(
        Summary(
            title, cls="cursor-pointer p-3 bg-gray-100 hover:bg-gray-200 rounded-md"
        ),
        Div(content, cls="p-3 border-l border-gray-200 ml-2 mt-2"),
        cls="mb-4",
    )


def SearchCard(result):
    """Card component for displaying search results"""
    # Extract fields with defaults for optional fields
    title = result.get("title", "No Title")
    url = result.get("url", "#")
    date = result.get("date", "No Date")
    score = result.get("score", "N/A")
    description = result.get("description", "No description available")
    highlights = result.get("highlights", "")
    summary = result.get("summary", "")

    # Get domain for display
    display_url = url
    if url.startswith("http"):
        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            display_url = parsed_url.netloc
        except:
            pass

    # Full content to be hidden in accordion
    full_content = Div(
        P(description, cls=TextPresets.muted_sm),
    )

    return Card(
        # Key information at the top
        Div(
            A(display_url, href=url, target="_blank", cls=ButtonT.link),
            P(f"Published: {date} | Score: {score}", cls=TextPresets.muted_sm),
            cls="mb-2",
        ),
        # Title
        H4(title, cls="mt-2"),
        # Show highlights and summary if available
        Div(
            (
                P(f"Highlights: {highlights}", cls=TextPresets.muted_sm)
                if highlights
                else ""
            ),
            P(f"Summary: {summary}", cls=TextPresets.muted_sm) if summary else "",
        ),
        # Full content in accordion
        Accordion("Show Details", full_content),
        Button(
            "View Details",
            cls=(ButtonT.primary, "mt-2"),
        ),
    )


def EventCard(event):
    """Card component for displaying relevant events"""
    # Extract fields with defaults
    title = event.get("title", "No Title")
    url = event.get("url", "#")
    date = event.get("date", "No Date")
    description = event.get("description", "No description available")
    relevance_score = event.get("relevance_score", "N/A")

    # Get domain for display
    display_url = url
    if url.startswith("http"):
        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            display_url = parsed_url.netloc
        except:
            pass

    # Full content to be hidden in accordion
    full_content = Div(
        P(description, cls=TextPresets.muted_sm),
    )

    return Card(
        # Key information at the top
        Div(
            A(display_url, href=url, target="_blank", cls=ButtonT.link),
            P(f"Date: {date} | Relevance: {relevance_score}", cls=TextPresets.muted_sm),
            cls="mb-2",
        ),
        # Title
        H4(title, cls="mt-2"),
        # Full content in accordion
        Accordion("Show Details", full_content),
        Button(
            "View Event",
            cls=(ButtonT.primary, "mt-2"),
        ),
    )


def search_form():
    """Create a responsive search form with query, date, and model selection"""
    models = ["gpt-4o-mini", "gpt-4o"]

    # Advanced settings content
    advanced_settings = DivVStacked(
        # API Keys section
        DivVStacked(
            H4("API Keys", cls="text-lg font-bold"),
            DivHStacked(
                LabelInput(
                    "OpenAI API Key",
                    id="openai_key",
                    name="openai_key",
                    type="password",
                    placeholder="Enter your OpenAI API key...",
                ),
                LabelInput(
                    "EXA API Key",
                    id="exa_key",
                    name="exa_key",
                    type="password",
                    placeholder="Enter your EXA API key...",
                ),
            ),
        ),
        # Judge Prompt section - use a container to ensure full width
        Container(
            H4("Judge Prompt", cls="text-lg font-bold mt-4"),
            # Use Label and Textarea separately for more control
            Label("Custom Judge Prompt", for_="judge-prompt"),
            # Create a textarea with more rows and full width
            Textarea(
                id="judge-prompt",
                name="judge_prompt",
                rows=20,  # Increased rows for more height
                placeholder="Enter your judge prompt here...",
                cls="w-full",  # Full width
            )(
                current_judge_prompt
            ),  # Set content this way
            cls="w-full",
        ),
    )

    # Container for the entire form - use Container for full width
    return Container(
        DivCentered(
            H3("Bitcoin News Search", cls="text-2xl font-bold"),
            P("Search for Bitcoin news and related events", cls=TextPresets.muted_sm),
        ),
        Form(
            id="search-form",
            cls="space-y-4",
            hx_post="/search_results",
            hx_target="#results",
            hx_indicator="#search-indicator",
        )(
            # Query input on its own line
            LabelInput(
                "Search Query",
                id="query",
                name="query",
                placeholder="Enter search terms...",
                value=current_query,
                input_cls="w-full",  # Make input full width
            ),
            # Date and Model inputs side by side
            DivLAligned(
                LabelInput(
                    "Date",
                    id="date",
                    name="date",
                    type="date",
                    placeholder="YYYY-MM-DD",
                    value=current_date,
                ),
                LabelSelect(
                    *[
                        Option(model, value=model, selected=(model == current_model))
                        for model in models
                    ],
                    label="Model",
                    id="model",
                    name="model",
                ),
                cols=1,
                cols_md=2,  # Two columns on medium screens and above
            ),
            # Advanced Settings in accordion
            Accordion("Advanced Settings", advanced_settings),
            # Search button centered
            DivCentered(
                Button("Search", cls=ButtonT.primary, id="search-btn", type="submit"),
                # Loading indicator
                Div(id="search-indicator", style="display:none")(
                    Span("Searching...", cls=TextPresets.muted_sm),
                    Span("⟳", cls="animate-spin ml-2"),
                ),
            ),
        ),
        # Results section - initially empty, will be populated after search
        Div(id="results", cls="mt-8"),
    )


# Mock search results data
mock_search_results = [
    {
        "title": "Bitcoin Price Surge",
        "url": "https://example.com/bitcoin-price-surge",
        "date": "2023-05-15",
        "score": "0.92",
        "description": "Bitcoin price reaches new heights as institutional adoption increases. Analysts predict continued growth in the coming months.",
        "highlights": "Price surge, institutional adoption, growth predictions",
        "summary": "Bitcoin prices have surged to new heights due to increased institutional adoption and positive market sentiment.",
    },
    {
        "title": "Crypto Regulations",
        "url": "https://example.com/crypto-regulations",
        "date": "2023-04-22",
        "score": "0.85",
        "description": "New regulations impact Bitcoin market as governments worldwide establish frameworks. Industry leaders respond with mixed reactions.",
        "highlights": "New regulations, government frameworks, industry response",
        "summary": "Governments worldwide are establishing new regulatory frameworks for cryptocurrencies, with mixed reactions from industry leaders.",
    },
    {
        "title": "Mining Difficulty Increases",
        "url": "https://example.com/mining-difficulty",
        "date": "2023-06-01",
        "score": "0.78",
        "description": "Bitcoin mining difficulty reaches all-time high as more miners join the network. Energy consumption concerns grow among environmental advocates.",
        "highlights": "Mining difficulty, network growth, energy concerns",
        "summary": "Bitcoin mining difficulty has reached an all-time high, raising concerns about energy consumption and environmental impact.",
    },
]

# Mock event data
mock_events = [
    {
        "title": "Bitcoin Conference",
        "url": "https://example.com/bitcoin-conference",
        "date": "2023-06-10",
        "description": "Annual Bitcoin conference in Miami featuring keynote speakers and workshops. Industry leaders will discuss the future of cryptocurrency.",
        "relevance_score": "0.95",
    },
    {
        "title": "Halving Event",
        "url": "https://example.com/halving-event",
        "date": "2023-05-20",
        "description": "Bitcoin halving scheduled for next month, expected to impact price and mining profitability. Experts analyze potential market effects.",
        "relevance_score": "0.89",
    },
    {
        "title": "Developer Summit",
        "url": "https://example.com/developer-summit",
        "date": "2023-07-05",
        "description": "Bitcoin core developers meeting to discuss protocol improvements and future roadmap. Technical discussions will focus on scalability and security.",
        "relevance_score": "0.82",
    },
]


@rt("/search_results", methods=["POST"])
def search_results():
    """Mock endpoint to handle search form submission and return results"""
    # In a real application, you would process the form data and perform a search
    # Here we just return mock data
    return Grid(
        # Left column: Search Results
        Div(
            H3("Search Results", cls="text-xl font-bold mb-4"),
            Div(id="search-results", cls="space-y-4")(
                *[SearchCard(result) for result in mock_search_results]
            ),
        ),
        # Right column: Relevant Events
        Div(
            H3("Relevant Events", cls="text-xl font-bold mb-4"),
            Div(id="event-results", cls="space-y-4")(
                *[EventCard(event) for event in mock_events]
            ),
        ),
        cols_lg=2,
        cls="gap-6",
    )


@rt("/search")
def search_page():
    """Render the search page with the search form"""
    return Titled(
        "Bitcoin News Search",
        Div(
            search_form(),
            # Add JavaScript to handle the loading indicator
            Script(
                """
                document.addEventListener('htmx:beforeRequest', function(event) {
                    if (event.detail.elt.id === 'search-form') {
                        document.getElementById('search-indicator').style.display = 'block';
                    }
                });
                
                document.addEventListener('htmx:afterRequest', function(event) {
                    if (event.detail.elt.id === 'search-form') {
                        document.getElementById('search-indicator').style.display = 'none';
                    }
                });
            """
            ),
        ),
    )


@rt("/")
def index():
    """Main page that redirects to the search page"""
    return search_page()


# Use a different port
serve(port=5003)
