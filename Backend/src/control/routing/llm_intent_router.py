"""
LLM-based Intent Router.

Uses a lightweight LLM call to classify user intent from conversation context.
Replaces the deterministic embedding-based router for better accuracy.
"""

from control.models.intent import Intent
from control.models.intent_score import IntentScore
from control.models.routing_result import RoutingResult
from langchain_core.messages import HumanMessage, SystemMessage

INTENT_CLASSIFICATION_PROMPT = """Classify the user's intent into ONE category. Reply with ONLY the label.

Categories:
- book_appointment: wants to book/schedule, describes symptoms, or continuing a booking flow
- check_availability: checking what's available (not committing yet)
- reschedule_appointment: wants to move/change an existing appointment
- cancel_appointment: wants to cancel an existing appointment
- escalate: wants a human, or medical emergency
- general: greetings, thanks, goodbye, clinic info questions

Rules:
- If [Previous intent: X] is shown and the user gives a short reply (yes/no/time/name), keep the SAME intent.
- Symptoms = book_appointment.
- Only change intent if the user explicitly switches topic.

Reply with ONLY the intent label."""


class LLMIntentRouter:
    """Routes intents using an LLM call for accurate classification."""

    def __init__(self, llm):
        self.llm = llm

    def route(self, conversation_text: str) -> RoutingResult:
        """
        Classify intent from conversation text using LLM.

        Args:
            conversation_text: Recent conversation messages joined by newlines.

        Returns:
            RoutingResult with the classified intent.
        """
        messages = [
            SystemMessage(content=INTENT_CLASSIFICATION_PROMPT),
            HumanMessage(content=conversation_text),
        ]

        try:
            response = self.llm.invoke(messages)
            raw = response.content.strip().lower().replace('"', "").replace("'", "")

            # Strip any thinking tags (some models wrap in <think>)
            import re

            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

            # Parse the intent from LLM response
            intent = self._parse_intent(raw)
            print(f"\n[LLM ROUTER] Classified → {intent.value}")

            return RoutingResult(intents=[IntentScore(intent=intent, score=1.0)])

        except Exception as e:
            print(f"\n[LLM ROUTER] Error: {e}, falling back to general")
            return RoutingResult(
                intents=[IntentScore(intent=Intent.GENERAL, score=1.0)]
            )

    def _parse_intent(self, raw: str) -> Intent:
        """Parse LLM output to a valid Intent enum."""
        # Direct match
        for intent in Intent:
            if intent.value in raw:
                return intent

        # Fuzzy matching for common variations
        mapping = {
            "book": Intent.BOOK_APPOINTMENT,
            "schedule": Intent.BOOK_APPOINTMENT,
            "availability": Intent.CHECK_AVAILABILITY,
            "available": Intent.CHECK_AVAILABILITY,
            "reschedule": Intent.RESCHEDULE_APPOINTMENT,
            "move": Intent.RESCHEDULE_APPOINTMENT,
            "change": Intent.RESCHEDULE_APPOINTMENT,
            "cancel": Intent.CANCEL_APPOINTMENT,
            "escalat": Intent.ESCALATE,
            "human": Intent.ESCALATE,
            "general": Intent.GENERAL,
            "greet": Intent.GENERAL,
        }

        for keyword, intent in mapping.items():
            if keyword in raw:
                return intent

        return Intent.GENERAL
