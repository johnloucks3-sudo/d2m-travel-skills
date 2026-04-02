#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
import ssl

# Bypass SSL verify for testing if needed
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Read the vault file to extract keys
vault_path = '/home/john/Thunderbird/~~DO NOT DELETE API Keys.txt'
keys = {}
current_section = None

with open(vault_path, 'r') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        if '━━━' in line:
            current_section = line
        elif current_section and 'AI21' in current_section and 'KEY' not in keys:
            if not line.startswith('http'):
                keys['AI21'] = line
        elif current_section and 'PINECONE' in current_section:
            if line.startswith('pcsk_'):
                keys['PINECONE'] = line
            elif line.startswith('http'):
                keys['PINECONE_URL'] = line

print("--- TESTING AI21 ---")
ai21_key = keys.get('AI21')
if ai21_key:
    try:
        url = 'https://api.ai21.com/studio/v1/jamba-instruct/chat'
        headers = {
            'Authorization': f'Bearer {ai21_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
        with urllib.request.urlopen(req, context=ctx) as response:
            res_data = json.loads(response.read().decode())
            print("AI21 SUCCESS:", res_data['choices'][0]['message']['content'])
    except Exception as e:
        print("AI21 FAILED:", str(e))
else:
    print("AI21 Key not found in expected format.")

print("\n--- TESTING PINECONE ---")
pine_key = keys.get('PINECONE')
pine_url = keys.get('PINECONE_URL')
if pine_key and pine_url:
    try:
        url = f"{pine_url}/describe_index_stats"
        headers = {
            'Api-Key': pine_key,
            'Accept': 'application/json'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx) as response:
            res_data = json.loads(response.read().decode())
            print("PINECONE SUCCESS:", "Dimension:", res_data.get('dimension'), "Total Records:", res_data.get('totalRecordCount'))
    except Exception as e:
        print("PINECONE FAILED:", str(e))
else:
    print("Pinecone Key or URL not found.")

