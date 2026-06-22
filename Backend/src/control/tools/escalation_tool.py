from control.tools.base_tool import BaseTool
from pydantic import BaseModel, Field


class EscalationToolInput(BaseModel):
    reason: str = Field(description="Reason for escalation to human staff")

    conversation_id: str = Field(
        default="",
        description="UUID of the current conversation (if available)",
    )

    patient_phone: str = Field(
        default="",
        description="Patient phone number for callback (if available)",
    )


class EscalationTool(BaseTool):
    name = "escalation_tool"

    description = (
        "Escalate the conversation to a human receptionist/staff member. "
        "Use when the patient request cannot be handled by the AI."
    )

    args_schema = EscalationToolInput

    def __init__(self, conversation_service=None):
        self.conversation_service = conversation_service

    async def execute(
        self,
        reason: str,
        conversation_id: str = "",
        patient_phone: str = "",
    ):
        # If we have a conversation service and conversation_id, mark it for escalation
        if self.conversation_service and conversation_id:
            from uuid import UUID

            try:
                conv_uuid = UUID(conversation_id)
                # End the AI conversation so staff can pick it up
                self.conversation_service.end_conversation(conv_uuid)
            except (ValueError, Exception):
                pass  # Don't fail escalation if conversation update fails

        return {
            "escalated": True,
            "reason": reason,
            "conversation_id": conversation_id,
            "patient_phone": patient_phone,
            "message": (
                "Your request has been escalated to our reception staff. "
                "A team member will assist you shortly."
            ),
        }
