from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config.settings import settings
from utils.schemas import ProcessedLead, LeadInput

class AIService:
    def __init__(self):
        self.llm=ChatOpenAI(
            model=settings.MODEL,
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE
        )

    def process_lead(self, lead: LeadInput) -> ProcessedLead:
        """Analyze lead inquiry, categorize, summarize, and draft a response using GPT-4o-mini."""

        system_prompt=(
        "You are an expert AI assistant for a professional small business. "
            "Analyze the incoming customer inquiry and provide:\n"
            "1. category: The primary category (e.g., Pricing, Technical Support, Sales, General Inquiry).\n"
            "2. summary: A concise 1-sentence summary of what the lead wants.\n"
            "3. draft_response: A polite, professional email response addressed to the lead.\n\n"
            "CRITICAL GUARDRAILS:\n"
            "- DO NOT invent prices, discounts, delivery dates, or specific business policies.\n"
            "- If exact pricing or details are missing from your knowledge, the draft_response MUST politely ask the lead for clarification or state that a team member will email them with specific details shortly.\n"
            "- Never confirm commitments or appointments on behalf of the business."
        )
        human_prompt=(
            f"Lead Name: {lead.name}\n"
            f"Email: {lead.email}\n"
            f"Phone: {lead.phone if lead.phone else 'N/A'}\n"
            f"Message: {lead.message}\n\n"
            "Return your output structured clearly."
        )
        prompt=ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt)
        ])
        strucuted_llm=self.llm.with_structured_output(ProcessedLead)
        chain= prompt | strucuted_llm

        result=chain.invoke({
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "message": lead.message
        })
        return result

ai_service = AIService()