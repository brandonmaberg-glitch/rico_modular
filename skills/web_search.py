from openai import OpenAI
import logging
import os

logger = logging.getLogger("RICO")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def run_web_search(query: str) -> str:
    """
    Uses OpenAI's built-in web search tool to retrieve real-time information.
    """
    try:
        logger.info(f"Running web search for: {query}")

        completion = client.chat.completions.create(
            model="gpt-5.1",
            messages=[
                {
                    "role": "user",
                    "content": f"Using the web search tool, answer this question with current information: {query}"
                }
            ],
            tools=[
                {"type": "web_search"}
            ]
        )

        answer = completion.choices[0].message.content
        logger.info(f"Web search result: {answer}")
        return answer

    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Sorry Sir, I was unable to search the web. {e}"


__all__ = ["run_web_search"]
