"""
LLM-based Intent Router.

Uses a lightweight LLM call to classify user intent from conversation context.
Replaces the deterministic embedding-based router for better accuracy.
"""

from control.models.intent import Intent
from control.models.intent_score import IntentScore
from control.models.routing_result import RoutingResult
from langchain_core.messages import HumanMessage, SystemMessage

INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a medical clinic's AI front desk assistant.

Given the conversation context, classify the user's CURRENT intent into exactly ONE of these categories:

- book_appointment: User wants to book/schedule a new appointment, describes symptoms, or is continuing a booking flow (answering doctor/time/confirmation questions)
- check_availability: User wants to check what doctors or time slots are available (but hasn't committed to booking yet)
- reschedule_appointment: User wants to move/change/reschedule an existing appointment
- cancel_appointment: User wants to cancel an existing appointment
- escalate: User wants to speak to a human staff member, OR describes a medical emergency
- general: ONLY for greetings (hi/hello), thank you, goodbye, or factual clinic questions (hours, location). NOT for symptoms.

CRITICAL RULES:

1. CONTINUITY: If [Previous intent: X] is shown, the user is likely STILL in that flow unless they explicitly switch topics.
   - "yes", "sure", "ok", "that one", "the first", "morning", "tomorrow", "Dr. Khan" → SAME intent as previous
   - Only change intent if the user EXPLICITLY introduces a new topic (e.g., "actually, cancel my appointment instead")

2. SYMPTOMS = BOOKING: Any health complaint (pain, ache, fever, cough, dizziness) → book_appointment

3. SHORT REPLIES CONTINUE THE FLOW:
   - If assistant asked "When would you like to come in?" and user says "tomorrow" → book_appointment
   - If assistant asked "Which one to cancel?" and user says "the first one" → cancel_appointment
   - If assistant asked "Confirm the reschedule?" and user says "yes" → reschedule_appointment

4. INTENT SWITCHES (only when explicit):
   - "I want to cancel" / "cancel my appointment" → cancel_appointment (even if previously booking)
   - "reschedule it" / "move my booking" → reschedule_appointment
   - "talk to someone" / "human please" → escalate
   - "book that slot" (after checking availability) → book_appointment

Respond with ONLY the intent label. Nothing else."""


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
            HumanMessage(content=f"Conversation:\n{conversation_text}\n\nIntent:"),
        ]

        try:
            response = self.llm.invoke(messages)
            raw = response.content.strip().lower().replace('"', "").replace("'", "")

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
            "faq": Intent.GENERAL,
        }

        for keyword, intent in mapping.items():
            if keyword in raw:
                return intent

        return Intent.GENERAL
