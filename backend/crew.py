from crewai import Crew, Process
from agents.scout import create_scout
from tasks.tasks import create_scout_task
from config import TOPICS


def run():
    scout = create_scout()

    for topic in TOPICS:
        print(f"\n{'='*60}")
        print(f"Searching: {topic}")
        print("=" * 60)

        task = create_scout_task(scout, topic)
        crew = Crew(
            agents=[scout],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()
        print("\n--- RESULT ---")
        print(result)


if __name__ == "__main__":
    run()
