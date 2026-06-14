import os
from crewai import Agent, LLM
from tavily import TavilyClient
from config import GROQ_MODEL


# Phase 2 lesson applied to Phase 3: Groq's Llama models produce malformed XML
# when CrewAI calls TavilySearchTool as an LLM tool call. The fix is the same
# principle from Curator — use Python for execution (Tavily SDK), LLM for reasoning
# (formatting and summarizing what was found).

def search_topic(topic: str, max_results: int = 5) -> str:
    """Call Tavily directly via Python SDK and return formatted text blocks."""
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = client.search(
        query=topic,
        search_depth="basic",
        max_results=max_results,
        include_answer=False,
    )
    blocks = []
    for i, r in enumerate(response.get("results", []), 1):
        snippet = (r.get("content") or "")[:400].strip()
        blocks.append(
            f"{i}. {r['title']}\n"
            f"   URL: {r['url']}\n"
            f"   {snippet}"
        )
    return "\n\n".join(blocks)


def create_scout() -> Agent:
    llm = LLM(model=GROQ_MODEL)

    # No tools — Tavily is called in Python before this agent runs.
    # The agent's job is now purely reasoning: read pre-fetched results
    # and produce a clean, consistently formatted numbered list.
    return Agent(
        role="Research Scout",
        goal=(
            "Summarize pre-fetched search results into a clean numbered list. "
            "Each entry must include: title, URL, and a one-sentence summary of what the article covers."
        ),
        backstory=(
            "You are a specialist researcher who reads raw search results and distills "
            "them into a consistent format for downstream agents."
        ),
        llm=llm,
        verbose=True,
    )
