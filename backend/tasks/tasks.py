from crewai import Agent, Task
from agents.writer import Digest


def create_scout_task(scout: Agent, topic: str, raw_results: str) -> Task:
    return Task(
        description=(
            f"The following search results were fetched from Tavily for the topic: '{topic}'.\n\n"
            f"{raw_results}\n\n"
            "Format these into a clean numbered list. "
            "Each entry: title, URL, and a one-sentence summary of what the article covers. "
            "Keep all URLs exactly as shown — do not alter or shorten them."
        ),
        expected_output=(
            "A numbered list of results. Each entry must include: title, URL, and a one-sentence summary."
        ),
        agent=scout,
    )


def create_writer_task(writer: Agent, articles: list[dict], topic: str) -> Task:
    # Format the curator's output into a numbered block the LLM can reason over.
    # Each dict has {"raw": <Scout's original text block>, "url": <extracted URL>}.
    article_blocks = "\n\n---\n\n".join(
        f"[{i+1}] {a['raw']}" for i, a in enumerate(articles)
    )

    # Prompt engineering lesson: every instruction below exists for a specific reason.
    # Remove any one of them and the output degrades in a predictable way.
    description = f"""
You are editing a research digest for the topic: "{topic}".

Below are {len(articles)} articles found by the Scout agent. Your job has two steps:

STEP 1 — SCORE RELEVANCE
Score each article 0.0–1.0 against the topic. Be honest and strict.
Penalize (score below 0.6, set kept=False):
  - Marketing/promotional content with no technical depth
  - Paywalled previews (title + teaser, no substance)
  - Generic overviews that anyone could write without expertise
  - Off-topic results (tangentially related but not about "{topic}")

STEP 2 — SYNTHESIZE THE KEEPERS
For articles with kept=True, write a digest. Do NOT summarize each article separately.
Instead:
  - Identify 2-3 themes or patterns that cut across multiple articles
  - Write one DigestSection per theme with a specific heading and a 2-3 sentence synthesis
  - Each key_insight must be a specific, non-obvious claim — not "research is advancing"
  - The overview is 3 sentences on the current state of the topic, informed by these articles

ARTICLES TO EVALUATE:

{article_blocks}
"""

    # expected_output describes the Pydantic fields in plain language.
    # CrewAI passes this to the LLM alongside the output_pydantic schema.
    expected_output = (
        "A Digest object with: topic, overview (3 sentences), key_insights (3-5 specific bullets), "
        "sections (one per theme, each with heading + 2-3 sentence synthesis body), "
        "scored_articles (one ArticleScore per input article with url, relevance_score, kept, reason), "
        "sources (URLs of kept articles only), total_articles, included_articles."
    )

    # output_pydantic is the key line. It tells CrewAI:
    #   "Don't accept free-form text — make the LLM return valid JSON for this schema."
    # CrewAI then parses the response into a real Digest instance available at result.pydantic.
    return Task(
        description=description,
        expected_output=expected_output,
        agent=writer,
        output_pydantic=Digest,
    )
