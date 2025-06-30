from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI
from rich.markdown import Markdown
from rich.console import Console
from dotenv import load_dotenv
from textwrap import dedent
import os

from Lecture2.prompts import SYSTEM_PROMPT

if __name__ == "__main__":
    load_dotenv()

    MODEL_NAME = "gpt-4o-mini"
    API_KEY = os.getenv("OPENAI_API_KEY")
    FUNCTION_CODE = dedent(
        """
        def calculate_area(length, width):
            if length <= 0 or width <= 0:
                raise ValueError("Dimensions must be positive")
            return length * width
        """
    )

    llm = OpenAI(model=MODEL_NAME, api_key=API_KEY)
    console = Console()

    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=FUNCTION_CODE,
        ),
    ]

    response = llm.chat(messages)

    markdown = Markdown(response.message.content)
    console.print(markdown)
