#!/usr/bin/env python3
"""
Create Bryana onboarding email draft — NDA + portal access.
Creates in d2mconcierge, labeled THUNDERBIRD-Commander-Review.
"""
import sys
sys.path.insert(0, '/home/john/Thunderbird')
from core.email.thunderbird_gmail import gmail_create_draft_sync

TO = "bryanajarboe@gmail.com"
SUBJECT = "Welcome aboard, Bryana — two things before we start"

BODY = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f7f3ea;font-family:Georgia,serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f3ea;">
<tr><td align="center" style="padding:30px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#f7f3ea;border:1px solid #c8a96e;">

  <!-- Header banner -->
  <tr>
    <td style="background:#003087;padding:20px 30px;text-align:center;">
      <span style="color:#f7f3ea;font-family:Georgia,serif;font-size:22px;font-weight:bold;letter-spacing:2px;">
        DREAMS2MEMORIES TRAVEL, LLC
      </span><br>
      <span style="color:#c8a96e;font-family:Georgia,serif;font-size:12px;letter-spacing:1px;">
        Luxury &amp; Premium Travel
      </span>
    </td>
  </tr>

  <!-- Body -->
  <tr>
    <td style="padding:35px 40px;color:#0000ff;font-family:Georgia,serif;font-size:15px;line-height:1.7;">

      <p style="margin:0 0 18px 0;color:#003087;font-size:17px;font-weight:bold;">Bryana,</p>

      <p style="margin:0 0 18px 0;">
        I'm glad you said yes. Welcome to the team.
      </p>

      <p style="margin:0 0 18px 0;">
        Before we get your Telegram channel set up and start working with client information together,
        I need two things from you. Both are quick.
      </p>

      <!-- Step 1 -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin:25px 0;">
        <tr>
          <td style="background:#003087;padding:10px 20px;border-radius:4px 4px 0 0;">
            <span style="color:#c8a96e;font-family:Georgia,serif;font-size:13px;font-weight:bold;letter-spacing:1px;">
              STEP 1 &mdash; SIGN THE NDA
            </span>
          </td>
        </tr>
        <tr>
          <td style="background:#fff8f0;border:1px solid #c8a96e;border-top:none;padding:20px 25px;">
            <p style="margin:0 0 14px 0;color:#003087;font-weight:bold;font-size:15px;">
              Read through the agreement below. If everything looks good, reply to this email with the words <em>"I accept"</em> and we're set.
            </p>
            <p style="margin:0 0 6px 0;color:#333;font-size:13px;">It is a mutual NDA — it protects you as much as it protects us.</p>
          </td>
        </tr>
      </table>

      <!-- NDA text box -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 30px 0;">
        <tr>
          <td style="background:#fdf9f4;border:2px solid #003087;padding:25px 30px;font-family:Georgia,serif;font-size:13px;color:#222;line-height:1.7;">

            <p style="margin:0 0 6px 0;text-align:center;font-size:15px;font-weight:bold;color:#003087;">MUTUAL NON-DISCLOSURE AGREEMENT</p>
            <p style="margin:0 0 16px 0;text-align:center;font-size:12px;color:#555;">
              Between: Dreams2Memories Travel, LLC (&ldquo;Company&rdquo;) and Bryana Roelke (&ldquo;Advisor&rdquo;)<br>
              Date: June 2, 2026 &nbsp;|&nbsp; Purpose: Advisor onboarding and client services collaboration
            </p>

            <p style="margin:0 0 8px 0;font-weight:bold;color:#003087;">1. Confidential Information</p>
            <p style="margin:0 0 4px 0;">&ldquo;Confidential Information&rdquo; includes:</p>
            <ul style="margin:0 0 14px 0;padding-left:20px;">
              <li>Client names, contact details, travel history, preferences, financial information, and booking records</li>
              <li>Company processes, workflows, pricing models, commission structures, and internal tools</li>
              <li>Itineraries, proposals, research briefs, and any client-facing materials before they are sent</li>
              <li>The existence and capabilities of the Company&rsquo;s AI systems and internal methodology</li>
            </ul>

            <p style="margin:0 0 8px 0;font-weight:bold;color:#003087;">2. Obligations</p>
            <p style="margin:0 0 4px 0;">Advisor agrees to:</p>
            <ul style="margin:0 0 14px 0;padding-left:20px;">
              <li>Use Confidential Information solely for providing client services on behalf of the Company</li>
              <li>Not disclose Confidential Information to any third party without prior written consent</li>
              <li>Protect Confidential Information with at least reasonable care</li>
              <li>Not use Confidential Information for any purpose other than the Engagement</li>
              <li>Return or destroy all Confidential Information upon termination of this Agreement</li>
            </ul>

            <p style="margin:0 0 8px 0;font-weight:bold;color:#003087;">3. Exclusions</p>
            <p style="margin:0 0 14px 0;">Confidential Information does not include information that is or becomes publicly available through no fault of Advisor, was known to Advisor prior to disclosure (with written evidence), or is independently developed by Advisor without use of Confidential Information.</p>

            <p style="margin:0 0 8px 0;font-weight:bold;color:#003087;">4. Term</p>
            <p style="margin:0 0 14px 0;">This Agreement begins on the date of acceptance and continues for 2 years. Confidentiality obligations survive termination indefinitely for trade secrets and for 3 years for other Confidential Information.</p>

            <p style="margin:0 0 8px 0;font-weight:bold;color:#003087;">5. No Conflict</p>
            <p style="margin:0 0 14px 0;">Advisor represents that they are not subject to any existing non-disclosure or non-compete agreement that would prevent them from working with the Company.</p>

            <p style="margin:0 0 8px 0;font-weight:bold;color:#003087;">6. Governing Law</p>
            <p style="margin:0 0 18px 0;">This Agreement shall be governed by the laws of the State of Colorado.</p>

            <p style="margin:0;text-align:center;font-size:13px;color:#003087;font-weight:bold;border-top:1px solid #c8a96e;padding-top:14px;">
              To accept: Reply to this email with the words &ldquo;<strong>I accept</strong>&rdquo;
            </p>

          </td>
        </tr>
      </table>

      <!-- Step 2 -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin:25px 0;">
        <tr>
          <td style="background:#003087;padding:10px 20px;border-radius:4px 4px 0 0;">
            <span style="color:#c8a96e;font-family:Georgia,serif;font-size:13px;font-weight:bold;letter-spacing:1px;">
              STEP 2 &mdash; ACCESS YOUR TRAINING PORTAL
            </span>
          </td>
        </tr>
        <tr>
          <td style="background:#fff8f0;border:1px solid #c8a96e;border-top:none;padding:20px 25px;">
            <p style="margin:0 0 12px 0;color:#003087;font-size:15px;">
              Your training portal is live. Everything we discussed &mdash; the FAQ, the Wing overview, the team bios,
              your curriculum &mdash; is in there waiting for you.
            </p>
            <table cellpadding="0" cellspacing="0" style="margin:14px 0;">
              <tr>
                <td style="background:#003087;padding:12px 24px;border-radius:4px;text-align:center;">
                  <a href="https://itinerary.d2mluxury.quest/" style="color:#f7f3ea;font-family:Georgia,serif;font-size:15px;text-decoration:none;font-weight:bold;letter-spacing:1px;">
                    Open Training Portal &rarr;
                  </a>
                </td>
              </tr>
            </table>
            <p style="margin:12px 0 4px 0;color:#333;font-size:13px;font-weight:bold;">Your login credentials:</p>
            <table cellpadding="6" cellspacing="0" style="border:1px solid #c8a96e;background:#fdf9f4;border-radius:4px;">
              <tr>
                <td style="padding:6px 16px;color:#003087;font-weight:bold;font-size:13px;">Username:</td>
                <td style="padding:6px 16px;color:#222;font-size:13px;font-family:Courier New,monospace;">Bryana</td>
              </tr>
              <tr>
                <td style="padding:6px 16px;color:#003087;font-weight:bold;font-size:13px;">Password:</td>
                <td style="padding:6px 16px;color:#222;font-size:13px;font-family:Courier New,monospace;">0602</td>
              </tr>
            </table>
            <p style="margin:12px 0 0 0;color:#555;font-size:12px;font-style:italic;">
              Your browser will prompt for these when you open the link. You can change the password once you're in &mdash; just let me know.
            </p>
          </td>
        </tr>
      </table>

      <p style="margin:25px 0 10px 0;">
        Once I have your &ldquo;I accept,&rdquo; we&rsquo;ll get your Telegram channel set up and you&rsquo;ll have your first conversation with Hale.
        After that, we're off and running.
      </p>

      <p style="margin:0 0 6px 0;">Looking forward to it.</p>

    </td>
  </tr>

  <!-- Signature -->
  <tr>
    <td style="padding:0 40px 35px 40px;">
      <table cellpadding="0" cellspacing="0" style="border-top:2px solid #c8a96e;padding-top:16px;width:100%;">
        <tr>
          <td>
            <p style="margin:0;font-family:Georgia,serif;font-size:14px;font-weight:bold;color:#003087;">John Loucks</p>
            <p style="margin:2px 0 0 0;font-family:Georgia,serif;font-size:12px;color:#0000ff;">Dreams2Memories Travel, LLC</p>
            <p style="margin:2px 0 0 0;font-family:Georgia,serif;font-size:12px;color:#555;">719-291-0742</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="background:#003087;padding:10px 30px;text-align:center;">
      <span style="color:#c8a96e;font-family:Georgia,serif;font-size:10px;letter-spacing:1px;">
        DREAMS2MEMORIES TRAVEL, LLC &mdash; CONFIDENTIAL
      </span>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""

if __name__ == "__main__":
    result = gmail_create_draft_sync(TO, SUBJECT, BODY)
    print(result)
