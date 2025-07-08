from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat
from agno.agent import Agent

from phoenix.otel import register
from dotenv import load_dotenv

from prompts import WITH_SAMPLES_PROMPT, WITHOUT_SAMPLES_PROMPT


tracer_provider = register(
    project_name="TIC43",
    auto_instrument=True,
    protocol="http/protobuf",
)
tracer = tracer_provider.get_tracer(__name__)


@tracer.chain
def random_func(input: str) -> str:
    return f"For the input {input}, the output is Output"


if __name__ == "__main__":
    load_dotenv()

    TASK = "Who was the person that created the GAN architecture?"

    cot_agent = Agent(
        tools=[DuckDuckGoTools()],
        show_tool_calls=True,
        model=OpenAIChat(id="gpt-4o-mini", system_prompt=WITH_SAMPLES_PROMPT),
    )

    without_cot_agent = Agent(
        tools=[DuckDuckGoTools()],
        show_tool_calls=True,
        model=OpenAIChat(id="gpt-4o-mini", system_prompt=WITHOUT_SAMPLES_PROMPT),
    )

    output = random_func("input")
    print(output)

    cot_agent.print_response(TASK)

    without_cot_agent.print_response(TASK)
