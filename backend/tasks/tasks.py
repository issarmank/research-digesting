from crewai import Agent, Task


def create_scout_task(scout: Agent, topic: str) -> Task:
    return Task(
        description=(
            f"Search for recent, high-quality content about: '{topic}'. "
            "Find articles, blog posts, papers, or news from the last 30 days. "
            "Collect the title, URL, and a one-sentence summary for each result."
        ),
        expected_output=(
            "A list of 3-5 results. Each result must include: title, URL, and a one-sentence summary."
        ),
        agent=scout,
    )
