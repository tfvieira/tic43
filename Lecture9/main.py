from docling.document_converter import DocumentConverter
from agno.tools.bravesearch import BraveSearchTools
from semantic_text_splitter import TextSplitter
from agno.embedder.openai import OpenAIEmbedder
from agno.models.openai import OpenAIChat
from agno.vectordb.qdrant import Qdrant
from qdrant_client.http import models
from joblib import Parallel, delayed
from agno.document import Document
from dotenv import load_dotenv
from agno.agent import Agent
import traceback
import requests
import pprint
import os


from prompts import (
    TECH_EXTRACTOR_PROMPT,
    CODE_GENERATOR_ARCHITECT_PROMPT,
    CODE_GENERATOR_PERFORMANCE_PROMPT,
    CODE_GENERATOR_ROBUSTNESS_PROMPT,
    CODE_MERGER_PROMPT,
)


def extract_urls_from_webpage(url: str) -> list[str]:
    """
    Extracts all URLs from a given webpage.

    :param url: The URL of the webpage to extract URLs from.
    :type url: str
    :raises ValueError: If the URL is empty or invalid.
    :raises ConnectionError: If unable to connect to the URL.
    :raises TimeoutError: If the request times out.
    :return: A list of URLs found in the webpage.
    :rtype: list[str]
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    try:
        import requests
        from urllib.parse import urljoin, urlparse
        from bs4 import BeautifulSoup

        # Send GET request to the URL
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all anchor tags with href attributes
        links = soup.find_all("a", href=True)

        # Extract and normalize URLs
        extracted_urls = []
        for link in links:
            href = link["href"]
            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(url, href)

            # Validate the URL format
            parsed_url = urlparse(absolute_url)
            if parsed_url.scheme in ("http", "https"):
                extracted_urls.append(absolute_url)

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(extracted_urls))

        return unique_urls

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        traceback.print_exc()
        raise ConnectionError(f"Failed to connect to URL '{url}': {str(e)}")
    except requests.exceptions.HTTPError as e:
        traceback.print_exc()
        raise ConnectionError(f"HTTP error occurred for URL '{url}': {str(e)}")
    except requests.exceptions.RequestException as e:
        traceback.print_exc()
        raise ConnectionError(f"Request failed for URL '{url}': {str(e)}")
    except ImportError as e:
        traceback.print_exc()
        raise ImportError(f"Required packages not installed: {str(e)}")


def create_qdrant_table(
    table_name: str, embedder: OpenAIEmbedder, vector_db: Qdrant
) -> None:
    """
    Creates a Qdrant collection named 'TIC43' if it doesn't already exist.

    :param table_name: The name of the table to create.
    :type table_name: str
    :param embedder: The embedder instance used to get vector dimensions.
    :type embedder: OpenAIEmbedder
    :param vector_db: The Qdrant vector database instance.
    :type vector_db: Qdrant
    """
    collections_response = vector_db.client.get_collections()
    collection_names = [c.name for c in collections_response.collections]

    if table_name not in collection_names:
        vector_db.client.create_collection(
            collection_name=table_name,
            vectors_config=models.VectorParams(
                size=embedder.dimensions, distance=models.Distance.COSINE
            ),
        )


def process_link(vector_db: Qdrant, link: str) -> list[Document]:
    """
    Processes a single link by converting it to documents and chunking the content.

    :param link: The URL to process.
    :type link: str
    :return: A list of Document objects created from the chunked content.
    :rtype: list[Document]
    """
    try:
        result = converter.convert(link)
        chunks = splitter.chunks(result.document.export_to_markdown())
        docs = [Document(content=chunk) for chunk in chunks]
        vector_db.insert(docs)
        print(f"Processed {link} and inserted {len(docs)} documents")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred for URL '{link}': {str(e)}")
        return False
    return True


if __name__ == "__main__":
    load_dotenv()
    INSERT_CHUNKS = False
    WITH_CONTEXT = False
    QUERY = "Create a python script that use LemonFox.ai to transcript an audio and save it to a file"

    embedder = OpenAIEmbedder(api_key=os.getenv("OPENAI_API_KEY"))
    vector_db = Qdrant(
        collection="Lecture9", url="http://localhost:6333", embedder=embedder
    )

    create_qdrant_table("Lecture9", embedder, vector_db)

    tech_extractor_agent = Agent(
        show_tool_calls=True,
        tools=[BraveSearchTools(fixed_max_results=1)],
        model=OpenAIChat(
            id="gpt-4o-mini",
            system_prompt=TECH_EXTRACTOR_PROMPT,
        ),
    )

    code_generator_architect_agent = Agent(
        model=OpenAIChat(
            id="gpt-4o-mini",
            system_prompt=CODE_GENERATOR_ARCHITECT_PROMPT,
        ),
    )

    code_generator_performance_agent = Agent(
        model=OpenAIChat(
            id="gpt-4o-mini",
            system_prompt=CODE_GENERATOR_PERFORMANCE_PROMPT,
        ),
    )

    code_generator_robustness_agent = Agent(
        model=OpenAIChat(
            id="gpt-4o-mini",
            system_prompt=CODE_GENERATOR_ROBUSTNESS_PROMPT,
        ),
    )

    code_merger_agent = Agent(
        model=OpenAIChat(
            id="gpt-4o-mini",
            system_prompt=CODE_MERGER_PROMPT,
        ),
    )

    if INSERT_CHUNKS:
        converter = DocumentConverter()
        splitter = TextSplitter(1000, 100)

        print("🔍 Extracting technologies and collecting URLs...")
        tech_urls_response = tech_extractor_agent.run(
            f"Extract technologies from this query and find relevant URLs: {QUERY}"
        )
        print("Tech URLs Response:", tech_urls_response.content)
        links = [
            link.split(": ")[1].strip()
            for link in tech_urls_response.content.split("\n")
            if link.strip()
        ]

        extracted_links = []

        for link in links:
            extracted_links.extend(extract_urls_from_webpage(link))

        links = list(set(extracted_links))
        pprint.pprint(links)

        all_docs = Parallel(n_jobs=-1, backend="threading")(
            delayed(process_link)(vector_db, link) for link in links
        )

    if WITH_CONTEXT:
        context = [frag.content for frag in vector_db.search(QUERY, 10)]
        context = "\n----------------------------------------------\n".join(context)
        context = f"Context:\n{context}"
        context += "\n----------------------------------------------\n"
    else:
        context = ""

    print("Generating code...")

    def generate_code(
        agent, context: str, query: str, code_type: str
    ) -> tuple[str, str]:
        """
        Generates code using the specified agent.

        :param agent: The agent to use for code generation.
        :param context: The context to provide to the agent.
        :type context: str
        :param query: The query to process.
        :type query: str
        :param code_type: The type of code being generated.
        :type code_type: str
        :return: Tuple containing the generated code content and type.
        :rtype: tuple[str, str]
        """
        result = agent.run(f"{context}\n\n\n{query}")
        print(f"{code_type} code generated")
        return result.content, code_type

    code_results = Parallel(n_jobs=3, backend="threading")(
        delayed(generate_code)(agent, context, QUERY, code_type)
        for agent, code_type in [
            (code_generator_architect_agent, "Architectural"),
            (code_generator_performance_agent, "Performance"),
            (code_generator_robustness_agent, "Robustness"),
        ]
    )

    architectural_code_content = next(
        result[0] for result in code_results if result[1] == "Architectural"
    )
    performance_code_content = next(
        result[0] for result in code_results if result[1] == "Performance"
    )
    robustness_code_content = next(
        result[0] for result in code_results if result[1] == "Robustness"
    )

    code_context = f"""
    {context}

    Architectural code:
    {architectural_code_content}

    Performance code:
    {performance_code_content}

    Robustness code:
    {robustness_code_content}
    """

    print("Merging code...")
    merged_code = code_merger_agent.run(code_context, markdown=True)
    print("Code merged")

    merged_code_content = merged_code.content
    merged_code_content = merged_code_content.replace("```python", "").replace("```", "").strip()

    output_name = "merged_code.py"
    if INSERT_CHUNKS:
        output_name = f"insert_chunks_{output_name}"
    if WITH_CONTEXT:
        output_name = f"with_context_{output_name}"

    with open(output_name, "w") as f:
        f.write(merged_code_content)

    print(f"Code saved to {output_name}")
