from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from config import get_settings
from data.schemas import ExtractedMemories


logger = logging.getLogger(__name__)

settings = get_settings()


class MemoryExtractor:
    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
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

Your goal is to remember ONLY information that will improve future email-related tasks such as:

- writing emails
- replying to emails
- scheduling meetings
- understanding organizations
- understanding projects
- recognizing recurring contacts
- remembering communication preferences

Return ONLY valid JSON.

No markdown.
No explanation.

Format:

{{
    "semantic": [],
    "episodic": [],
    "procedural": []
}}

========================
SEMANTIC MEMORY
========================

Store ONLY durable information that is useful for future email conversations.

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

Do NOT store:

- food preferences
- hobbies
- favorite movies
- favorite sports
- random opinions
- casual conversation
- temporary emotions

Bad examples:

❌ "I love pizza."

❌ "Today I'm tired."

❌ "I watched a movie."

Good examples:

✅ "The user works as an AI Engineer."

✅ "The user works at Hassan Allam."

✅ "The user's manager is Ahmed."

✅ "The user usually writes formal emails."

========================
EPISODIC MEMORY
========================

Store only important work events that may matter later.

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

Do NOT store:

- every conversation
- greetings
- small talk
- trivial requests

Bad:

❌ "The user said hello."

❌ "The assistant summarized an email."

Good:

✅ "Meeting with Google scheduled for Thursday at 2 PM."

✅ "The user accepted the internship offer."

✅ "Waiting for Acme Company to reply."

========================
PROCEDURAL MEMORY
========================

Store stable instructions about how the assistant should behave.

Examples:

- Always write concise emails.
- Use a formal tone.
- Always CC the manager.
- End emails with the user's signature.
- Use British English.
- Never send emails without confirmation.
- Draft emails before sending.
- Keep replies under 150 words.

Do NOT store one-time instructions.

Bad:

❌ "Reply to this email politely."

Good:

✅ "The user prefers concise professional emails."

========================
GENERAL RULES
========================

Only store memories that are likely to be useful weeks or months later.

Do not store information that is:

- temporary
- obvious from the current conversation
- unrelated to email or work
- unlikely to improve future email assistance

If nothing is worth remembering, return:

{{
    "semantic": [],
    "episodic": [],
    "procedural": []
}}

User message:
{user_message}

Assistant response:
{assistant_message}
"""

        response = await self._llm.ainvoke(prompt)

        content = response.content

        print("========== MEMORY EXTRACTION ==========")
        print(content)
        print("=======================================")

        try:
            if isinstance(content, list):
                content = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict)
                )

            content = content.strip()

            if content.startswith("```"):
                content = (
                    content
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            data = json.loads(content)

            memories = ExtractedMemories.model_validate(data)

            print("EXTRACTED:")
            print(memories)

            return memories

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(
                "Memory extraction failed: %s",
                e,
            )

            return ExtractedMemories()


memory_extractor = MemoryExtractor()