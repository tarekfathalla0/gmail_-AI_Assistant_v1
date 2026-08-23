from __future__ import annotations

import logging

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

from config import get_settings
from data.schemas import ExtractedMemories


logger = logging.getLogger(__name__)

settings = get_settings()


class MemoryExtractor:

    def __init__(self) -> None:

        # self._llm = ChatOpenAI(
        #     model=settings.MODEL_NAME,
        #     api_key=settings.OPENROUTER_API_KEY,
        #     base_url="https://openrouter.ai/api/v1",
        #     temperature=0,
        # )
        self._llm = ChatGroq(
            model=settings.GROQ_MODEL_NAME,
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )

        self._extractor_llm = self._llm.with_structured_output(
            ExtractedMemories,
            method="json_schema",
        )

    async def extract(
        self,
        *,
        user_message: str,
        assistant_message: str,
    ) -> ExtractedMemories:

        prompt = f"""
You are the long-term memory extraction engine for an AI Email Assistant.

Your goal is NOT to remember everything.

Your goal is to remember ONLY information that will improve future
email-related tasks such as:

- writing emails
- replying to emails
- scheduling meetings
- understanding organizations
- understanding projects
- recognizing recurring contacts
- remembering communication preferences

IMPORTANT OUTPUT RULES:

You MUST return the exact structured format defined by the system schema.

Each item in semantic MUST be a plain STRING.

Each item in episodic MUST be a plain STRING.

Each item in procedural MUST be a plain STRING.

NEVER return objects/dictionaries inside semantic, episodic, or procedural.

For example, this is VALID:

semantic:
[
    "Ahmed Mohamed is a Software Engineer in the IT department.",
    "Ahmed Mohamed's email address is ahmed@company.com."
]

This is INVALID:

semantic:
[
    {{
        "name": "Ahmed Mohamed",
        "email": "ahmed@company.com"
    }}
]

--------------------------------------------------
SEMANTIC MEMORY
--------------------------------------------------

Store durable facts useful for future email or work-related tasks.
IMPORTANT DATA OWNERSHIP RULE:

Employee information is managed by a dedicated Employee Database.

NEVER store employee master data in memory, including:

- employee names
- employee IDs
- employee email addresses
- employee departments
- employee job titles
- employee phone numbers
- employee manager relationships
- employee records returned from the Employee Agent

The Employee Database is the single source of truth for employee information.

If an employee's information appears in the conversation, do NOT store that information as semantic memory.

For example, DO NOT store:

❌ "Ahmed Mohamed is a Software Engineer in the IT department."

❌ "Ahmed Mohamed's email is ahmed@company.com."

❌ "Ahmed Mohamed has employee ID 1."

Instead, if the interaction contains an important email-related event, you may store the event without copying the employee's database attributes.

For example:

✅ "An email was sent to Ahmed Mohamed asking about the deployment schedule."

The employee's email address should NOT be included in the memory.

Examples:

- User's company
- User's job title
- User's department
- User's manager
- Team members
- Frequent contacts
- Client names
- Project names
- Products
- Company policies
- Working hours
- Time zone
- Office location
- Meeting preferences
- Email signature
- Preferred language
- Communication style
- Business relationships

Convert every memory into a concise natural-language sentence.

Example:

"Ahmed Mohamed is a Software Engineer in the IT department and his email is ahmed@company.com."

--------------------------------------------------
EPISODIC MEMORY
--------------------------------------------------

Store important work events that may matter later.

Examples:

- meetings that were scheduled
- interviews
- important decisions
- promises
- ongoing conversations
- active projects
- pending follow-ups
- deadlines
- tasks assigned by email

Example:

"An email was sent to Ahmed Mohamed asking about the deployment schedule."

Do NOT store greetings, small talk, or trivial requests.

--------------------------------------------------
PROCEDURAL MEMORY
--------------------------------------------------

Store stable instructions about how the assistant should behave.

Examples:

- "The user prefers concise professional emails."
- "The user prefers formal email communication."
- "The user prefers Arabic responses."

Do NOT store one-time instructions.

--------------------------------------------------
DO NOT STORE
--------------------------------------------------

Do not store:

- food preferences
- hobbies
- favorite movies
- favorite sports
- random opinions
- casual conversation
- temporary emotions
- temporary requests
- obvious information that only matters to the current request

Only store information likely to remain useful weeks or months later.

--------------------------------------------------
IMPORTANT
--------------------------------------------------

If nothing is worth remembering, return empty lists.

User message:

{user_message}

Assistant response:

{assistant_message}
"""

        try:

            memories = await self._extractor_llm.ainvoke(
                prompt
            )

            print("========== MEMORY EXTRACTION ==========")
            print(memories)
            print("=======================================")

            return memories

        except Exception as e:

            logger.error(
                "Memory extraction failed: %s",
                e,
                exc_info=True,
            )

            return ExtractedMemories()


memory_extractor = MemoryExtractor()