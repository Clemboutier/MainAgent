"""
Flow wiring for the MainAgent PocketFlow pipeline.

The concrete nodes will be implemented in future tasks; for now we expose
factory helpers so the FastAPI server can instantiate the flow easily.
"""

from pocketflow import Flow

from .nodes import (
    AnswerNode,
    DecideActionNode,
    EmbedQueryNode,
    RetrieveRAGNode,
    SearchWebNode,
    ExecuteMCPToolNode,
)


def create_research_flow() -> Flow:
    """Create the main PocketFlow graph used by the backend."""
    decide = DecideActionNode()
    search = SearchWebNode()
    embed_query = EmbedQueryNode()
    retrieve = RetrieveRAGNode()
    execute_tool = ExecuteMCPToolNode()
    answer = AnswerNode()

    decide - "search" >> search
    decide - "rag" >> embed_query
    decide - "tool" >> execute_tool
    decide - "answer" >> answer
    
    search - "decide" >> decide
    execute_tool - "decide" >> decide
    
    embed_query >> retrieve >> answer

    return Flow(start=decide)

