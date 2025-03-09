from fasthtml.common import *
from fasthtml.components import Script

# MonsterUI shadows fasthtml components with the same name
from monsterui.all import *

import os
import logging
from datetime import datetime
import dotenv
import json
from pathlib import Path
from starlette.requests import Request

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


def BaseCard(
    title,
    url,
    date,
    score_or_relevance,
    score_label,
    description,
    highlights=None,
    summary=None,
):
    """Base card component for displaying search results or events"""
    # Get domain for display
    display_url = url
    if url.startswith("http"):
        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            display_url = "URL: " + parsed_url.netloc
        except:
            pass

    # Full content to be hidden in accordion
    full_content = Div(
        P(description, cls=TextPresets.muted_sm),
    )

    # Create optional content elements for highlights and summary
    optional_elements = []
    if highlights:
        optional_elements.append(
            P(f"Highlights: {highlights}", cls=TextPresets.muted_sm)
        )
    if summary:
        optional_elements.append(P(f"Summary: {summary}", cls=TextPresets.muted_sm))

    # Create optional content div only if there are elements to show
    optional_content = Div(*optional_elements) if optional_elements else None

    card_elements = [
        # Title
        H4(title, cls="mt-2"),
        # Key information at the top
        Div(
            A(display_url, href=url, target="_blank", cls=ButtonT.link),
            P(
                f"{date} | {score_label}: {score_or_relevance}",
                cls=TextPresets.muted_sm,
            ),
            cls="mb-2",
        ),
        # Full content in accordion
        Accordion("Show Details", full_content),
    ]

    # Add optional content if it exists
    if optional_content:
        # Insert optional content before the accordion (at index 2)
        card_elements.insert(2, optional_content)

    return Card(*card_elements)


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

    card = BaseCard(
        title=title,
        url=url,
        date=f"Published: {date}",
        score_or_relevance=score,
        score_label="Score",
        description=description,
        highlights=highlights,
        summary=summary,
    )

    return card


def EventCard(event):
    """Card component for displaying relevant events"""
    # Extract fields with defaults
    title = event.get("title", "No Title")
    url = event.get("url", "#")
    date = event.get("date", "No Date")
    description = event.get("description", "No description available")
    relevance_score = event.get("relevance_score", "N/A")

    card = BaseCard(
        title=title,
        url=url,
        date=f"Date: {date}",
        score_or_relevance=relevance_score,
        score_label="Relevance",
        description=description,
    )

    return card


def search_form():
    """Create a responsive search form with query, date, and model selection"""
    models = ["gpt-4o-mini", "gpt-4o"]

    # Get the current judge prompt
    current_judge_prompt_value = current_judge_prompt

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
            LabelTextArea(
                "Custom Judge Prompt",
                id="judge-prompt",
                name="judge_prompt",
                rows=20,  # Increased rows for more height
                placeholder="Enter your judge prompt here...",
                cls="w-full",  # Full width
                value=current_judge_prompt_value,
            ),
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
                DivHStacked(
                    Button(
                        "Search", cls=ButtonT.primary, id="search-btn", type="submit"
                    ),
                    Button(
                        "Save Feedback",
                        cls=(ButtonT.secondary, "ml-2"),
                        data_uk_toggle="target: #feedback-modal",
                        type="button",
                    ),
                ),
                # Loading indicator
                Div(id="search-indicator", style="display:none")(
                    Span("Searching...", cls=TextPresets.muted_sm),
                    Span("⟳", cls="animate-spin ml-2"),
                ),
            ),
        ),
        # Results section - initially empty, will be populated after search
        Div(id="results", cls="mt-8"),
        # Feedback Modal
        Modal(
            ModalTitle("Save Your Feedback"),
            P(
                "Please provide your feedback on the search results and ranked events. This will auto-log the search form configuration.",
                cls=TextPresets.muted_sm,
            ),
            Form(
                id="feedback-form",
                hx_post="/save_feedback",
                hx_target="#feedback-result",
                hx_trigger="submit",
                hx_on_after_request="UIkit.modal('#feedback-modal').hide();",
            )(
                # Hidden fields to capture current search parameters
                Input(
                    type="hidden", id="query-hidden", name="query", value=current_query
                ),
                Input(type="hidden", id="date-hidden", name="date", value=current_date),
                Input(
                    type="hidden", id="model-hidden", name="model", value=current_model
                ),
                # Hidden field for judge prompt
                Input(
                    type="hidden",
                    id="judge-prompt-hidden",
                    name="judge_prompt",
                    value=current_judge_prompt,
                ),
                # Feedback textarea
                Textarea(
                    id="feedback-text",
                    name="feedback_text",
                    rows=5,
                    placeholder="Enter your feedback here...",
                    cls="w-full mt-2",
                ),
                # Footer with buttons
                Div(
                    Button(
                        "Save",
                        type="submit",
                        cls=ButtonT.primary,
                        onclick="setTimeout(function() { UIkit.modal('#feedback-modal').hide(); }, 300);",
                    ),
                    ModalCloseButton("Cancel", cls=ButtonT.secondary),
                    cls="flex justify-between mt-4",
                ),
            ),
            id="feedback-modal",
        ),
        # Feedback result notification (hidden initially)
        Div(id="feedback-result", cls="mt-4"),
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
async def search_results(request: Request):
    """Mock endpoint to handle search form submission and return results"""
    # Get form data
    form_data = await request.form()
    query = form_data.get("query", current_query)
    date = form_data.get("date", current_date)
    model = form_data.get("model", current_model)

    # Get the judge prompt from the form if it exists, otherwise use empty string
    judge_prompt = form_data.get("judge_prompt", JUDGE_SYSTEM_PROMPT)
    # In a real application, you would process the form data and perform a search
    # Here we just return mock data with JavaScript to update hidden fields
    return Div(
        # JavaScript to update hidden fields in the feedback form
        Script(
            f"""
            document.addEventListener('DOMContentLoaded', function() {{
                document.getElementById('query-hidden').value = "{query}";
                document.getElementById('date-hidden').value = "{date}";
                document.getElementById('model-hidden').value = "{model}";
                document.getElementById('judge-prompt-hidden').value = `{judge_prompt}`;
            }});
        """
        ),
        # Search results grid
        Grid(
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
        ),
    )


@rt("/search")
def search_page():
    """Render the search page with the search form"""
    return Titled(
        "Bitcoin News Search",
        Div(
            search_form(),
            # Add JavaScript to handle the loading indicator and modal closing
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
                    
                    // Close feedback modal after successful form submission
                    if (event.detail.elt.id === 'feedback-form' && event.detail.successful) {
                        if (typeof UIkit !== 'undefined' && UIkit.modal) {
                            UIkit.modal('#feedback-modal').hide();
                        }
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


@rt("/save_feedback", methods=["POST"])
async def save_feedback(request: Request):
    """Save user feedback to a JSON file"""
    try:
        # Get form data
        form_data = await request.form()
        feedback_text = form_data.get("feedback_text", "")
        query = form_data.get("query", current_query)
        date = form_data.get("date", current_date)
        model = form_data.get("model", current_model)
        judge_prompt = form_data.get("judge_prompt", "")
        # Strip special characters, keep only letters, numbers and basic punctuation
        judge_prompt_clean = "".join(
            c for c in judge_prompt if c.isalnum() or c in ".,?!;:()[]{}\"' "
        )
        default_prompt_clean = "".join(
            c for c in JUDGE_SYSTEM_PROMPT if c.isalnum() or c in ".,?!;:()[]{}\"' "
        )
        if judge_prompt_clean.lower() == default_prompt_clean.lower():
            judge_prompt = ""

        # Count results and events (if available)
        search_results_count = len(mock_search_results)
        events_count = len(mock_events)

        # Create feedback data structure
        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "date": date,
            "model": model,
            "judge_prompt": judge_prompt,
            "search_results_count": search_results_count,
            "events_count": events_count,
            "feedback": feedback_text,
        }

        # Ensure the feedback file exists
        feedback_file = Path("feedback.json")

        # Load existing data or create new list
        if feedback_file.exists():
            try:
                with open(feedback_file, "r") as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = []
            except json.JSONDecodeError:
                # If file exists but is not valid JSON, start fresh
                existing_data = []
        else:
            existing_data = []

        # Append new feedback
        existing_data.append(feedback_data)

        # Write back to file
        with open(feedback_file, "w") as f:
            json.dump(existing_data, f, indent=2)

        # Return success message with JavaScript to close the modal
        return Div(
            P("Feedback saved successfully!", cls="text-success font-bold"),
            cls="p-4 bg-success-light rounded",
        )

    except Exception as e:
        logging.error(f"Error saving feedback: {str(e)}")
        return Div(
            P(f"Error saving feedback: {str(e)}", cls="text-error font-bold"),
            cls="p-4 bg-error-light rounded",
        )


# Use a different port
serve(port=5000)
