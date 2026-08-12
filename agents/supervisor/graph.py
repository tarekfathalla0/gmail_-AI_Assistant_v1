from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from agents.supervisor.state import SupervisorState
from agents.supervisor.agent import get_supervisor_decision

from agents.employee.agent import run_employee_agent
from agent import run_email_agent


# ============================================================
# Supervisor Node
# ============================================================

async def supervisor_node(
    state: SupervisorState,
):

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

    decision = await get_supervisor_decision(
        supervisor_context
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

    print("\n[EMPLOYEE AGENT] Started")

    user_message = state["messages"][-1].content

    result = await run_employee_agent(
        message=user_message,
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

    needs_gmail = state.get(
        "employee_required_for_gmail",
        False,
    )

    if needs_gmail:

        print(
            "[ROUTER] Employee completed → Gmail"
        )

        return "gmail"

    print(
        "[ROUTER] Employee completed → Finish"
    )

    return "finish"


# ============================================================
# Gmail Node
# ============================================================

async def gmail_node(
    state: SupervisorState,
):

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

    result = await run_email_agent(
        message=gmail_message,
        thread_id=state["thread_id"],
        user_id=state["user_id"],
    )

    response = result["messages"][-1].content

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

        "messages": [
            AIMessage(
                content=(
                    "[Gmail Agent Result]\n"
                    f"{response}"
                )
            )
        ],
    }


# ============================================================
# Finish Node
# ============================================================

async def finish_node(
    state: SupervisorState,
):

    if state.get("gmail_result"):

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
# Gmail → Finish
# ------------------------------------------------------------

builder.add_edge(
    "gmail",
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