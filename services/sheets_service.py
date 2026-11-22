import gspread
from config.settings import settings
from utils.schemas import ProcessedLead
class GoogleSheetService:
    def __init__(self):
        self.gc = gspread.service_account(filename=settings.GOOGLE_CREDENTIALS)
        self.sheet = self.gc.open_by_key(settings.GOOGLE_SHEET_ID)
        self.worksheet = self.sheet.get_worksheet(0)  # Assuming you want the first worksheet


def save_lead(self, lead: ProcessedLead):
    "Append a processed lead row to the Google Sheet"
    row_data = [
        lead.name,
        lead.email,
        lead.phone if lead.phone else "N/A",
        lead.message,
        lead.category,
        lead.summary,
        lead.draft_response
    ]   
    self.worksheet.append_row(row_data)

sheet_service = GoogleSheetService()
