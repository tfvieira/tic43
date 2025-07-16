from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.schema import UserMemory
from agno.models.openai import OpenAIChat
from agno.memory.v2.memory import Memory
from rich.markdown import Markdown
from rich.console import Console
from dotenv import load_dotenv
from agno.agent import Agent
from textwrap import dedent
import traceback
import json

from prompts import CODER_PROMPT, PLANNER_PROMPT, REVIEWER_PROMPT


def main() -> None:
    load_dotenv()

    QUERY = "Generate a simples function that parse a JSON in markdown format to a parsable JSON."

    console = Console()
    database_file = "sqlite:///memory.db"
    memory_db = SqliteMemoryDb("memories", database_file)
    memory = Memory(db=memory_db)

    memories_to_add = [
        ("I like to code in Python.", ["coding"], "coding_memory_1"),
        (
            "All the functions must have a docstring following the Sphinx pattern with :param and :return. If the return is None, do not add :return: None in the docstring.",
            ["coding"],
            "coding_memory_2",
        ),
        (
            "The code must be well-formatted and easy to read.",
            ["coding"],
            "coding_memory_3",
        ),
        (
            "When i ask for coding, just provide the code without any other text.",
            ["coding"],
            "coding_memory_4",
        ),
    ]

    for memory_to_add in memories_to_add:
        memory.add_user_memory(
            memory=UserMemory(
                memory=memory_to_add[0],
                topics=memory_to_add[1],
                memory_id=memory_to_add[2],
            )
        )

    planner = Agent(
        model=OpenAIChat("o4-mini", system_prompt=PLANNER_PROMPT),
        memory=memory,
        enable_user_memories=True,
    )

    coder = Agent(
        model=OpenAIChat("gpt-4o-mini", system_prompt=CODER_PROMPT),
        memory=memory,
    )

    reviewer = Agent(
        model=OpenAIChat("gpt-4o-mini", system_prompt=REVIEWER_PROMPT),
        memory=memory,
    )

    review_suggestions = ""
    max_tries = 3
    for _ in range(max_tries):
        query = QUERY + review_suggestions

        plan = planner.run(query, markdown=True)

        plan_content = plan.content
        print("=" * 40, "PLAN", "=" * 40)
        console.print(Markdown(plan_content))

        code = coder.run(plan_content)
        code_content = code.content
        print("=" * 40, "CODE", "=" * 40)
        console.print(Markdown(code_content))

        review_template = dedent(
            """
        Query: {query}
        Code: {code}
        """
        )
        review = reviewer.run(review_template.format(query=query, code=code_content))
        review_content = review.content
        review_content = review_content.replace("```json", "").replace("```", "")
        print("=" * 39, "REVIEW", "=" * 39)

        try:
            review_content = json.loads(review_content)
            review_suggestions = review_content["review_suggestions"]
            review_status = review_content["review_status"]
            console.print(Markdown(f"# Review Status: `{review_status}`"))
            console.print(Markdown(f"**Review Suggestions:** \n\n{review_suggestions}"))

            if review_status == "approve":
                break
        except json.JSONDecodeError:
            traceback.print_exc()
            console.print(Markdown(review_content))
            break
        print("=" * 80)


if __name__ == "__main__":
    main()
