#!/usr/bin/env python3
"""
force_claude_max_oauth.py
Extract real OAuth token from Claude Desktop and force it to work
"""

import json
import base64
import re
import subprocess
import os
import sys

def extract_real_token():
    """Extract actual OAuth token from Claude Desktop config"""
    config_path = "/home/john/.config/Claude/config.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Get the base64 encoded token cache
        token_cache = config.get("oauth:tokenCache", "")
        if not token_cache:
            print("❌ No OAuth token cache found in config")
            return None
        
        # Decode base64
        decoded = base64.b64decode(token_cache).decode('utf-8', errors='ignore')
        print(f"Decoded token cache (first 500 chars):\n{decoded[:500]}...")
        
        # Find the actual API token (starts with sk-ant-api)
        match = re.search(r'sk-ant-api[^\s\"\\\\]*', decoded)
        if match:
            token = match.group(0)
            print(f"✅ Found token: {token[:50]}...")
            return token
        else:
            print("❌ No API token found in decoded cache")
            # Try alternative pattern
            match = re.search(r'\"access_token\"\s*:\s*\"([^\"]+)\"', decoded)
            if match:
                token = match.group(1)
                print(f"✅ Found token via access_token: {token[:50]}...")
                return token
    
    except Exception as e:
        print(f"❌ Error extracting token: {e}")
        import traceback
        traceback.print_exc()
    
    return None

def test_token(token):
    """Test if extracted token works"""
    if not token:
        return False
    
    try:
        # Clear conflicting environment variables
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_BASE_URL", None)
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
        
        test_prompt = "Test Claude MAX - respond with 'Claude MAX OAuth working'"
        
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", test_prompt],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            if "Claude MAX OAuth working" in result.stdout:
                print("✅ Token works perfectly!")
                return True
            else:
                print(f"⚠️  Token works but wrong response: {result.stdout[:100]}")
                return True
        else:
            print(f"❌ Token failed: {result.stderr[:200]}")
            return False
    
    except Exception as e:
        print(f"❌ Error testing token: {e}")
        return False

def update_thunderbird_cache(token):
    """Update Thunderbird's OAuth cache"""
    cache_path = "/home/john/Thunderbird/OpsCenter/.claude_oauth_cache"
    
    try:
        with open(cache_path, 'w') as f:
            f.write(f"CLAUDE_CODE_OAUTH_TOKEN={token}")
        
        print(f"✅ Updated cache: {cache_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to update cache: {e}")
        return False

def run_with_token(token, prompt):
    """Run a task with the extracted token"""
    if not token:
        print("❌ No token available")
        return
    
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_BASE_URL", None)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    
    try:
        print(f"🚀 Running prompt with extracted token...")
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", prompt],
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        
        if result.returncode == 0:
            print(f"✅ Success!\n{result.stdout}")
        else:
            print(f"❌ Failed: {result.stderr}")
    
    except subprocess.TimeoutExpired:
        print("❌ Timeout (5 minutes) - prompt too long?")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🔍 Extracting Claude MAX OAuth token...")
    token = extract_real_token()
    
    if not token:
        print("❌ Could not extract token. Alternatives:")
        print("1. Open Claude Desktop GUI and ensure logged in")
        print("2. Check ~/.config/Claude/config.json exists")
        print("3. Manually copy token from config")
        return
    
    print(f"\n🧪 Testing token...")
    if test_token(token):
        print(f"\n📝 Updating Thunderbird cache...")
        update_thunderbird_cache(token)
        
        # Run a test task
        test_prompt = "Research the latest tech for travel industry automation in 2026"
        run_with_token(token, test_prompt)
    else:
        print("\n❌ Token doesn't work. Possible issues:")
        print("1. Token expired")
        print("2. Account not subscribed to Claude MAX")
        print("3. Claude Desktop not running")
        print("\nFix: Open Claude Desktop GUI, log in, then retry")

if __name__ == "__main__":
    main()