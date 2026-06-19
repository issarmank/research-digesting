import os
import time
from loguru import logger
from crewai import Crew, Process
from agents.scout import create_scout, search_topic
from agents.curator import deduplicate, save_digest
from agents.writer import create_writer, Digest
from agents.dispatcher import send_digest_email
from tasks.tasks import create_scout_task, create_writer_task
from config import TOPICS


def _log_digest(digest: Digest) -> None:
    width = 60
    sep = "=" * width
    logger.info(f"\n{sep}\n  DIGEST: {digest.topic}\n{sep}")
    logger.info(f"OVERVIEW\n{digest.overview}")

    insights = "\n".join(f"  • {i}" for i in digest.key_insights)
    logger.info(f"KEY INSIGHTS\n{insights}")

    for section in digest.sections:
        logger.info(f"{section.heading.upper()}\n  {section.body}")

    kept = digest.included_articles
    total = digest.total_articles
    sources = "\n".join(f"  {u}" for u in digest.sources)
    logger.info(f"SOURCES ({kept} of {total} articles kept)\n{sources}")

    if kept < total:
        dropped = [a for a in digest.scored_articles if not a.kept]
        dropped_lines = "\n".join(
            f"  [{a.relevance_score:.1f}] {a.url}\n        {a.reason}"
            for a in dropped
        )
        logger.info(f"DROPPED ({total - kept} articles — relevance < 0.6)\n{dropped_lines}")

    logger.info(sep)


def run(topics: list[str] | None = None) -> list[Digest]:
    active_topics = topics or TOPICS
    scout = create_scout()
    writer = create_writer()
    completed: list[Digest] = []

    for i, topic in enumerate(active_topics):
        if i > 0:
            logger.info("Pausing 60s to respect Groq TPM limit...")
            time.sleep(60)

        logger.info(f"Searching: {topic}")

        raw_results = search_topic(topic)
        scout_task = create_scout_task(scout, topic, raw_results)
        scout_crew = Crew(
            agents=[scout],
            tasks=[scout_task],
            process=Process.sequential,
            verbose=True,
        )
        scout_result = scout_crew.kickoff()

        new_articles = deduplicate(str(scout_result), topic)

        if not new_articles:
            logger.info("No new articles — all already seen.")
            continue

        logger.info(f"{len(new_articles)} new article(s) passed deduplication.")

        # Groq's TPM limit means back-to-back LLM calls within the same topic
        # will hit the cap. A short pause lets the token window reset.
        logger.info("Pausing 30s before Writer call (Groq TPM limit)...")
        time.sleep(30)

        writer_task = create_writer_task(writer, new_articles, topic)
        writer_crew = Crew(
            agents=[writer],
            tasks=[writer_task],
            process=Process.sequential,
            verbose=True,
        )
        writer_result = writer_crew.kickoff()

        digest = writer_result.pydantic
        if digest is None:
            # output_pydantic parsing failed — fall back to raw text so the run
            # doesn't silently swallow the Writer's output
            logger.warning(f"Structured output parsing failed. Raw writer output:\n{writer_result}")
        else:
            _log_digest(digest)
            save_digest(digest, topic)
            to_email = os.getenv("TO_EMAIL", "")
            if to_email:
                logger.info(f"Sending digest to {to_email}...")
                result = send_digest_email(digest, to_email)
                logger.info(f"Email sent. id={result['id']}")
            completed.append(digest)

    return completed


if __name__ == "__main__":
    run()
