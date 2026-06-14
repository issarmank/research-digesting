import time

from crewai import Crew, Process
from agents.scout import create_scout, search_topic
from agents.curator import deduplicate
from agents.writer import create_writer, Digest
from tasks.tasks import create_scout_task, create_writer_task
from config import TOPICS


def _print_digest(digest: Digest) -> None:
    width = 60
    print(f"\n{'=' * width}")
    print(f"  DIGEST: {digest.topic}")
    print(f"{'=' * width}")

    print(f"\nOVERVIEW\n{digest.overview}")

    print("\nKEY INSIGHTS")
    for insight in digest.key_insights:
        print(f"  • {insight}")

    for section in digest.sections:
        print(f"\n{section.heading.upper()}")
        print(f"  {section.body}")

    kept = digest.included_articles
    total = digest.total_articles
    print(f"\nSOURCES ({kept} of {total} articles kept)")
    for url in digest.sources:
        print(f"  {url}")

    if kept < total:
        dropped = [a for a in digest.scored_articles if not a.kept]
        print(f"\nDROPPED ({total - kept} articles — relevance < 0.6)")
        for a in dropped:
            print(f"  [{a.relevance_score:.1f}] {a.url}")
            print(f"        {a.reason}")

    print(f"{'=' * width}\n")


def run():
    scout = create_scout()
    writer = create_writer()

    for i, topic in enumerate(TOPICS):
        if i > 0:
            print("\nPausing 60s to respect Groq TPM limit...")
            time.sleep(60)

        print(f"\n{'='*60}")
        print(f"Searching: {topic}")
        print("=" * 60)

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

        print("\n--- CURATOR RESULT ---")
        if not new_articles:
            print("No new articles — all already seen.")
            continue

        print(f"{len(new_articles)} new article(s) passed deduplication.")

        # Groq's TPM limit means back-to-back LLM calls within the same topic
        # will hit the cap. A short pause lets the token window reset.
        print("\nPausing 30s before Writer call (Groq TPM limit)...")
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
            print("\n[WARNING] Structured output parsing failed. Raw writer output:")
            print(writer_result)
        else:
            _print_digest(digest)


if __name__ == "__main__":
    run()
