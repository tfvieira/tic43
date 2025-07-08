from docling.document_converter import DocumentConverter
from semantic_text_splitter import TextSplitter
from agno.embedder.openai import OpenAIEmbedder
from agno.models.openai import OpenAIChat
from agno.vectordb.qdrant import Qdrant
from qdrant_client.http import models
from agno.document import Document
from dotenv import load_dotenv
from agno.agent import Agent
import os


from prompts import SYSTEM_PROMPT


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


if __name__ == "__main__":
    load_dotenv()

    INSERT_CHUNKS = False
    WITH_CONTEXT = True
    QUERY = "How can I use docling in Python to convert a PDF file to text? Give a code example."

    embedder = OpenAIEmbedder(api_key=os.getenv("OPENAI_API_KEY"))
    vector_db = Qdrant(
        collection="TIC43", url="http://localhost:6333", embedder=embedder
    )

    converter = DocumentConverter()
    splitter = TextSplitter(1000, 200)

    if INSERT_CHUNKS:
        create_qdrant_table("TIC43", embedder, vector_db)

        result = converter.convert("https://docling-project.github.io/docling/usage/")
        chunks = splitter.chunks(result.document.export_to_markdown())
        docs = [Document(content=chunk) for chunk in chunks]
        vector_db.insert(docs)
    else:
        if WITH_CONTEXT:
            context = [frag.content for frag in vector_db.search(QUERY, 2)]
            context = " - " + "\n - ".join(context)
        else:
            context = ""

        SYSTEM_PROMPT = SYSTEM_PROMPT.format(context=context)

        agent = Agent(
            show_tool_calls=True,
            model=OpenAIChat(id="gpt-4o-mini", system_prompt=SYSTEM_PROMPT),
            search_knowledge=True,
        )

        agent.print_response(QUERY, markdown=True)
