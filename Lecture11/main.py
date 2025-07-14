from agno.models.openai import OpenAIChat
from joblib import Parallel, delayed
from dotenv import load_dotenv
from agno.agent import Agent
from textwrap import dedent
import pandas as pd
import traceback
import json
import os

from prompts import JUDGE_PROMPT, DEFAULT_PROMPT


def process_question_pair(
    question: str,
    expected_output: str,
    default_agent: Agent,
    judge_agent: Agent,
    EVAL_RATINGS: dict,
) -> dict:
    """
    Process a single question-expected output pair and return evaluation results.

    :param question: The input question to evaluate.
    :type question: str
    :param expected_output: The expected answer for the question.
    :type expected_output: str
    :param default_agent: The default agent to use for the question.
    :type default_agent: Agent
    :param judge_agent: The judge agent to use for the question.
    :type judge_agent: Agent
    :param EVAL_RATINGS: The evaluation ratings to use for the question.
    :type EVAL_RATINGS: dict
    :return: Dictionary containing evaluation results.
    :rtype: dict
    :raises json.JSONDecodeError: If the judge output cannot be parsed as JSON.
    :raises KeyError: If required keys are missing from the judge output.
    """
    try:
        response = default_agent.run(question)
        response = response.content
        output = judge_agent.run(
            dedent(
                f"""
                        Obtained Answer: {response}
                        Expected Answer: {expected_output}
                        """
            )
        )
        output = json.loads(
            output.content.replace("```json", "").replace("```", "").strip()
        )
        # print(
        #     dedent(
        #         f"""
        #         Question: {question}
        #         Obtained Answer: {response}
        #         Expected Answer: {expected_output}
        #         Judge: {EVAL_RATINGS[output['similarity_rating']]}/4 - {output['justification']}
        #         """
        #     )
        # )
        return {
            "question": question,
            "obtained_answer": response,
            "expected_answer": expected_output,
            "similarity_rating": output["similarity_rating"],
            "similarity_score": EVAL_RATINGS[output["similarity_rating"]],
            "justification": output["justification"],
        }
    except (json.JSONDecodeError, KeyError) as e:
        traceback.print_exc()
        return {
            "question": question,
            "obtained_answer": "",
            "expected_answer": expected_output,
            "similarity_rating": "Error",
            "similarity_score": 0,
            "justification": f"Error processing question: {str(e)}",
        }


def main() -> None:
    load_dotenv()

    EVAL_RATINGS = {
        "Totally Different": 0,
        "Slightly Similar": 1,
        "Moderately Similar": 2,
        "Highly Similar": 3,
        "Identical / Semantically Equivalent": 4,
    }

    os.makedirs("eval", exist_ok=True)

    eval_datasets = [
        "basic_questions",
        "domain_specific_questions",
        "adversarial_questions",
    ]
    for eval_dataset in eval_datasets:
        try:
            csv_file_path = f"data/{eval_dataset}.csv"
            eval_file_path = f"eval/{eval_dataset}.csv"
            df = pd.read_csv(csv_file_path)

            questions, expected_outputs = df["input"], df["expected_output"]

            default_agent = Agent(
                name="Default Agent",
                model=OpenAIChat(id="gpt-4o-mini", system_prompt=DEFAULT_PROMPT),
            )

            judge_agent = Agent(
                name="Judge Agent",
                model=OpenAIChat(id="o4-mini", system_prompt=JUDGE_PROMPT),
            )

            eval_df = pd.DataFrame(
                columns=[
                    "question",
                    "obtained_answer",
                    "expected_answer",
                    "similarity_rating",
                    "similarity_score",
                    "justification",
                ]
            )

            results = Parallel(n_jobs=3)(
                delayed(process_question_pair)(
                    question, expected_output, default_agent, judge_agent, EVAL_RATINGS
                )
                for question, expected_output in zip(questions, expected_outputs)
            )

            for result in results:
                new_row = pd.DataFrame([result])
                eval_df = pd.concat([eval_df, new_row], ignore_index=True)
            eval_df.to_csv(eval_file_path, index=False)

        except Exception as e:
            traceback.print_exc()
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
