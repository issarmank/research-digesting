import time

from crewai import Crew, Process
from agents.scout import create_scout
from agents.curator import deduplicate
from tasks.tasks import create_scout_task
from config import TOPICS


def run():
    scout = create_scout()

    for i, topic in enumerate(TOPICS):
        if i > 0:
            print("\nPausing 60s to respect Groq TPM limit...")
            time.sleep(60)

        print(f"\n{'='*60}")
        print(f"Searching: {topic}")
        print("=" * 60)

        scout_task = create_scout_task(scout, topic)
        crew = Crew(
            agents=[scout],
            tasks=[scout_task],
            process=Process.sequential,
            verbose=True,
        )
        scout_result = crew.kickoff()

        new_articles = deduplicate(str(scout_result), topic)

        print("\n--- CURATOR RESULT ---")
        if new_articles:
            for article in new_articles:
                print(article["raw"])
                print()
        else:
            print("No new articles — all already seen.")


if __name__ == "__main__":
    run()
