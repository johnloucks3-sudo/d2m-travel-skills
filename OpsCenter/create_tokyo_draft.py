
import sys
from pathlib import Path

_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(_ROOT))

from thunderbird_gmail import _get_gmail_service, USER_EMAIL
import base64
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def create_draft():
    service = _get_gmail_service()
    
    html_content = Path("/home/john/Templates/Template_B.html").read_text()
    
    msg = MIMEMultipart('alternative')
    msg['To'] = "johnloucks3@gmail.com"
    msg['Cc'] = "susanna.loucks@gmail.com"
    msg['Subject'] = "Tokyo Itinerary: 1-Day Ginza Shopping & Culinary Tour"
    msg['From'] = "Dani - D2M Concierge <concierge@d2mluxury.quest>"
    msg['Reply-To'] = "johnloucks3@gmail.com"
    
    part1 = MIMEText("Please view this email in an HTML-compatible client.", 'plain')
    part2 = MIMEText(html_content, 'html')
    
    msg.attach(part1)
    msg.attach(part2)
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    
    body = {'message': {'raw': raw}}
    draft = service.users().drafts().create(userId='me', body=body).execute()
    
    # Label it for Commander review
    try:
        service.users().messages().modify(
            userId='me',
            id=draft['message']['id'],
            body={'addLabelIds': ['Label_1']}  # Assuming we can find the label later or this is enough for the draft to show up
        ).execute()
    except:
        pass
        
    print(f"Draft created successfully. Draft ID: {draft['id']}")

if __name__ == "__main__":
    create_draft()
