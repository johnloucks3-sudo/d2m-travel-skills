# Claude Usage Report Task

## Objective
Extract your Claude MAX usage stats from claude.ai/settings/usage and POST them to the Thunderbird cost dashboard so they flow into Looker Studio.

## Step 1 — Browse to Usage Page

Use the `/browse` or `gstack` skill to navigate to:
```
https://claude.ai/settings/usage
```

Wait for the page to fully load. This page shows your MAX plan usage with two key numbers:
- **Sonnet weekly percentage** (e.g., "88% of weekly limit")
- **Monthly spend** (e.g., "$55.67 of $100.00")

## Step 2 — Extract the Numbers

The page has two progress bars / cards. Find and extract:

### Number A: Sonnet Weekly %
Look for text like "Sonnet" near a percentage. The format is approximately:
- `"88% of weekly Sonnet limit"`
- Or a large percentage number next to "Sonnet" label
- Extract as a float 0-100 (e.g., 88.0 for 88%)

### Number B: Monthly Spend ($)
Look for the dollar amount. The format is approximately:
- `"$55.67 of $100.00"`
- Or a dollar value next to "Monthly" / "Max plan" label
- Extract as a float (e.g., 55.67)

### Number C (optional): Monthly Limit
The max limit. Default to 100.00 if not found. Extract as float (e.g., 100.00).

Use browser developer tools / element inspection to find the exact text. Try multiple selectors:
- Look for text containing "%"
- Look for text containing "$" and "of"
- Look for cards/sections with "Sonnet" or "Max plan" headers
- Check aria labels, data attributes, and visible text content

If you can't find the exact numbers with one method, try:
- Reading the full page text content and searching for patterns
- Looking at the page HTML for data attributes with usage values
- Checking for any API calls the page makes that return JSON with the numbers

## Step 3 — Report the Data via POST

Send a POST request to the Thunderbird cost dashboard:

```
POST https://costs.d2mluxury.quest/api/claude-usage
Content-Type: application/json
X-API-Key: ***REMOVED-SECRET***
```

Body:
```json
{
  "percentage": 88.0,
  "dollars": 55.67,
  "max_limit": 100.00,
  "source": "haiku_browse"
}
```

Replace `88.0` and `55.67` with the actual values you extracted.

Use the browse tool's HTTP request capability, or if that doesn't support POST, use:
- A `requests` Python call if available
- Or `curl` via shell
- Or the browser's fetch API via console

## Step 4 — Verify

The endpoint returns:
```json
{
  "status": "ok",
  "recorded": "2026-05-20T21:45:23+00:00",
  "percentage": 88.0,
  "dollars": 55.67,
  "sheet_exported": true
}
```

Check that:
- `status` is "ok"
- `percentage` and `dollars` match what you extracted
- `sheet_exported` is true (if Google Sheets auth is set up) or false (if not yet)
- Send the response back to me so I know it worked

## Error Handling

If the page doesn't load (login wall):
- Use the `browse` skill which inherits your Chrome session — it should already be logged in
- If not logged in, navigate to claude.ai first and log in, THEN go to settings/usage

If the POST fails:
- Check the URL is correct: `https://costs.d2mluxury.quest/api/claude-usage`
- Check the API key is correct
- Try with curl: `curl -s -X POST https://costs.d2mluxury.quest/api/claude-usage -H "Content-Type: application/json" -H "X-API-Key: ***REMOVED-SECRET***" -d '{"percentage": 88.0, "dollars": 55.67}'`

If extraction fails:
- Take a screenshot of the page and describe what you see
- Read the full page HTML and search for "Sonnet", "weekly", "monthly", "%", "$"
- Check for a "Usage" or "Billing" section specifically

## Output
When done, tell me:
1. The numbers you found (Sonnet weekly %, monthly $ spent)
2. Whether the POST succeeded
3. The response from the server
