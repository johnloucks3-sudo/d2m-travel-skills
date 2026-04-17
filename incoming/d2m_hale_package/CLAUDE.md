CLAUDE.md
Mission Brief — D2M Hale Touchpoint System Deployment
Dreams2Memories Travel, LLC — YOGA / OpenSUSE Tumbleweed
________________


WHO YOU ARE TALKING TO
You are Claude Code CLI, receiving a deployment package from John Loucks (Dreams2Memories Travel). John is not watching this run. Execute the full deployment described below. When complete, write a DEPLOYMENT_REPORT.md summarizing every action taken, every file placed, and any errors encountered.


________________


WHAT THIS PACKAGE IS
A complete email automation system for a luxury travel business. It enables an AI agent called Hale to:


1. Generate proposed client email schedules
2. Post them for John's approval
3. Auto-draft the right email into Gmail at the right time — before John thinks to ask


This package contains 10 files that need to be deployed to specific locations on YOGA.


________________


SYSTEM CONTEXT
* Machine: YOGA (OpenSUSE Tumbleweed, Linux)
* User home: /home/john
* Thunderbird root: /home/john/Thunderbird
* Python: Python 3 (/usr/bin/python3)
* Existing infrastructure: Thunderbird Wing multi-agent system, D2M-COMMAND-HUB, Hale agent, claude_inbox.md blackboard


________________


PACKAGE CONTENTS
File
	Type
	Deploy To
	CLAUDE.md
	This file
	—
	hale_draft_engine.py
	Python script
	/home/john/Thunderbird/D2M/
	hale_touchpoint_proposer.py
	Python script
	/home/john/Thunderbird/D2M/
	kuklinski_touchpoints.json
	Client schedule
	/home/john/Thunderbird/D2M/clients/
	kuklinski_profile.json
	Client profile
	/home/john/Thunderbird/D2M/clients/
	Kuklinski_Timeline_Touchpoint_Emails.md
	Email templates
	/home/john/Thunderbird/D2M/email_templates/
	Kuklinski_Discretionary_Arc_Library.md
	Email templates
	/home/john/Thunderbird/D2M/email_templates/
	Kuklinski_Lifecycle_Email_Library.md
	Email templates
	/home/john/Thunderbird/D2M/email_templates/
	Kuklinski_Email_System_Guide.md
	Reference doc
	/home/john/Thunderbird/D2M/docs/
	d2m_drive_upload.py
	Utility script
	/home/john/Thunderbird/
	

________________


DEPLOYMENT INSTRUCTIONS
Execute these steps in order. Do not skip any step. Report each result.


________________


STEP 1 — Create directory structure
Create the following directories if they do not already exist:


/home/john/Thunderbird/D2M/


/home/john/Thunderbird/D2M/clients/


/home/john/Thunderbird/D2M/email_templates/


/home/john/Thunderbird/D2M/docs/


/home/john/Thunderbird/logs/


________________


STEP 2 — Deploy all files
Copy each file from this package to its target location per the table above.


After copying each file, verify it exists at the destination with the correct size.


________________


STEP 3 — Set executable permissions
chmod +x /home/john/Thunderbird/D2M/hale_draft_engine.py


chmod +x /home/john/Thunderbird/D2M/hale_touchpoint_proposer.py


chmod +x /home/john/Thunderbird/d2m_drive_upload.py


________________


STEP 4 — Validate Python syntax on all scripts
Run syntax check on each .py file:


python3 -m py_compile /home/john/Thunderbird/D2M/hale_draft_engine.py


python3 -m py_compile /home/john/Thunderbird/D2M/hale_touchpoint_proposer.py


python3 -m py_compile /home/john/Thunderbird/d2m_drive_upload.py


Report pass/fail for each.


________________


STEP 5 — Validate JSON files
python3 -c "import json; json.load(open('/home/john/Thunderbird/D2M/clients/kuklinski_touchpoints.json')); print('kuklinski_touchpoints.json OK')"


python3 -c "import json; json.load(open('/home/john/Thunderbird/D2M/clients/kuklinski_profile.json')); print('kuklinski_profile.json OK')"


________________


STEP 6 — Check Python dependencies
Check whether these packages are available:


python3 -c "import requests; print('requests OK')"


python3 -c "from google.oauth2.credentials import Credentials; print('google-auth OK')"


python3 -c "from googleapiclient.discovery import build; print('google-api-python-client OK')"


If any are missing, install them:


pip install requests --break-system-packages


pip install google-auth google-auth-oauthlib google-api-python-client --break-system-packages


________________


STEP 7 — Run proposer status check
Verify the proposer can read the Kuklinski client data:


python3 /home/john/Thunderbird/D2M/hale_touchpoint_proposer.py \


  --client kuklinski \


  --status


Expected: A table showing 22 touchpoints with dates and statuses. If it errors, report the full error message.


________________


STEP 8 — Run draft engine dry run
Verify the draft engine can find due touchpoints without actually creating Gmail drafts:


python3 /home/john/Thunderbird/D2M/hale_draft_engine.py \


  --dry-run \


  --client kuklinski


Expected: Output listing any touchpoints due today or in the lookback window, with [DRY RUN] prefix. No Gmail drafts created.


________________


STEP 9 — Install systemd daily timer
Create the systemd service and timer files to run the draft engine every morning at 7:00 AM.


Service file at /etc/systemd/system/hale-draft-engine.service:


[Unit]


Description=Hale Draft Engine — D2M Touchpoint Email Drafter


After=network.target


[Service]


Type=oneshot


User=john


ExecStart=/usr/bin/python3 /home/john/Thunderbird/D2M/hale_draft_engine.py


StandardOutput=append:/home/john/Thunderbird/logs/hale_draft_engine.log


StandardError=append:/home/john/Thunderbird/logs/hale_draft_engine.log


[Install]


WantedBy=multi-user.target


Timer file at /etc/systemd/system/hale-draft-engine.timer:


[Unit]


Description=Run Hale Draft Engine daily at 7 AM


Requires=hale-draft-engine.service


[Timer]


OnCalendar=*-*-* 07:00:00


Persistent=true


[Install]


WantedBy=timers.target


Then enable and start the timer:


sudo systemctl daemon-reload


sudo systemctl enable hale-draft-engine.timer


sudo systemctl start hale-draft-engine.timer


sudo systemctl status hale-draft-engine.timer


If sudo is not available, note this in the report and skip — John will run this step manually.


________________


STEP 10 — Locate Gmail credential
Check whether a Gmail OAuth token already exists from the D2M-COMMAND-HUB:


find /home/john/Thunderbird -name "gmail_token.json" 2>/dev/null


find /home/john/Thunderbird -name "token.json" 2>/dev/null


find /home/john/.config -name "*gmail*" 2>/dev/null


Report what you find. Do NOT modify any credential files. If found, note the path — John needs to update the creds_path variable in hale_draft_engine.py line ~73 to point at it.


If not found, note it in the report — John needs to run the Gmail OAuth flow from D2M-COMMAND-HUB first.


________________


STEP 11 — Check D2M-COMMAND-HUB Gmail tool
Check whether the hub's Gmail tools module exists:


find /home/john/Thunderbird -name "gmail_tools.py" 2>/dev/null


find /home/john/Thunderbird -name "*command*hub*" -type d 2>/dev/null


Report what you find. Do not modify.


________________


STEP 12 — Write DEPLOYMENT_REPORT.md
Create /home/john/Thunderbird/D2M/DEPLOYMENT_REPORT.md with:


* Date and time of deployment
* Result of every step above (PASS / FAIL / SKIPPED + notes)
* Full paths of every file deployed
* Any errors with full error text
* The two commands John needs to run next:
   1. The Gmail credential path update (if needed)
   2. The first proposer run: python3 /home/john/Thunderbird/D2M/hale_touchpoint_proposer.py --client kuklinski --status


________________


WHAT SUCCESS LOOKS LIKE
At the end of this deployment:


* All files are in place at the correct paths
* Python syntax checks pass
* JSON files validate clean
* Proposer prints a 22-row status table for Kuklinski
* Draft engine dry run runs without crashing
* Systemd timer is installed (or noted as needing manual setup)
* DEPLOYMENT_REPORT.md exists at /home/john/Thunderbird/D2M/
* John knows exactly what one or two things he needs to finish manually


________________


DO NOT
* Do not modify any existing Thunderbird files outside the D2M/ directory
* Do not touch .env, blackboard.md, claude_inbox.md, or any agent config
* Do not attempt to run actual Gmail draft creation (dry-run only)
* Do not delete or overwrite files that already exist without checking first — if a conflict exists, report it and ask


________________


IF SOMETHING FAILS
Write the full error to DEPLOYMENT_REPORT.md and continue with remaining steps. Do not stop on a single failure. John can fix individual items — he needs to know the full picture.


________________




Package built April 15, 2026 — Dreams2Memories Travel, LLC Contact: johnloucks3@gmail.com · 719-291-0742