from agno.models.openai import OpenAIChat
from agno.media import Image
from dotenv import load_dotenv
from agno.agent import Agent
import os

from prompts import SYSTEM_PROMPT

if __name__ == "__main__":
    load_dotenv()

    # IMAGE_PATH = "images/diagram.png"
    IMAGE_PATH = "images/cctv.jpg"

    try:
        if not os.path.exists(IMAGE_PATH):
            raise FileNotFoundError(f"The image file was not found at '{IMAGE_PATH}'")

        agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini", system_prompt=SYSTEM_PROMPT),
        )

        image = Image(filepath=IMAGE_PATH)

        print(f"Sending image '{IMAGE_PATH}' to the model for description...")

        agent.print_response(images=[image], markdown=True)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure the path in the IMAGE_PATH variable is correct.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
