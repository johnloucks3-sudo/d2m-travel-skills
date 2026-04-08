#!/usr/bin/env python3
"""
Send Kuklinski lifecycle chart email to Commander.
"""

import os
import sys

sys.path.append("/home/john/Thunderbird")
from core.communication.thunderbird_gmail import send_email_v2


def main():
    # Read HTML content
    with open(
        "/home/john/Thunderbird/business/client_lifecycle/Kuklinski_Morton_Lifecycle_v2.html",
        "r",
    ) as f:
        chart_html = f.read()

    # Create email body
    body_html = f"""
<html>
<body style="font-family: Georgia, serif; background-color: #f7f3ea; color: #000; padding: 20px;">
    <div style="max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <p style="color: #0000ff; font-size: 18px; margin-bottom: 20px;"><strong>KUKLINSKI MORTON LIFECYCLE CHART — Event-Driven Architecture Complete</strong></p>
        
        <p>Commander,</p>
        
        <p>First event-driven lifecycle chart built per your "flexible but firm" directive.</p>
        
        <p><strong>Architecture shift:</strong> Rigid timeline → Anchor-date model complete.</p>
        
        <div style="margin: 25px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #0000ff;">
            <p style="margin: 0;"><strong>Key features implemented:</strong></p>
            <ul style="margin-top: 10px;">
                <li>Anchor dates (Booking, Embark, FPD, Disembark)</li>
                <li>Phase transitions based on time-to-anchor calculations</li>
                <li>Staff workflow integration (A2/A6/A9 → A3)</li>
                <li>Google Forms timing protocol integration</li>
                <li>"Flexible but firm" scheduling per event triggers</li>
            </ul>
        </div>
        
        <p><strong>Kuklinski Morton Panama Canal</strong> example used as validation template.</p>
        
        <p><strong>Next steps:</strong></p>
        <ol>
            <li>Convert Furlow_Nichols_Ely_Lifecycle.html using same architecture</li>
            <li>Implement research components (fare/flight, destination, dining/lodging)</li>
            <li>Build monthly validation process</li>
            <li>Complete comprehensive travel research framework</li>
        </ol>
        
        <p style="margin-top: 30px; color: #666;">
            Wing activated per Hale protocol when Claude stalled.<br>
            Mission board updates every 2 minutes. Memory updated.
        </p>
        
        <p>Thank you</p>
    </div>
</body>
</html>
"""

    # Prepare email
    try:
        result = send_email_v2(
            to="johnloucks3@gmail.com",
            subject="Client Lifecycle Chart — Event-Driven Architecture Complete",
            html_body=body_html,
            from_address="d2mconcierge@gmail.com",
        )
        print(f"Email sent: {result}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")

        # Fallback: print content for manual sending
        print("\n--- Email Content (for manual sending) ---")
        print(f"To: johnloucks3@gmail.com")
        print(f"From: d2mconcierge@gmail.com")
        print(f"Subject: Client Lifecycle Chart — Event-Driven Architecture Complete")
        print(body_html)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
