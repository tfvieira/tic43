from phoenix.client.types import PromptVersion
from agno.models.openai import OpenAIChat
from phoenix.client import Client
from phoenix.otel import register
from dotenv import load_dotenv
from agno.agent import Agent
import traceback
import httpx
import json
import time


from prompts import DEFAULT_PROMPT, DEFAULT_PROMPT_V2


def parse_string_to_dict(json_string: str) -> dict | None:
    """
    Parse a JSON string to a dictionary.

    :param json_string: The JSON string to parse.
    :type json_string: str
    :raises json.JSONDecodeError: If the string is not valid JSON.
    :raises TypeError: If the input is not a string.
    :return: The parsed dictionary or None if parsing fails.
    :rtype: dict | None
    """
    try:
        if not isinstance(json_string, str):
            raise TypeError(f"Expected string, got {type(json_string).__name__}")

        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        traceback.print_exc()
        return None


def get_prompt_versions(base_url: str, prompt_id: str) -> dict | None:
    """
    Retrieve all versions of a specific prompt from the Phoenix API.

    :param base_url: The base URL of the Phoenix API.
    :type base_url: str
    :param prompt_id: The identifier of the prompt.
    :type prompt_id: str
    :raises httpx.HTTPStatusError: If the HTTP request fails with a status error.
    :raises httpx.RequestError: If the request fails due to connection issues.
    :raises TypeError: If the parameters are not strings.
    :return: The prompt versions data or None if the request fails.
    :rtype: dict | None
    """
    try:
        if not isinstance(base_url, str):
            raise TypeError(
                f"Expected string for base_url, got {type(base_url).__name__}"
            )
        if not isinstance(prompt_id, str):
            raise TypeError(
                f"Expected string for prompt_id, got {type(prompt_id).__name__}"
            )

        url = f"{base_url}/v1/prompts/{prompt_id}/versions"

        with httpx.Client() as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()["data"]

    except (httpx.HTTPStatusError, httpx.RequestError, TypeError):
        traceback.print_exc()
        return None


if __name__ == "__main__":
    load_dotenv()

    PROJECT_ID = "TIC43"
    QUERY = "What is the capital of Brazil?"
    PROMPT_ID = "default"
    SELECTED_PROMPT = DEFAULT_PROMPT

    tracer_provider = register(
        project_name=PROJECT_ID,
        auto_instrument=True,
        protocol="http/protobuf",
    )
    tracer = tracer_provider.get_tracer(__name__)

    base_url = "http://localhost:6006"
    client = Client(base_url=base_url)

    current_prompt = None
    current_version = None
    try:
        versions = get_prompt_versions(base_url, PROMPT_ID)

        for version in versions:
            content = version["template"]["messages"][0]["content"]
            if content == SELECTED_PROMPT:
                current_prompt = content
                current_id = version["id"]
                current_version = client.prompts.tags.list(
                    prompt_version_id=current_id
                )[0]["name"]
                break
    except httpx.HTTPStatusError:
        current_prompt = None

    if current_prompt is None or current_prompt != SELECTED_PROMPT:
        prompt = client.prompts.create(
            name=PROMPT_ID,
            version=PromptVersion(
                [{"role": "system", "content": SELECTED_PROMPT}],
                model_name="gpt-4o-mini",
            ),
        )
        versions = get_prompt_versions(base_url, PROMPT_ID)
        tag_name = f"v{len(versions)}"
        client.prompts.tags.create(
            prompt_version_id=prompt.id,
            name=tag_name,
        )

        current_prompt = SELECTED_PROMPT
        current_version = tag_name

    agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini", system_prompt=current_prompt),
    )

    agent.print_response(QUERY)

    time.sleep(1)

    spans = client.spans.get_spans(project_identifier=PROJECT_ID)
    sorted_spans = sorted(spans, key=lambda span: span["end_time"], reverse=True)
    last_span_id = sorted_spans[0]["context"]["span_id"]

    annotation = client.annotations.add_span_annotation(
        annotation_name=current_version,
        annotator_kind="CODE",
        span_id=last_span_id,
        label=current_version,
    )
