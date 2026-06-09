from crewai import Agent, LLM
from crewai_tools import TavilySearchTool
from config import GROQ_MODEL


def create_scout() -> Agent:
    llm = LLM(model=GROQ_MODEL)

    search_tool = TavilySearchTool()

    return Agent(
        role="Research Scout",
        goal="Find the most relevant and recent articles, papers, and posts on the given topic.",
        backstory=(
            "You are a specialist researcher who knows how to search efficiently "
            "and surface high-quality sources."
        ),
        tools=[search_tool],
        llm=llm,
        verbose=True,
    )
