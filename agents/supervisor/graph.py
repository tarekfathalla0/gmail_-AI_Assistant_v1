from __future__ import annotations

import logging
import re
import time
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from agents.supervisor.state import SupervisorState
from agents.supervisor.agent import get_supervisor_decision, llm

from agents.employee.agent import run_employee_agent
from agent import run_email_agent
from gmail_client import gmail_client


logger = logging.getLogger(__name__)


# ============================================================
# Supervisor Node
# ============================================================

async def supervisor_node(
    state: SupervisorState,
):

    started_at = time.perf_counter()
    step_count = state.get("step_count", 0)

    if step_count >= 5:
        print("[SUPERVISOR] Maximum steps reached.")

        return {
            "next_agent": "finish",
            "step_count": step_count,
        }

    messages = state.get("messages", [])

    employee_result = state.get("employee_result")

    # --------------------------------------------------------
    # Build conversation context
    # --------------------------------------------------------

    conversation = []

    for message in messages:

        role = getattr(
            message,
            "type",
            "unknown",
        )

        content = getattr(
            message,
            "content",
            "",
        )

        if content:

            conversation.append(
                f"{role}: {content}"
            )

    conversation_context = "\n".join(
        conversation
    )

    # --------------------------------------------------------
    # Employee context
    # --------------------------------------------------------

    if employee_result:

        employee_context = f"""
Employee information already retrieved:

{employee_result}

IMPORTANT:

The Employee Agent has already been executed for this
conversation.

Do NOT call the Employee Agent again for the same employee.

If the user now requests a Gmail operation involving
this employee, route directly to Gmail.
"""

    else:

        employee_context = """
No employee information has been retrieved yet.
"""

    # --------------------------------------------------------
    # Gmail dependency context
    # --------------------------------------------------------

    employee_required_for_gmail = state.get(
        "employee_required_for_gmail",
        False,
    )

    previous_requirement = f"""
Previous routing decision:

employee_required_for_gmail =
{employee_required_for_gmail}
"""

    # --------------------------------------------------------
    # Supervisor context
    # --------------------------------------------------------

    supervisor_context = f"""

CONVERSATION HISTORY:

{conversation_context}


{employee_context}


{previous_requirement}


Use the conversation history to resolve references such as:

- له
- لها
- هو
- هي
- ابعتله
- ابعتلها
- الشخص ده
- الموظف ده
- that person
- that employee


IMPORTANT:

If employee information is already available and the user
asks for a Gmail operation involving that employee, route
directly to Gmail.

Do NOT call the Employee Agent again.

Determine the next specialized agent.
"""

    # --------------------------------------------------------
    # Ask Supervisor LLM
    # --------------------------------------------------------

    try:
        decision = await get_supervisor_decision(
            supervisor_context
        )
    except Exception:
        logger.exception(
            "latency operation=supervisor_decision latency_ms=%.2f status=error",
            (time.perf_counter() - started_at) * 1000,
        )
        raise

    logger.info(
        "latency operation=supervisor_decision latency_ms=%.2f status=success",
        (time.perf_counter() - started_at) * 1000,
    )

    print("\n" + "=" * 70)
    print("[SUPERVISOR]")
    print("Next Agent:", decision.next_agent)
    print(
        "Needs Gmail After Employee:",
        decision.needs_gmail_after_employee,
    )
    print("Reason:", decision.reason)
    print("=" * 70)

    return {
        "next_agent": decision.next_agent,

        "employee_required_for_gmail": (
            decision.needs_gmail_after_employee
        ),

        "step_count": step_count + 1,
    }


# ============================================================
# Employee Node
# ============================================================

async def employee_node(
    state: SupervisorState,
):

    started_at = time.perf_counter()
    print("\n[EMPLOYEE AGENT] Started")

    user_message = state["messages"][-1].content

    try:
        result = await run_employee_agent(
            message=user_message,
        )
    except Exception:
        logger.exception(
            "latency operation=employee_node latency_ms=%.2f status=error",
            (time.perf_counter() - started_at) * 1000,
        )
        raise

    logger.info(
        "latency operation=employee_node latency_ms=%.2f status=success",
        (time.perf_counter() - started_at) * 1000,
    )

    print("\n[EMPLOYEE AGENT] Result:")
    print(result)

    return {
        "employee_result": result,

        "messages": [
            AIMessage(
                content=(
                    "[Employee Agent Result]\n"
                    f"{result['summary']}"
                )
            )
        ],
    }


# ============================================================
# Route After Employee
# ============================================================

def route_after_employee(
    state: SupervisorState,
):
    employee_result = state.get("employee_result")

    if not employee_result:
        print(
            "[ROUTER] No employee result → Finish"
        )
        return "finish"

    records = employee_result.get(
        "records",
        [],
    )

    if not records:
        print(
            "[ROUTER] Employee not found → Finish"
        )
        return "finish"

    needs_gmail = state.get(
        "employee_required_for_gmail",
        False,
    )

    if needs_gmail:
        print(
            "[ROUTER] Employee found → Gmail"
        )
        return "gmail"

    print(
        "[ROUTER] Employee found → Finish"
    )
    return "finish"


def _latest_email_limit(message: str) -> int | None:
    if not re.search(
        r"\b(last|latest|recent)\b|آخر|اخر",
        message,
        re.IGNORECASE,
    ):
        return None

    match = re.search(r"\b([1-9][0-9]?)\b", message)
    return min(int(match.group(1)), 50) if match else 5


def _latest_email_query(message: str) -> str | None:
    query_parts = []

    sender_match = re.search(
        r"(?:from|by)\s+([\w.+-]+(?:\.[\w-]+)*(?:@[\w.-]+)?)|"
        r"من\s+([\w.+-]+(?:\.[\w-]+)*(?:@[\w.-]+)?)",
        message,
        re.IGNORECASE,
    )
    if sender_match:
        sender = next(group for group in sender_match.groups() if group)
        query_parts.append(f"from:{sender}")

    month_names = (
        "january february march april may june july august "
        "september october november december"
    )
    month_match = re.search(
        rf"\b({month_names.replace(' ', '|')})\b|"
        r"يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يونيو|يوليو|"
        r"أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر",
        message,
        re.IGNORECASE,
    )
    if month_match:
        month_text = month_match.group(1)
        if month_text:
            month = next(
                index
                for index, name in enumerate(month_names.split(), start=1)
                if name.lower() == month_text.lower()
            )
        else:
            arabic_months = {
                "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4,
                "ابريل": 4, "مايو": 5, "يونيو": 6, "يوليو": 7,
                "أغسطس": 8, "اغسطس": 8, "سبتمبر": 9, "أكتوبر": 10,
                "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
            }
            month = arabic_months[month_match.group(0)]

        year_match = re.search(r"\b(20[0-9]{2})\b", message)
        year = int(year_match.group(1)) if year_match else datetime.now().year
        next_year = year + (month == 12)
        next_month = 1 if month == 12 else month + 1
        query_parts.extend((
            f"after:{year:04d}/{month:02d}/01",
            f"before:{next_year:04d}/{next_month:02d}/01",
        ))

    return " ".join(query_parts) or None


def _format_email_list(result) -> str:
    if not result.emails:
        return "No emails found."

    lines = [f"Here are your latest {result.total} emails:"]
    for index, email in enumerate(result.emails, start=1):
        lines.append(
            f"{index}. {email.subject or '(no subject)'} - "
            f"{email.sender} ({email.sender_email})\n"
            f"   {email.snippet}"
        )
    return "\n".join(lines)


def _requires_gmail_rewrite(message: str) -> bool:
    return bool(re.search(
        r"\b(send|reply|forward|draft|compose|write|edit)\b|"
        r"ابعت|ارسل|أرسل|رد|مسودة|اكتب|حرر|عدّل|عدل",
        message,
        re.IGNORECASE,
    ))


# ============================================================
# Gmail Node
# ============================================================

async def gmail_node(
    state: SupervisorState,
):

    started_at = time.perf_counter()
    print("\n[GMAIL AGENT] Started")

    messages = state.get(
        "messages",
        [],
    )

    # --------------------------------------------------------
    # Get ORIGINAL user request
    # --------------------------------------------------------

    original_message = None

    for message in messages:

        if isinstance(
            message,
            HumanMessage,
        ):

            original_message = message.content

    if original_message is None:

        original_message = messages[0].content

    requires_gmail_rewrite = _requires_gmail_rewrite(original_message)

    # --------------------------------------------------------
    # Employee information
    # --------------------------------------------------------

    employee_result = state.get(
        "employee_result"
    )

    if employee_result:

        gmail_message = f"""
Current user request:

{original_message}


Employee information resolved earlier:

{employee_result}


IMPORTANT:

Use the employee email from the employee information
when the user refers to the employee using words such as:

- له
- لها
- هو
- هي
- ابعتله
- ابعتلها
- الشخص ده
- الموظف ده
- that person
- that employee


Perform the requested Gmail operation.

Do not ask the user for the employee email if it is already
available above.
"""

    else:

        gmail_message = original_message

    print("\n[GMAIL AGENT] Instruction:")
    print(gmail_message)

    # --------------------------------------------------------
    # Run Gmail Agent
    # --------------------------------------------------------

    latest_limit = _latest_email_limit(original_message)
    latest_query = _latest_email_query(original_message)

    try:
        if latest_limit is not None and not requires_gmail_rewrite and not employee_result:
            if latest_query:
                direct_result = await gmail_client.search_messages(
                    query=latest_query,
                    limit=latest_limit,
                )
            else:
                direct_result = await gmail_client.list_messages(
                    limit=latest_limit,
                )
            response = _format_email_list(direct_result)
        else:
            result = await run_email_agent(
                message=gmail_message,
                thread_id=state["thread_id"],
                user_id=state["user_id"],
                pending_approval=state.get("pending_email_approval"),
            )
            response = result["messages"][-1].content
    except Exception:
        logger.exception(
            "latency operation=gmail_node latency_ms=%.2f status=error",
            (time.perf_counter() - started_at) * 1000,
        )
        raise

    logger.info(
        "latency operation=gmail_node latency_ms=%.2f status=success",
        (time.perf_counter() - started_at) * 1000,
    )

    if isinstance(
        response,
        list,
    ):

        response = "\n".join(
            block.get("text", "")
            for block in response
            if isinstance(block, dict)
        )

    print("\n[GMAIL AGENT] Result:")
    print(response)

    return {
        "gmail_result": response,
        "skip_gmail_rewrite": not requires_gmail_rewrite,

        "messages": [
            AIMessage(
                content=(
                    "[Gmail Agent Result]\n"
                    f"{response}"
                )
            )
        ],
    }


# ============================================================# ============================================================
# Gmail Response Rewrite / Email Quality Node
# ============================================================

async def rewrite_gmail_node(
    state: SupervisorState,
):
    gmail_result = state.get("gmail_result", "")

    if not gmail_result:
        return {
            "rewritten_result": gmail_result,
        }

    # --------------------------------------------------------
    # Never modify an email that is already waiting for approval
    # --------------------------------------------------------

    if "ready for approval" in gmail_result.lower():
        return {
            "rewritten_result": gmail_result,
        }

    messages = state.get("messages", [])

    user_request = ""

    for message in messages:
        if isinstance(message, HumanMessage):
            user_request = message.content

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a senior professional email editor and business
communication specialist.

Your job is to transform the Gmail Agent's raw email content
into a polished, natural, professional email that is ready
to be sent to the recipient.

You must preserve the user's original intent and factual
information while improving the quality, clarity, tone,
structure, grammar, and professionalism of the email.

============================================================
EMAIL QUALITY STANDARD
============================================================

Every email must be professionally written from beginning
to end.

The email should normally contain:

1. Subject
2. Appropriate greeting
3. Natural opening
4. Clear main message
5. Appropriate call to action when needed
6. Professional closing
7. Sender signature

============================================================
SUBJECT
============================================================

Create a concise, specific, professional subject.

The subject must:

- Clearly describe the purpose of the email.
- Be natural and human-written.
- Avoid unnecessary words.
- Avoid vague subjects such as "Hello", "Request",
  "Important", or "Question" unless appropriate.
- Match the actual content of the email.
- Never invent information.

Keep the subject reasonably short.

============================================================
GREETING
============================================================

Choose the greeting based on the context and recipient.

Examples:

Formal:
Dear Ahmed,

Professional and natural:
Hello Ahmed,

Less formal:
Hi Ahmed,

If the recipient's name is known, use it naturally.

Do not use awkward translations or overly formal language
unless the context requires it.

============================================================
OPENING
============================================================

Start naturally.

Avoid generic or robotic phrases when they add no value.

Do not write unnecessary introductions.

For simple requests, get to the point quickly.

============================================================
BODY
============================================================

The body must:

- Clearly communicate the user's intent.
- Be grammatically correct.
- Be concise without being unnaturally short.
- Use natural professional language.
- Preserve all important factual information.
- Make the requested action clear.
- Avoid repetition.
- Avoid unnecessary paragraphs.
- Avoid exaggerated politeness.
- Avoid robotic or AI-generated sounding language.

Choose the appropriate length based on the situation.

Simple request:
2–5 sentences.

Normal business email:
1–3 short paragraphs.

Complex request:
Use additional paragraphs only when necessary.

Never make a simple email unnecessarily long.

============================================================
CALL TO ACTION
============================================================

If the user is asking the recipient to do something,
make the requested action explicit and polite.

For example:

"Could you please confirm whether you will be available
tomorrow at 3:00 PM?"

or:

"Please let me know if this time works for you."

Do not add a call to action if the original email does not
require one.

============================================================
CLOSING
============================================================

Use an appropriate professional closing.

Examples:

Best regards,
Kind regards,
Best,
Thank you,

Choose based on the context.

Do not use overly formal or unnatural closings for casual
internal communication.

============================================================
SIGNATURE
============================================================

Use the sender's name if it is available from the original
email or user context.

Do not invent a name, job title, company, phone number,
or other signature information.

If the sender's name is known to be Tarek Fathalla, use:

Best regards,
Tarek Fathalla

Otherwise use only information that is explicitly available.

============================================================
LANGUAGE
============================================================

Write the email in the language appropriate for the recipient
and the original request.

If the original request is in English, produce a natural
professional English email.

If the original request is in Arabic, produce natural
professional Arabic.

Do NOT translate literally.

Write like a native professional human, not like a machine.

============================================================
FACTUAL ACCURACY
============================================================

This is extremely important.

NEVER:

- Invent facts.
- Invent dates.
- Invent times.
- Invent names.
- Invent email addresses.
- Invent meetings.
- Invent deadlines.
- Invent job titles.
- Invent commitments.
- Change numbers.
- Change the recipient.
- Change the user's requested action.

Preserve all factual information from the Gmail Agent.

If information is missing, do not fabricate it.

============================================================
EMAIL METADATA
============================================================

If the Gmail Agent provides:

To:
Subject:
Body:

preserve the recipient exactly.

You may improve the Subject and Body when appropriate,
but NEVER change the recipient email address.

============================================================
PROFESSIONALISM
============================================================

Before returning the email, silently check:

- Grammar
- Spelling
- Punctuation
- Sentence structure
- Tone
- Subject quality
- Greeting
- Closing
- Signature
- Clarity
- Appropriate length
- Factual accuracy
- Natural human wording

The final email should look like it was written by a
competent professional who sends emails regularly.

============================================================
IMPORTANT OUTPUT RULE
============================================================

Return ONLY the final Gmail response.

Do not explain what you changed.

Do not say:
"I improved the email."

Do not provide analysis.

Do not provide multiple versions.

Do not add commentary outside the email.

============================================================
APPROVAL SAFETY
============================================================

If the Gmail Agent response indicates that an email is
already prepared and waiting for user approval, do NOT
rewrite or modify it.

The approval message and the complete email content must
remain unchanged so the user can review exactly what will
be sent.

Otherwise, professionally rewrite the email as described
above.
""",
            ),
            (
                "human",
                """
Original user request:
{user_request}

Gmail Agent response:
{gmail_result}

Produce the final professional email response.
""",
            ),
        ]
    )

    chain = prompt | llm

    response = await chain.ainvoke(
        {
            "user_request": user_request,
            "gmail_result": gmail_result,
        }
    )

    rewritten_result = response.content

    if not isinstance(rewritten_result, str):
        rewritten_result = str(rewritten_result)

    return {
        "rewritten_result": rewritten_result,
    }
# ============================================================
# Finish Node
# ============================================================

async def finish_node(
    state: SupervisorState,
):

    if state.get("rewritten_result"):

        final_response = state[
            "rewritten_result"
        ]

    elif state.get("gmail_result"):

        final_response = state[
            "gmail_result"
        ]

    elif state.get("employee_result"):

        final_response = state[
            "employee_result"
        ]["summary"]

    else:

        final_response = (
            "The requested operation could not be completed."
        )

    return {
        "final_response": final_response,
    }


# ============================================================
# Supervisor Router
# ============================================================

def route_supervisor(
    state: SupervisorState,
):

    return state["next_agent"]


def route_after_gmail(state: SupervisorState):
    return "finish" if state.get("skip_gmail_rewrite") else "rewrite_gmail"


# ============================================================
# Build Graph
# ============================================================

builder = StateGraph(
    SupervisorState
)


# ------------------------------------------------------------
# Nodes
# ------------------------------------------------------------

builder.add_node(
    "supervisor",
    supervisor_node,
)

builder.add_node(
    "employee",
    employee_node,
)

builder.add_node(
    "gmail",
    gmail_node,
)

builder.add_node(
    "rewrite_gmail",
    rewrite_gmail_node,
)

builder.add_node(
    "finish",
    finish_node,
)


# ------------------------------------------------------------
# START → Supervisor
# ------------------------------------------------------------

builder.add_edge(
    START,
    "supervisor",
)


# ------------------------------------------------------------
# Supervisor → Agent
# ------------------------------------------------------------

builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "employee": "employee",
        "gmail": "gmail",
        "finish": "finish",
    },
)


# ------------------------------------------------------------
# Employee → Gmail OR Finish
# ------------------------------------------------------------

builder.add_conditional_edges(
    "employee",
    route_after_employee,
    {
        "gmail": "gmail",
        "finish": "finish",
    },
)


# ------------------------------------------------------------
# Gmail → Rewrite/Finish
# ------------------------------------------------------------

builder.add_conditional_edges(
    "gmail",
    route_after_gmail,
    {
        "rewrite_gmail": "rewrite_gmail",
        "finish": "finish",
    },
)

builder.add_edge(
    "rewrite_gmail",
    "finish",
)


# ------------------------------------------------------------
# Finish → END
# ------------------------------------------------------------

builder.add_edge(
    "finish",
    END,
)


# ============================================================
# Compile
# ============================================================

memory = InMemorySaver()

supervisor_graph = builder.compile(
    checkpointer=memory,
)