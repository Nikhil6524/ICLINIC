"""
WorkflowNode — Generic workflow node that can be configured with:
- A system prompt
- A set of tools
- An LLM

Handles the tool-calling loop: LLM call → tool execution → final LLM call.
Also detects and handles models that output tool calls as text instead of
structured tool_calls (e.g. Groq's Llama 3.3).
"""

import json
import re

from control.adapters.tool_adapter import ToolAdapter
from control.tools.base_tool import BaseTool
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage


def _extract_text_tool_calls(content: str) -> list[dict] | None:
    """
    Detect tool calls embedded as text in the response.
    Patterns: <function=tool_name>{"arg": "val"}</function>
              or {"name": "tool_name", "arguments": {...}}
    Returns parsed tool calls or None if not found.
    """
    # Pattern: <function=tool_name>{...JSON...}</function>
    # Use a greedy match for JSON content (handles nested braces)
    pattern = r"<function=(\w+)>\s*(\{.*?\})\s*</function>"
    matches = re.findall(pattern, content, re.DOTALL)

    if matches:
        calls = []
        for name, args_str in matches:
            try:
                args = json.loads(args_str)
                calls.append({"name": name, "args": args, "id": f"text_call_{name}"})
            except json.JSONDecodeError:
                continue
        return calls if calls else None

    return None


class WorkflowNode:
    def __init__(
        self,
        name: str,
        llm,
        system_prompt: str,
        tools: list[BaseTool],
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    def _build_entity_context(self, entities: dict) -> str:
        """Build a structured summary of what's already known from previous turns."""
        if not entities:
            return ""

        lines = []

        # Patient identity (pre-loaded from auth or collected during conversation)
        has_patient = bool(entities.get("patient_id"))
        has_name = bool(entities.get("first_name"))
        has_phone = bool(entities.get("phone"))
        has_email = bool(entities.get("email"))

        if has_name:
            name_str = (
                f"{entities.get('first_name', '')} {entities.get('last_name', '')}"
            )
            if has_patient:
                lines.append(
                    f"- PATIENT IDENTIFIED: {name_str} (patient_id: {entities['patient_id']})"
                )
            else:
                lines.append(f"- Patient name: {name_str}")
        if has_phone:
            lines.append(f"- Phone: {entities['phone']}")
        if has_email:
            lines.append(f"- Email: {entities['email']}")

        if entities.get("specialty"):
            lines.append(f"- Specialty: {entities['specialty']}")

        if entities.get("doctors"):
            docs = entities["doctors"]
            if isinstance(docs, list) and docs:
                for d in docs[:4]:
                    lines.append(
                        f"- Doctor: {d.get('full_name', '?')} "
                        f"(doctor_id: {d.get('doctor_id', '?')})"
                    )

        if entities.get("available_slots"):
            slots = entities["available_slots"]
            if isinstance(slots, list) and slots:
                slot_strs = [
                    f"{s.get('start', '?')} with {s.get('doctor_name', '?')} "
                    f"(doctor_id: {s.get('doctor_id', '?')})"
                    for s in slots[:6]
                ]
                lines.append(f"- Available slots: {'; '.join(slot_strs)}")

        if entities.get("appointment_type_id"):
            lines.append(f"- Appointment type ID: {entities['appointment_type_id']}")
        if entities.get("appointment_type"):
            lines.append(f"- Appointment type: {entities['appointment_type']}")

        if entities.get("date"):
            lines.append(f"- Date: {entities['date']}")

        if entities.get("doctor_name"):
            lines.append(f"- Selected doctor: {entities['doctor_name']}")

        if entities.get("doctor_id"):
            lines.append(f"- Doctor ID: {entities['doctor_id']}")

        if entities.get("appointment_id"):
            lines.append(f"- Appointment booked (ID: {entities['appointment_id']})")
        if entities.get("success") is True:
            lines.append("- Status: BOOKING CONFIRMED")
        if entities.get("email_sent"):
            lines.append("- Confirmation email: SENT")

        # Booking history (last 5 appointments for recommendations)
        if entities.get("booking_history"):
            history = entities["booking_history"]
            if isinstance(history, list) and history:
                # Separate active (BOOKED) from past bookings for clarity
                active_from_history = [
                    h for h in history if h.get("status") == "BOOKED"
                ]
                past_bookings = [h for h in history if h.get("status") != "BOOKED"]

                if active_from_history:
                    lines.append("")
                    lines.append(
                        "PATIENT'S ACTIVE UPCOMING APPOINTMENTS (for awareness only — use active_bookings_tool for IDs):"
                    )
                    for h in active_from_history:
                        lines.append(
                            f"  - {h.get('date', '?')} with {h.get('doctor_name', '?')} "
                            f"({h.get('specialty', '?')})"
                        )

                if past_bookings:
                    lines.append("")
                    lines.append(
                        "PATIENT'S PAST VISITS (use for doctor recommendations):"
                    )
                    for h in past_bookings:
                        lines.append(
                            f"  - {h.get('date', '?')} with {h.get('doctor_name', '?')} "
                            f"({h.get('specialty', '?')}) — {h.get('status', '?')}"
                        )

        # Active bookings from tool call
        if entities.get("active_bookings"):
            active = entities["active_bookings"]
            if isinstance(active, list) and active:
                lines.append("")
                lines.append(
                    "PATIENT'S ACTIVE BOOKINGS (use appointment_id from here for cancel/reschedule):"
                )
                for b in active:
                    lines.append(
                        f"  - ID: {b.get('appointment_id', '?')} | "
                        f"{b.get('start_datetime', '?')} with {b.get('doctor_name', '?')}"
                    )

        if not lines:
            return ""

        # Add explicit instruction about what's MISSING — only if patient is NOT already identified
        if has_patient:
            # Patient is fully identified from login — no need to ask for details
            lines.append("")
            lines.append(
                "PATIENT IS PRE-IDENTIFIED (logged in user). "
                "Do NOT ask for name, phone, or email. Use the patient_id above directly when booking."
            )
        else:
            missing = []
            if not has_name:
                missing.append("patient's full name")
            if not has_phone:
                missing.append("patient's phone number")
            if not has_email:
                missing.append("patient's email address")

            if missing:
                lines.append("")
                lines.append(
                    "STILL NEEDED FROM PATIENT (ASK, do NOT invent): "
                    + ", ".join(missing)
                )

        return "\n".join(lines)

    async def __call__(self, state):
        messages = state["messages"]
        entities = state.get("entities", {})

        # Adapt tools for LangChain
        llm_tools = [ToolAdapter.adapt(tool) for tool in self.tools]
        llm = self.llm.bind_tools(llm_tools) if llm_tools else self.llm

        # Build entity context string for injection
        entity_context = self._build_entity_context(entities)

        # Inject today's date so the LLM doesn't hallucinate dates
        from datetime import datetime as _dt

        today_str = _dt.now().strftime("%Y-%m-%d")
        today_readable = _dt.now().strftime("%A, %B %d, %Y")

        # Build message list with system prompt + entity context
        prompt_with_context = self.system_prompt
        prompt_with_context += f"\n\nTODAY'S DATE: {today_readable} ({today_str})"

        if entity_context:
            prompt_with_context += (
                "\n\nCURRENT CONTEXT (what you already know — do NOT re-ask):\n"
                f"{entity_context}\n\n"
                "CRITICAL RULES:\n"
                "- Read the conversation history above CAREFULLY. If the patient already answered something, do NOT ask again.\n"
                "- If patient is PRE-IDENTIFIED, do NOT ask for name/phone/email. Use patient_id directly.\n"
                "- If you recommended a doctor and the patient said 'yes', that doctor is chosen — ask for time, not the doctor again.\n"
                "- If patient details are listed as STILL NEEDED, ask for them. Do NOT invent values.\n"
                "- When calling tools, use UUIDs from context, NOT names.\n"
                "- If the patient describes EMERGENCY symptoms (severe chest pain, can't breathe, stroke, heavy bleeding), "
                "prioritize their safety — tell them to call 911/go to ER, then offer to escalate."
            )

        llm_messages = [SystemMessage(content=prompt_with_context)]
        llm_messages.extend(messages)

        # First LLM call
        try:
            response = await llm.ainvoke(llm_messages)
        except Exception as e:
            # Groq sometimes fails with tool_use_failed but includes the attempted call
            error_str = str(e)
            if "failed_generation" in error_str or "tool_use_failed" in error_str:
                # Extract the failed generation from error
                import json as _json

                try:
                    # Try to parse the error JSON from the API response
                    raw_json = (
                        error_str.split(" - ", 1)[1] if " - " in error_str else "{}"
                    )
                    err_data = _json.loads(raw_json)
                    failed_gen = err_data.get("error", {}).get("failed_generation", "")
                    text_calls = _extract_text_tool_calls(failed_gen)
                    if text_calls:
                        # Create a fake response so we can process the tool calls
                        from langchain_core.messages import AIMessage as _AIM

                        response = _AIM(content=failed_gen)
                        response.tool_calls = []  # We'll use text_tool_calls path
                    else:
                        # No valid tool calls found — return a safe fallback
                        print(
                            f"[{self.name.upper()}] tool_use_failed but no parseable calls, returning fallback"
                        )
                        return {
                            "response": "I'm sorry, I encountered an issue processing that. Could you try again?"
                        }
                except (ValueError, KeyError, _json.JSONDecodeError):
                    # JSON parsing failed — return a safe fallback instead of crashing
                    print(
                        f"[{self.name.upper()}] Error parsing failed_generation, returning fallback"
                    )
                    return {
                        "response": "I'm sorry, I encountered an issue processing that. Could you try again?"
                    }
            else:
                raise

        # Check for text-based tool calls (model writing tool calls as text)
        text_tool_calls = None
        if not response.tool_calls and response.content:
            text_tool_calls = _extract_text_tool_calls(response.content)
            if text_tool_calls:
                print(
                    f"\n[{self.name.upper()}] Detected text-based tool calls: {[c['name'] for c in text_tool_calls]}"
                )

        tool_calls = response.tool_calls or text_tool_calls

        print(f"\n[{self.name.upper()}] LLM response (tool_calls: {bool(tool_calls)})")

        # No tool calls — return direct response (but strip any accidental function text)
        if not tool_calls:
            content = response.content or ""
            # Strip any leftover <function> tags from response
            content = re.sub(
                r"<function=\w+>\s*\{[^}]*\}\s*</function>", "", content
            ).strip()
            return {
                "messages": [AIMessage(content=content)],
                "response": content,
                "entities": entities,
            }

        # Execute tool calls
        llm_messages.append(response)
        updated_entities = dict(entities)

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"[{self.name.upper()}] Tool call: {tool_name}({tool_args})")

            tool = self.tool_map.get(tool_name)

            if tool is None:
                result = {
                    "error": f"Tool '{tool_name}' not available in this workflow."
                }
            else:
                try:
                    result = await tool.execute(**tool_args)
                except Exception as e:
                    result = {"error": str(e)}

            print(f"[{self.name.upper()}] Tool result: {result}")

            # Update entities with tool output
            if isinstance(result, dict):
                updated_entities.update(result)

            tool_call_id = tool_call.get("id", f"call_{tool_name}")
            llm_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                )
            )

        # Final LLM call with tool results (use tools-bound LLM)
        try:
            final_response = await llm.ainvoke(llm_messages)
        except Exception:
            try:
                final_response = await self.llm.ainvoke(llm_messages)
            except Exception:
                final_response = None

        print(f"[{self.name.upper()}] Final response generated")

        # Handle chained tool calls — model wants to call more tools after first results
        max_chains = 5
        chain_count = 0
        while (
            final_response
            and getattr(final_response, "tool_calls", None)
            and chain_count < max_chains
        ):
            chain_count += 1
            llm_messages.append(final_response)
            for tc in final_response.tool_calls:
                t_name = tc["name"]
                t_args = tc["args"]
                print(
                    f"[{self.name.upper()}] Chained tool call #{chain_count}: {t_name}({t_args})"
                )
                t = self.tool_map.get(t_name)
                if t:
                    try:
                        r = await t.execute(**t_args)
                    except Exception as ex:
                        r = {"error": str(ex)}
                    if isinstance(r, dict):
                        updated_entities.update(r)
                    print(f"[{self.name.upper()}] Chained result: {r}")
                    llm_messages.append(
                        ToolMessage(
                            content=str(r), tool_call_id=tc.get("id", f"chain_{t_name}")
                        )
                    )
                else:
                    llm_messages.append(
                        ToolMessage(
                            content=str({"error": f"Tool '{t_name}' not found"}),
                            tool_call_id=tc.get("id", f"chain_{t_name}"),
                        )
                    )

            try:
                final_response = await llm.ainvoke(llm_messages)
            except Exception:
                final_response = None
                break

        # Extract text content
        if (
            final_response
            and getattr(final_response, "content", None)
            and final_response.content.strip()
        ):
            response_content = final_response.content
        else:
            # Fallback: if we executed tools but got no final text,
            # generate a contextual response based on what happened
            if updated_entities.get("success") is True:
                # Booking/reschedule succeeded
                response_content = "All done! Your appointment has been confirmed. I've sent a confirmation email too."
            elif updated_entities.get("status") == "CANCELLED":
                response_content = "Done, your appointment has been cancelled. I've sent a confirmation email."
            elif updated_entities.get("escalated"):
                response_content = (
                    "I've flagged this for our team. Someone will be with you shortly."
                )
            elif updated_entities.get("email_sent"):
                response_content = (
                    "All set! I've sent you a confirmation email with the details."
                )
            else:
                response_content = "Let me know how you'd like to proceed."

        # Strip any function tags from final response
        response_content = re.sub(
            r"<function=\w+>\s*\{[^}]*\}\s*</function>", "", response_content
        ).strip()

        return {
            "messages": [AIMessage(content=response_content)],
            "response": response_content,
            "entities": updated_entities,
        }
