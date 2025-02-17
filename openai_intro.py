import openai
from datetime import datetime

# import os
# os.environ["OPENAI_API_KEY"] = "your-key"


def get_bitcoin_events(date_str="2022-06-05"):
    try:
        # Initialize OpenAI client
        client = (
            openai.OpenAI()
        )  # Assumes OPENAI_API_KEY is set in environment variables

        # Craft the prompt
        prompt = f"What significant events happened in the Bitcoin ecosystem on {date_str}? Please provide a concise summary."

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "Your task is to extract the events from the news articles and provide a concise summary.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"Error occurred: {str(e)}"


def main():
    # Get Bitcoin events for June 5th, 2022
    events = get_bitcoin_events()
    print("Bitcoin Events on June 5th, 2022:")
    print(events)


if __name__ == "__main__":
    main()
