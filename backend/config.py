from dotenv import load_dotenv

load_dotenv()

# Groq has no provider adapter in CrewAI, so cache_breakpoint never gets stripped
# before the litellm call, causing Groq to reject the request. Patch it to a no-op.
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

TOPICS = [
    "AI agent frameworks 2025",
    "large language model research",
]

# litellm prefix "groq/" tells crewai to route this through the Groq API
GROQ_MODEL = "groq/llama-3.3-70b-versatile"