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

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get frankenui and tailwind headers via CDN using Theme.blue.headers()
hdrs = Theme.blue.headers()

# fast_app is shadowed by MonsterUI to make it default to no Pico, and add body classes
# needed for frankenui theme styling
app, rt = fast_app(hdrs=hdrs, live=False)

# Default values for the search form
current_query = "Bitcoin cryptocurrency news and developments"
current_date = datetime.now().strftime("%Y-%m-%d")
current_model = "gpt-4o-mini"
current_judge_prompt = JUDGE_SYSTEM_PROMPT

# Global variables to store the last search results
last_search_result = None
last_events = None

# Global variable to store the pipeline instance
pipeline = None


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
    relevance_reasoning=None,
    show_description_in_card=True,
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

    # Content for accordion
    accordion_elements = []

    # Add relevance reasoning to accordion if available
    if relevance_reasoning:
        accordion_elements.append(
            P(f"Relevance Reasoning: {relevance_reasoning}", cls=TextPresets.muted_sm)
        )

    # Add full description to accordion if it's not shown in the card
    # or if it's a search result (where we want to show it in both places)
    accordion_elements.append(
        P(f"Full Content: {description}", cls=TextPresets.muted_sm)
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
    ]

    # Add description to card if show_description_in_card is True
    if show_description_in_card:
        card_elements.append(P(description, cls=TextPresets.muted_sm))

    # Add optional content if it exists
    if optional_content:
        card_elements.append(optional_content)

    # Add accordion with additional details
    accordion_content = Div(*accordion_elements)
    card_elements.append(Accordion("Show Full Content", accordion_content))

    return Card(*card_elements)


def SearchCard(result):
    """Card component for displaying search results"""
    # All results from the pipeline's SearchResult.results are dictionaries
    title = result.get("title", "No Title")
    url = result.get("url", "#")

    # Parse and format the date
    date = result.get("published_date", "No Date")
    if isinstance(date, datetime):
        date = date.strftime("%Y-%m-%d")
    elif isinstance(date, str) and date:
        try:

            parsed_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
            date = parsed_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            # Keep the original string if parsing fails
            pass

    # Format score to 3 decimal places
    score = result.get("score", "N/A")
    if isinstance(score, (float, int)):
        score = f"{score:.3f}"

    # Get full content for the accordion
    description = result.get("content", "No description available")

    # Join highlights if it's a list
    highlights = result.get("highlights", "")
    if isinstance(highlights, list):
        highlights = "; ".join(highlights)

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
        show_description_in_card=False,  # Don't show description in card for search results
    )

    return card


def EventCard(event):
    """Card component for displaying relevant events"""
    # Events from the pipeline are Event objects
    title = event.title
    url = event.source_url
    event_date = event.event_date
    if isinstance(event_date, datetime):
        date = event_date.strftime("%Y-%m-%d")
    else:
        date = "No Date"
    description = event.description
    relevance_score = event.relevance_score
    if isinstance(relevance_score, float):
        relevance_score = f"{relevance_score:.3f}"

    # Get relevance reasoning for the accordion
    relevance_reasoning = event.relevance_reasoning

    card = BaseCard(
        title=title,
        url=url,
        date=f"Date: {date}",
        score_or_relevance=relevance_score,
        score_label="Relevance",
        description=description,
        relevance_reasoning=relevance_reasoning,
        show_description_in_card=True,  # Show description in card for ranked results
    )

    return card


def search_form():
    """Create a responsive search form with query, date, and model selection"""
    models = ["gpt-4o-mini", "gpt-4o"]  # , "gemini-2.0-flash"

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
                    id="openai_api_key",
                    name="openai_api_key",
                    type="password",
                    placeholder="Enter your OpenAI API key...",
                ),
                LabelInput(
                    "EXA API Key",
                    id="exa_api_key",
                    name="exa_api_key",
                    type="password",
                    placeholder="Enter your EXA API key...",
                ),
                LabelInput(
                    "Google API Key",
                    id="google_api_key",
                    name="google_api_key",
                    type="password",
                    placeholder="Enter your Google API key...",
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
            P("Search for Bitcoin news and related events", cls="text-2xl font-bold"),
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


def initialize_pipeline():
    """Initialize the CryptoEventPipeline."""
    # Get API keys from environment variables
    exa_api_key = os.environ.get("EXA_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")

    # Check if API keys are available
    if not exa_api_key or not openai_api_key:
        logger.error(
            "Missing required API keys. Set EXA_API_KEY and OPENAI_API_KEY environment variables."
        )
        raise ValueError("Missing API keys")

    # Initialize pipeline
    return CryptoEventPipeline(
        exa_api_key=exa_api_key,
        openai_api_key=openai_api_key,
        load_db=False,
    )


async def run_search(
    query,
    date_str,
    exa_api_key=None,
):
    """Run just the search part of the pipeline and return search results."""
    global pipeline, current_query, current_date

    # Parse date
    if date_str:
        try:
            # Parse YYYY-MM-DD format
            year, month, day = date_str.split("-")
            date = datetime(int(year), int(month), int(day))
        except (ValueError, IndexError):
            return {"error": "Invalid date format. Use YYYY-MM-DD."}
    else:
        date = datetime.now()

    # Update global state
    current_query = query
    current_date = date_str

    # Initialize pipeline if not already done
    if pipeline is None:
        try:
            pipeline = initialize_pipeline()
        except ValueError as e:
            logger.error(f"Pipeline initialization error: {str(e)}")
            return {"error": str(e)}

    # Override API key if provided
    if exa_api_key:
        pipeline.search_client.api_key = exa_api_key

    try:
        # Run just the search part of the pipeline
        logger.info(f"Running search for query: {query}, date: {date_str}")
        search_result, formatted_query = await pipeline._perform_search(
            date=date,
            base_query=query,
            full_month=False,
            max_results=15,
        )

        return {
            "search_result": search_result,
            "formatted_query": formatted_query,
            "date": date,
        }
    except Exception as e:
        logger.error(f"Error running search: {str(e)}")
        return {"error": str(e)}


async def run_ranking(
    search_result,
    formatted_query,
    date,
    openai_api_key=None,
    model="gpt-4o-mini",
    judge_prompt=None,
):
    """Run just the ranking part of the pipeline and return ranked events."""
    global pipeline, current_model, current_judge_prompt

    # Update global state
    current_model = model
    if judge_prompt:
        current_judge_prompt = judge_prompt

    # Initialize pipeline if not already done
    if pipeline is None:
        try:
            pipeline = initialize_pipeline()
        except ValueError as e:
            logger.error(f"Pipeline initialization error: {str(e)}")
            return {"error": str(e)}

    # Override API key if provided
    if openai_api_key:
        pipeline.openai_client.api_key = openai_api_key

    if model == "gemini-2.0-flash":
        logger.info(f"Using Gemini API key -- {openai_api_key}")
        pipeline.openai_client.base_url = (
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    else:
        logger.info(f"Using OpenAI API key -- {openai_api_key}")
        pipeline.openai_client.base_url = "https://api.openai.com/v1"

    try:
        # Run the ranking part of the pipeline
        logger.info(f"Running ranking with model: {model}")
        events = await pipeline._rank_search_results(
            search_result=search_result,
            formatted_query=formatted_query,
            date=date,
            judge_system_prompt=judge_prompt or current_judge_prompt,
            judge_model=model,
        )

        return {
            "events": events,
        }
    except Exception as e:
        logger.error(f"Error running ranking: {str(e)}")
        return {"error": str(e)}


async def run_pipeline(
    query,
    date_str,
    openai_api_key=None,
    exa_api_key=None,
    model="gpt-4o-mini",
    judge_prompt=None,
):
    """Run the full pipeline (search and judge) and return results."""
    # Run search
    search_result = await run_search(query, date_str, exa_api_key)
    if "error" in search_result:
        return search_result

    # Run ranking
    ranking_result = await run_ranking(
        search_result["search_result"],
        search_result["formatted_query"],
        search_result["date"],
        openai_api_key,
        model,
        judge_prompt,
    )
    if "error" in ranking_result:
        return ranking_result

    # Combine results
    return {
        "search_result": search_result["search_result"],
        "events": ranking_result["events"],
    }


@rt("/search_results", methods=["POST"])
async def search_results(request: Request):
    """Handle search form submission and return results from the crypto event pipeline"""
    global last_search_result, last_events

    # Get form data
    form_data = await request.form()
    query = form_data.get("query", current_query)
    date = form_data.get("date", current_date)
    model = form_data.get("model", current_model)
    judge_prompt = form_data.get("judge_prompt", JUDGE_SYSTEM_PROMPT)

    # Get API keys if provided
    openai_api_key = form_data.get("openai_api_key", "").strip()
    exa_api_key = form_data.get("exa_api_key", "").strip()
    google_api_key = form_data.get("google_api_key", "").strip()

    # Use provided API keys if not empty
    openai_key = openai_api_key if openai_api_key else None
    exa_key = exa_api_key if exa_api_key else None
    google_key = google_api_key if google_api_key else None
    judge_prompt_val = judge_prompt if judge_prompt.strip() else None

    # First, run the search part
    search_result = await run_search(query, date, exa_key)
    if "error" in search_result:
        return Alert(search_result["error"], cls=AlertT.error)

    # Display search results with loading indicator for ranking
    search_results_div = Div(
        H3("Search Results", cls="text-xl font-bold mb-4"),
        Div(id="search-results", cls="space-y-4")(
            *[SearchCard(result) for result in search_result["search_result"].results]
        ),
    )

    # Now run the ranking part
    api_key = openai_key if model == "gpt-4o-mini" or model == "gpt-4o" else google_key
    ranking_result = await run_ranking(
        search_result["search_result"],
        search_result["formatted_query"],
        search_result["date"],
        api_key,
        model,
        judge_prompt_val,
    )
    if "error" in ranking_result:
        return Div(
            search_results_div,
            Alert(ranking_result["error"], cls=AlertT.error),
        )

    # Extract events
    events = ranking_result["events"]

    # Store the results for later use
    last_search_result = search_result["search_result"]
    last_events = events

    # Get reasoning from the first event if available
    reasoning_summary = ""
    if events and events[0].relevance_reasoning:
        reasoning_summary = Div(
            H3("Ranking Reasoning", cls="text-xl font-bold mb-4"),
            P(events[0].relevance_reasoning, cls=TextPresets.muted_sm),
            cls="mb-4 p-4 bg-gray-50 rounded-lg",
        )

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
        # Display reasoning summary if available
        reasoning_summary,
        # Search results grid
        Grid(
            # Left column: Search Results
            search_results_div,
            # Right column: Relevant Events
            Div(
                H3("Relevant Events", cls="text-xl font-bold mb-4"),
                Div(id="event-results", cls="space-y-4")(
                    *[EventCard(event) for event in events]
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
    global last_search_result, last_events

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
        search_results_count = 0
        events_count = 0

        if last_search_result and hasattr(last_search_result, "results"):
            search_results_count = len(last_search_result.results)

        if last_events:
            events_count = len(last_events)

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
        feedback_file = Path(f"feedback_{datetime.now().strftime('%Y-%m-%d')}.json")

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
serve()
