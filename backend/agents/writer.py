from crewai import Agent, LLM
from config import GROQ_MODEL
from pydantic import BaseModel, Field


# --- Pydantic output schema ---
#
# These models define the CONTRACT between the Writer agent and the rest of the
# pipeline. When a CrewAI Task has output_pydantic=Digest, the LLM is forced to
# return JSON that matches this schema exactly — no free-form text, no guessing.
# Python then gets a real Digest object it can inspect, render, or pass along.

class ArticleScore(BaseModel):
    url: str = Field(description="The article URL")
    relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="How relevant this article is to the topic. 1.0 = essential, 0.0 = off-topic."
    )
    kept: bool = Field(description="True if relevance_score >= 0.6 and the article adds signal")
    reason: str = Field(description="One sentence: why this score and keep/discard decision")


class DigestSection(BaseModel):
    heading: str = Field(description="A specific, informative heading — not 'Summary' or 'Overview'")
    body: str = Field(description="2-3 sentences synthesizing ideas across articles, not per-article summaries")


class Digest(BaseModel):
    topic: str = Field(description="The research topic this digest covers")
    overview: str = Field(description="3-sentence executive summary of the current state of this topic")
    key_insights: list[str] = Field(
        description="3-5 specific, non-obvious insights a reader couldn't derive without reading the articles"
    )
    sections: list[DigestSection] = Field(description="Themed synthesis sections, one per major angle or pattern")
    scored_articles: list[ArticleScore] = Field(description="Relevance score for every article reviewed")
    sources: list[str] = Field(description="URLs of articles with kept=True only")
    total_articles: int = Field(description="Total number of articles evaluated")
    included_articles: int = Field(description="Number of articles with kept=True")


# --- Writer agent ---
#
# Prompt engineering lesson: compare the vague version vs what we write.
#
# VAGUE:  role="Content Writer", goal="Write a comprehensive article"
#         → LLM will write a generic blog post, ignore relevance, include everything
#
# PRECISE: role="Research Signal Editor", goal names the two-step job explicitly
#           → LLM knows it must filter first, then synthesize — not just paraphrase

def create_writer() -> Agent:
    llm = LLM(model=GROQ_MODEL)

    return Agent(
        role="Research Signal Editor",
        goal=(
            "Filter a batch of research articles by relevance to the given topic, "
            "then synthesize the keepers into a structured digest that surfaces real insight — "
            "not a list of summaries, but connected analysis across sources."
        ),
        backstory=(
            "You are a senior technical editor at a research newsletter. "
            "You receive raw search results and your job is two-fold: "
            "ruthlessly discard marketing fluff, paywalled previews, and tangential content; "
            "then write tight, insight-driven digests that help busy engineers understand "
            "what actually matters this week and why."
        ),
        llm=llm,
        verbose=True,
    )
