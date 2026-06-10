#!/bin/bash
# Fast Signal registration: captcha -> SMS -> verify in one shot
# Usage: ./signal_register_fast.sh "signalcaptcha://..."

CAPTCHA="$1"
NUMBER="+17196456186"
API="http://localhost:8088"

if [ -z "$CAPTCHA" ]; then
    echo "Usage: $0 'signalcaptcha://...'"
    echo ""
    echo "1. Go to: https://signalcaptchas.org/registration/generate.html"
    echo "2. Solve captcha"
    echo "3. Right-click 'Open Signal' -> Copy Link"
    echo "4. Run: $0 'PASTE_CAPTCHA_HERE'"
    exit 1
fi

echo "📡 Registering $NUMBER..."
RESULT=$(curl -s -X POST "$API/v1/register/$NUMBER" \
  -H "Content-Type: application/json" \
  -d "{\"captcha\": \"$CAPTCHA\"}")

if echo "$RESULT" | grep -q "error"; then
    echo "❌ Registration failed: $RESULT"
    exit 1
fi

echo "✅ SMS sent to Google Voice. Check voice.google.com"
echo ""
read -p "Enter 6-digit verification code: " CODE

echo "🔐 Verifying..."
VERIFY=$(curl -s -X POST "$API/v1/register/$NUMBER/verify/$CODE")

if echo "$VERIFY" | grep -q "error"; then
    echo "❌ Verification failed: $VERIFY"
    exit 1
fi

echo "✅ $NUMBER verified! Signal C2 active."
echo ""
echo "Testing send..."
curl -s -X POST "$API/v2/send" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"🦅 Hale Signal C2 is LIVE on +17196456186. Text this number to talk to Hale.\", \"number\": \"$NUMBER\", \"recipients\": [\"+17192910742\"]}"
echo ""
echo "✅ Done. Check Signal on your phone."
