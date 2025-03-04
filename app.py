"""Interactive application for Bitcoin news mining query discovery."""

from fasthtml.common import *
import os
import logging
from datetime import datetime

from src.pipeline import CryptoEventPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the FastHTML app
app = FastHTML()
rt = app.route

# Global variables to store state
pipeline = None
current_query = "Bitcoin cryptocurrency news and developments"
current_date = datetime.now()


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


async def run_pipeline(query, date_str, openai_api_key=None, exa_api_key=None):
    """Run the full pipeline (search and judge) and return results."""
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

    current_query = query
    current_date = date

    # Initialize pipeline if not already done or if new API keys are provided
    if pipeline is None or openai_api_key or exa_api_key:
        try:
            # Get API keys from environment variables or use provided ones
            env_exa_api_key = os.environ.get("EXA_API_KEY")
            env_openai_api_key = os.environ.get("OPENAI_API_KEY")

            # Use provided keys if available, otherwise fall back to environment variables
            exa_key = exa_api_key if exa_api_key else env_exa_api_key
            openai_key = openai_api_key if openai_api_key else env_openai_api_key

            if not exa_key or not openai_key:
                return {
                    "error": "Missing API keys. Please provide both OpenAI and EXA API keys."
                }

            # Initialize pipeline with the appropriate keys
            pipeline = CryptoEventPipeline(
                exa_api_key=exa_key,
                openai_api_key=openai_key,
                load_db=False,
            )
        except ValueError as e:
            return {"error": str(e)}

    try:
        # Run the pipeline
        search_result, events = await pipeline.process_date(
            date=date,
            base_query=query,
            full_month=False,
            max_results=15,
            save_results=False,
        )

        return {
            "search_result": {
                "query": search_result.query,
                "search_date": search_result.search_date.isoformat(),
                "results": search_result.results,
            },
            "events": [event.model_dump() for event in events],
        }
    except Exception as e:
        logger.error(f"Error running pipeline: {str(e)}")
        return {"error": str(e)}


@rt("/")
def get():
    """Render the main page."""
    form = Form(
        Group(
            Label("Query:", for_="query"),
            Textarea(
                id="query",
                name="query",
                value=current_query,
                rows=3,
                style="width: 100%; font-size: 16px; padding: 10px;",
            ),
            Small("Enter your search query for Bitcoin news and events"),
        ),
        Group(
            Label("Date (YYYY-MM-DD):", for_="date"),
            Input(id="date", name="date", value=current_date.strftime("%Y-%m-%d")),
        ),
        Group(
            Label("OpenAI API Key:", for_="openai_api_key"),
            Input(
                id="openai_api_key",
                name="openai_api_key",
                type="password",
                placeholder="Leave empty to use environment variable",
            ),
            Small("Optional: Provide your own OpenAI API key"),
        ),
        Group(
            Label("EXA API Key:", for_="exa_api_key"),
            Input(
                id="exa_api_key",
                name="exa_api_key",
                type="password",
                placeholder="Leave empty to use environment variable",
            ),
            Small("Optional: Provide your own EXA API key"),
        ),
        Group(
            Button("Run Pipeline", id="run-btn", hx_post="/run", hx_target="#results"),
        ),
        id="search-form",
    )

    results = Div(id="results")

    return Titled(
        "Bitcoin News Mining Explorer",
        P(
            "Explore the sourcing and ranking functionality of the Bitcoin news mining pipeline"
        ),
        Card(form, header=H2("Search Parameters")),
        results,
        Style(
            """
            body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            .card { margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            textarea#query {
                width: 100%;
                min-height: 80px;
                font-size: 16px;
                padding: 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
                transition: border-color 0.2s, box-shadow 0.2s;
                resize: vertical;
                font-family: inherit;
            }
            textarea#query:focus {
                border-color: #0066cc;
                box-shadow: inset 0 1px 3px rgba(0,102,204,0.2);
                outline: none;
            }
            .result-card { 
                margin-bottom: 15px; 
                padding: 15px; 
                border: 1px solid #e0e0e0; 
                border-radius: 8px; 
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                background-color: #fff;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .result-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 3px 6px rgba(0,0,0,0.12);
            }
            .result-card h4 { margin-top: 0; color: #333; }
            .result-card p { margin: 8px 0; color: #555; }
            .result-card a { color: #0066cc; text-decoration: none; }
            .result-card a:hover { text-decoration: underline; }
            .error { color: #d32f2f; font-weight: bold; padding: 10px; background: #ffebee; border-radius: 4px; }
            .badge { 
                display: inline-block; 
                background: #007bff; 
                color: white; 
                padding: 3px 8px; 
                border-radius: 12px; 
                font-size: 12px; 
                margin-left: 8px;
                font-weight: 500;
            }
            .badge.success { background: #28a745; }
            .columns { 
                display: flex; 
                gap: 25px; 
                margin-top: 20px;
            }
            .column { 
                flex: 1; 
                background: #f9f9f9;
                padding: 20px;
                border-radius: 8px;
            }
            .column h3 {
                margin-top: 0;
                padding-bottom: 10px;
                border-bottom: 1px solid #eee;
                color: #444;
            }
            .query-display {
                font-size: 1.1em;
                background: #f0f4f8;
                padding: 10px 15px;
                border-radius: 6px;
                margin-bottom: 15px;
                border-left: 4px solid #0066cc;
            }
            .query-text {
                font-weight: bold;
                color: #0066cc;
            }
            @media (max-width: 768px) { 
                .columns { flex-direction: column; } 
            }
        """
        ),
    )


@rt("/run", methods=["POST"])
async def run(query: str, date: str, openai_api_key: str = "", exa_api_key: str = ""):
    """Run the pipeline and return results."""
    # Use provided API keys if not empty
    openai_key = openai_api_key if openai_api_key.strip() else None
    exa_key = exa_api_key if exa_api_key.strip() else None

    result = await run_pipeline(query, date, openai_key, exa_key)

    if "error" in result:
        return Div(result["error"], cls="error")

    search_results = Div(
        H3("Search Results"),
        *[
            Div(
                H4(
                    result.get("title", "No Title"),
                    Span(f"{result.get('score', 'N/A')}", cls="badge"),
                ),
                P(f"Published: {result.get('published_date', 'Unknown')}"),
                P(
                    A(
                        result.get("url", "#"),
                        href=result.get("url", "#"),
                        target="_blank",
                    )
                ),
                P(
                    # Handle highlights that might be a list
                    format_content(
                        result.get("highlights"),
                        result.get("summary"),
                        result.get("content"),
                    )
                ),
                cls="result-card",
            )
            for result in result["search_result"]["results"]
        ],
    )

    # Sort events by rank
    events = sorted(
        result["events"], key=lambda x: (x.get("rank") is None, x.get("rank"))
    )

    ranked_events = Div(
        H3("Ranked Events"),
        *[
            Div(
                H4(
                    event.get("title", "No Title"),
                    Span(f"Rank: {event.get('rank', 'N/A')}", cls="badge"),
                    Span(
                        f"Score: {event.get('relevance_score', 'N/A')}",
                        cls="badge success",
                    ),
                ),
                P(f"Event Date: {event.get('event_date', 'Unknown')}"),
                P(
                    A(
                        event.get("source_url", "#"),
                        href=event.get("source_url", "#"),
                        target="_blank",
                    )
                ),
                P(event.get("description", "No description")),
                cls="result-card",
            )
            for event in events
        ],
    )

    return Div(
        H2("Pipeline Results"),
        Div(
            P(
                "Search query: ",
                Span(f'"{result["search_result"]["query"]}"', cls="query-text"),
            ),
            P(f"Search date: {result['search_result']['search_date']}"),
            cls="query-display",
        ),
        Div(
            Div(search_results, cls="column"),
            Div(ranked_events, cls="column"),
            cls="columns",
        ),
    )


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
