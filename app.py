"""Interactive application for Bitcoin news mining query discovery."""

from fasthtml.common import *
from monsterui.all import *
import os
import logging
from datetime import datetime
import dotenv

from src.llm.judge import JUDGE_SYSTEM_PROMPT
from src.pipeline import CryptoEventPipeline

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the FastHTML app
hdrs = Theme.blue.headers(
    shadows=ThemeShadows.md,
)
# app, rt = fast_app(headers=hdrs)
app, rt = fast_app()

# Global variables to store state
pipeline = None
current_query = "Bitcoin cryptocurrency news and developments"
current_date = datetime.now()
current_model = "gpt-4o-mini"
current_judge_prompt = JUDGE_SYSTEM_PROMPT


def Accordion(title, content):
    return Details(
        Summary(
            title, cls="cursor-pointer p-3 bg-gray-100 hover:bg-gray-200 rounded-md"
        ),
        Div(content, cls="p-3 border-l border-gray-200 ml-2 mt-2"),
        cls="mb-4",
    )


def DateTag(date_str, prefix="Date:"):
    """Create a date tag with prefix"""
    # Handle None case
    if date_str is None:
        return Label(f"{prefix} Unknown")

    # Handle datetime object
    if isinstance(date_str, datetime):
        formatted_date = date_str.strftime("%Y-%m-%d")
        return Label(f"{prefix} {formatted_date}")

    # Handle string type
    if isinstance(date_str, str):
        if date_str.lower() == "unknown":
            return Label(f"{prefix} Unknown")

        # Try to parse and format the date as YYYY-MM-DD
        try:
            # Handle ISO format dates
            if "T" in date_str:
                date_str = date_str.split("T")[0]

            # Check if date is already in YYYY-MM-DD format
            if len(date_str) >= 10 and date_str[4:5] == "-" and date_str[7:8] == "-":
                formatted_date = date_str[:10]  # Extract just YYYY-MM-DD portion
            else:
                # Try different parsing approaches
                try:
                    # Try direct parsing
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    formatted_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    # Fallback parsing
                    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y"]
                    for fmt in formats:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            formatted_date = dt.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format works, use as is
                        formatted_date = date_str
        except Exception:
            # If any parsing error, use as is
            formatted_date = date_str

        return Label(f"{prefix} {formatted_date}")

    # Handle any other type by converting to string
    return Label(f"{prefix} {str(date_str)}")


def RelevanceBadge(score):
    """Create a relevance badge on scale 1-5"""
    # Normalize score to 1-5 scale if needed
    if isinstance(score, (int, float)) and score > 5:
        normalized_score = min(5, max(1, round(score / 2)))
    else:
        try:
            normalized_score = min(5, max(1, int(score)))
        except (ValueError, TypeError):
            normalized_score = 3  # Default if score can't be parsed

    return Label(f"Relevance: {normalized_score}")


def ResultCard(result, is_event=False):
    """Create a card for displaying a search result or event."""
    # Extract common fields
    title = result.get("title") or "Untitled"
    url = result.get("url", "#")

    # Handle different content types
    if is_event:
        # For event results
        date_str = result.get("date", "Unknown")
        date_prefix = "Event:"
        content = P(result.get("description", "No description available"))
        score = result.get("relevance_score", 3)
        rank = result.get("rank", "N/A")
        rank_badge = Span(f"Rank: {rank}")
    else:
        # For search results
        date_str = result.get("published_date", "Unknown")
        date_prefix = "Published:"
        content = P(
            format_content(
                result.get("highlights"), result.get("summary"), result.get("content")
            )
        )
        score = result.get("score", 3)
        rank_badge = None

    # Create badges
    badges = [DateTag(date_str, date_prefix), RelevanceBadge(score)]
    if rank_badge:
        badges.append(rank_badge)

    # Create badge container using DivLAligned
    badge_container = DivLAligned(*badges)

    # Create a card using the Card component
    return Card(
        DivLAligned(
            Div(
                H4(title),
                content,
                DivFullySpaced(
                    badge_container, P(A("View Source", href=url, target="_blank"))
                ),
            )
        ),
        cls=CardT.hover,
    )


def initialize_pipeline():
    """Initialize the CryptoEventPipeline."""
    # Get API keys from environment variables
    exa_api_key = os.environ.get("EXA_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

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


async def run_pipeline(
    query,
    date_str,
    openai_api_key=None,
    exa_api_key=None,
    model="gpt-4o-mini",
    judge_prompt=None,
):
    """Run the full pipeline (search and judge) and return results."""
    global pipeline, current_query, current_date, current_model, current_judge_prompt

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
    current_date = date
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

    # Override API keys if provided
    if openai_api_key:
        pipeline.openai_api_key = openai_api_key
    if exa_api_key:
        pipeline.exa_api_key = exa_api_key

    try:
        # Run the search to get articles
        logger.info(f"Running search for query: {query}")
        search_result = await pipeline.search(query, date)

        # Run the judge to extract and rank events
        logger.info("Running judge to extract and rank events")
        events = await pipeline.judge.evaluate_relevance(
            search_result, query, date, model, judge_prompt
        )

        return {
            "search_result": {
                "query": query,
                "results": search_result.articles,
            },
            "events": [event.model_dump() for event in events],
        }
    except Exception as e:
        logger.error(f"Error running pipeline: {str(e)}")
        return {"error": str(e)}


@rt("/")
def get():
    """Render the main page."""
    form = Div(cls="space-y-4")(
        DivCentered(
            H3(
                "Explore the sourcing and ranking functionality",
            ),
        ),
        Form(cls="space-y-4")(
            # First row with Query, Date, and Model dropdown in 8:2:2 ratio
            Grid(
                LabelInput(
                    "Query:",
                    input_el=Textarea(
                        id="query", name="query", value=current_query, rows=3
                    ),
                ),
                LabelInput(
                    "Date:",
                    input_el=Input(
                        id="date",
                        name="date",
                        value=current_date.strftime("%Y-%m-%d"),
                        placeholder="YYYY-MM-DD",
                    ),
                ),
                LabelInput(
                    "Model:",
                    input_el=Select(
                        id="model",
                        name="model",
                        options=[("gpt-4o-mini", "GPT-4o Mini"), ("gpt-4o", "GPT-4o")],
                        value=current_model,
                    ),
                ),
                cols="8 2 2",
            ),
            # Accordion for API keys
            Accordion(
                "API Settings",
                Grid(
                    LabelInput(
                        "OpenAI API Key:",
                        input_el=Input(
                            id="openai_api_key",
                            name="openai_api_key",
                            type="password",
                            placeholder="Leave empty to use environment variable",
                        ),
                        help_text="Optional: Provide your own OpenAI API key",
                    ),
                    LabelInput(
                        "EXA API Key:",
                        input_el=Input(
                            id="exa_api_key",
                            name="exa_api_key",
                            type="password",
                            placeholder="Leave empty to use environment variable",
                        ),
                        help_text="Optional: Provide your own EXA API key",
                    ),
                    cols="1 1",
                ),
            ),
            # Accordion for judge prompt
            Accordion(
                "Judge Prompt",
                Textarea(
                    id="judge_prompt",
                    name="judge_prompt",
                    value=current_judge_prompt,
                    rows=8,
                ),
            ),
            # Centered button
            DivCentered(
                Button(
                    "Run Pipeline",
                    id="run-btn",
                    hx_post="/run",
                    hx_target="#results",
                    cls=ButtonT.primary,
                )
            ),
        ),
        id="search-form",
    )

    results = Div(id="results")

    return Titled("Bitcoin News Mining Explorer", Div(cls="space-y-4")(form, results))


@rt("/run", methods=["POST"])
async def run(
    query: str,
    date: str,
    model: str = "gpt-4o-mini",
    judge_prompt: str = JUDGE_SYSTEM_PROMPT,
    openai_api_key: str = "",
    exa_api_key: str = "",
):
    """Run the pipeline and return results."""
    # Use provided API keys if not empty
    openai_key = openai_api_key if openai_api_key.strip() else None
    exa_key = exa_api_key if exa_api_key.strip() else None
    judge_prompt_val = judge_prompt if judge_prompt.strip() else None

    result = await run_pipeline(
        query, date, openai_key, exa_key, model, judge_prompt_val
    )

    if "error" in result:
        return Alert(result["error"], cls=AlertT.error)

    # Sort events by rank
    events = sorted(
        result["events"], key=lambda x: (x.get("rank") is None, x.get("rank"))
    )

    # Create query display
    query_display = Div(
        H3("Search Results"),
        P(Strong("Query: "), f'"{result["search_result"]["query"]}"'),
        P(Strong("Model: "), model),
    )

    # Create grid layout
    results_grid = Grid(
        # Left column - Search Results
        Div(
            H4("Articles"),
            *[ResultCard(result) for result in result["search_result"]["results"]],
        ),
        # Right column - Ranked Events
        Div(
            H4("Ranked Events"), *[ResultCard(event, is_event=True) for event in events]
        ),
        cols="1 1",
    )

    # Return the complete results
    return Div(H2("Pipeline Results"), query_display, results_grid)


def format_content(highlights, summary, content):
    """Format content handling lists properly."""
    # Check if highlights is available and format it
    if highlights:
        if isinstance(highlights, list):
            return "<br>".join(highlights)
        return highlights

    # If no highlights, try summary
    if summary:
        if isinstance(summary, list):
            return "<br>".join(summary)
        return summary

    # If no summary, use content
    if content:
        if isinstance(content, list):
            return "<br>".join(content[:200]) + "..."
        return content[:200] + "..."

    return "No content"


# Run the application
serve()
