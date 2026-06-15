import os
from datetime import datetime, timezone
from pathlib import Path

import resend
from crewai import Agent, LLM
from crewai.tools import tool
from jinja2 import Environment, FileSystemLoader

from agents.writer import Digest
from config import GROQ_MODEL

# ---------------------------------------------------------------------------
# Layer 1 — direct Resend call (no LLM involved)
#
# This is the right choice here: sending an email is a deterministic action
# that needs no reasoning. The LLM already did its job (the Digest). Using
# a plain Python function keeps this fast, cheap, and debuggable.
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def send_digest_email(digest: Digest, to_email: str) -> dict:
    resend.api_key = os.environ["RESEND_API_KEY"]

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))
    html = env.get_template("digest_email.html").render(
        digest=digest,
        date=datetime.now(timezone.utc).strftime("%B %d, %Y"),
    )

    result = resend.Emails.send({
        "from": "onboarding@resend.dev",   # Resend sandbox sender — works without domain verification
        "to": [to_email],
        "subject": f"Research Digest: {digest.topic}",
        "html": html,
    })
    return result


# ---------------------------------------------------------------------------
# Layer 2 — CrewAI @tool wrapper
#
# When SHOULD you wrap a function as a @tool vs call it directly?
#
#   Direct call  → the action is deterministic and always happens (e.g. "always
#                  send the email after writing the digest"). No LLM decision needed.
#
#   @tool        → the agent needs to DECIDE whether/when/how to call it, or needs
#                  to compose multiple tools dynamically. The LLM drives the loop.
#
# Here the dispatcher @tool is shown for learning purposes. In the run loop we
# call send_digest_email() directly (Option A) because there's no decision to make.
# ---------------------------------------------------------------------------

_TO_EMAIL = os.getenv("TO_EMAIL", "")


@tool("Send Digest Email")
def send_digest_tool(digest_json: str) -> str:
    """
    Send the research digest as a formatted HTML email via Resend.
    Input: the full Digest object serialised as a JSON string.
    Output: a confirmation string with the Resend email id.
    """
    digest = Digest.model_validate_json(digest_json)
    result = send_digest_email(digest, _TO_EMAIL)
    return f"Email sent successfully. id={result['id']}"


# ---------------------------------------------------------------------------
# Agent factory — wraps the tool in a CrewAI agent
# ---------------------------------------------------------------------------

def create_dispatcher() -> Agent:
    llm = LLM(model=GROQ_MODEL)

    return Agent(
        role="Email Dispatcher",
        goal=(
            "Send the research digest as a formatted HTML email and confirm delivery."
        ),
        backstory=(
            "You are the final step in an automated research pipeline. "
            "Your only job is to take the finished digest JSON and deliver it to the subscriber's inbox."
        ),
        tools=[send_digest_tool],
        llm=llm,
        verbose=True,
    )
