from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import os

from prompts import SYSTEM_PROMPT


def explain_regex_factory(client):
    def explain_regex(user_input):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
        )
        return response.choices[0].message.content

    return explain_regex


if __name__ == "__main__":
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    explain_regex = explain_regex_factory(client)

    iface = gr.Interface(
        fn=explain_regex_factory(client),
        inputs=gr.Textbox(lines=2, label="Regex or Description"),
        outputs=gr.Markdown(label="Explanation / Generated Regex"),
        title="Interactive Regex Explainer",
        description="Enter a regular expression to get a natural language explanation, or describe the text pattern you want, and the AI will generate a regex for you.",
        flagging_mode="never",
    )

    iface.launch(inbrowser=True)
