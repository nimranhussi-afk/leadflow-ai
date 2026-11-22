import os
import smtplib
import traceback
import urllib.parse
import json
import gspread
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load Environment Variables from .env
load_dotenv()

app = FastAPI(title="Lead Management System with Human-in-the-Loop")

# Enable CORS so your frontend index.html can talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas for validation
class LeadInput(BaseModel):
    name: str
    email: str
    phone: str
    message: str

class ProcessedLead(BaseModel):
    name: str
    email: str
    phone: str
    message: str
    category: str
    summary: str
    draft_response: str


# --- HELPER: Send Owner Notification Email with Approval Link ---
def send_email_notification(lead_name: str, lead_email: str, summary: str, draft_response: str):
    email_address = os.getenv("EMAIL_ADDRESS")
    app_password = os.getenv("EMAIL_APP_PASSWORD")
    smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")

    # Encode data safely into a clickable approval URL link
    encoded_draft = urllib.parse.quote(draft_response)
    encoded_name = urllib.parse.quote(lead_name)
    approval_link = f"http://127.0.0.1:8000/api/approve?email={lead_email}&name={encoded_name}&draft={encoded_draft}"

    msg = MIMEMultipart()
    msg["From"] = email_address
    msg["To"] = email_address
    msg["Subject"] = f"🔔 Action Required: Approve Lead for {lead_name}"

    body = f"""
You have received a new lead and the AI has prepared a draft response.

- Name: {lead_name}
- Email: {lead_email}

AI Summary:
{summary}

Suggested Draft Response:
{draft_response}

--------------------------------------------------
👉 CLICK THE LINK BELOW TO APPROVE AND SEND THIS EMAIL TO THE CLIENT:
{approval_link}
--------------------------------------------------
    """
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL(smtp_server, 465) as server:
        server.login(email_address, app_password)
        server.send_message(msg)

@app.get("/api/leads-list")
async def get_all_leads():
    try:
        credentials_file = os.getenv("GOOGLE_CREDENTIALS", "credentials.json")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        
        gc = gspread.service_account(filename=credentials_file)
        sheet = gc.open_by_key(sheet_id).sheet1
        
        # Fetch all records from the sheet
        records = sheet.get_all_records()
        return {"status": "success", "leads": records}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- ROUTE 1: Root Health Check ---
@app.get("/")
def read_root():
    return {"status": "online", "message": "Lead Management API with HITL is running."}


# --- ROUTE 2: Submit Lead (Frontend -> AI -> Sheets -> Owner Email) ---
@app.post("/api/leads/", response_model=ProcessedLead)
async def create_lead(lead: LeadInput):
    try:
        # Step 1: OpenRouter / AI Generation with JSON Parsing
        llm = ChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_BASE_URL"),
            model_name=os.getenv("MODEL", "openai/gpt-4o-mini")
        )
        
        prompt = f"""
Analyze the following lead message and return ONLY a valid JSON object with these exact keys: 
"category" (e.g., Sales, Support, General Inquiry), 
"summary" (a brief 1-2 sentence summary), and 
"draft_response" (a polite professional reply draft).

Message: {lead.message}
"""
        ai_res = llm.invoke(prompt)
        ai_text = ai_res.content if hasattr(ai_res, 'content') else str(ai_res)
        
        # Parse JSON safely
        try:
            clean_json = ai_text.replace("```json", "").replace("```", "").strip()
            parsed_data = json.loads(clean_json)
            category = parsed_data.get("category", "General Inquiry")
            summary = parsed_data.get("summary", lead.message)
            draft_response = parsed_data.get("draft_response", "Thank you for reaching out.")
        except Exception:
            category = "General Inquiry"
            summary = ai_text[:150]
            draft_response = ai_text

        # Step 2: Save lead data and AI insights into Google Sheets with "Pending" status
        credentials_file = os.getenv("GOOGLE_CREDENTIALS", "credentials.json")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        
        gc = gspread.service_account(filename=credentials_file)
        sheet = gc.open_by_key(sheet_id).sheet1
        
        sheet.append_row([
            lead.name,
            lead.email,
            lead.phone,
            lead.message,
            category,
            summary,
            draft_response,
            "Pending"  # Status column (Column H)
        ])

        # Step 3: Dispatch owner email notification containing the approval link
        send_email_notification(
            lead_name=lead.name,
            lead_email=lead.email,
            summary=summary,
            draft_response=draft_response
        )

        return ProcessedLead(
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            message=lead.message,
            category=category,
            summary=summary,
            draft_response=draft_response
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# --- ROUTE 3: Approval Endpoint (Email Link Click -> Sends Email to Client -> Updates Sheet to "Sent") ---
@app.get("/api/approve")
async def approve_and_send_lead(email: str, name: str, draft: str):
    try:
        email_address = os.getenv("EMAIL_ADDRESS")
        app_password = os.getenv("EMAIL_APP_PASSWORD")
        smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")

        # 1. Send the final approved response directly to the client's email
        msg = MIMEMultipart()
        msg["From"] = email_address
        msg["To"] = email
        msg["Subject"] = "Thank you for reaching out!"

        client_body = f"Hi {name},\n\n{draft}\n\nBest regards,\nTeam"
        msg.attach(MIMEText(client_body, "plain"))

        with smtplib.SMTP_SSL(smtp_server, 465) as server:
            server.login(email_address, app_password)
            server.send_message(msg)

        # 2. Update Google Sheet status column for this lead from "Pending" to "Sent"
        credentials_file = os.getenv("GOOGLE_CREDENTIALS", "credentials.json")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        
        gc = gspread.service_account(filename=credentials_file)
        sheet = gc.open_by_key(sheet_id).sheet1

        cell = sheet.find(email)
        if cell:
            sheet.update_cell(cell.row, 8, "Sent")  # Column 8 is your Status column

        return {
            "status": "success", 
            "message": f"Draft successfully approved, sent to {email}, and Google Sheet updated to Sent!"
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))