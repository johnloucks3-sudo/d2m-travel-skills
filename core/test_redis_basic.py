#!/usr/bin/env python3
"""
Minimal Redis test - avoids redis module version check issue
Tests basic connectivity without triggering importlib.metadata
"""
import sys
import socket

# Test 1: Direct socket connection to Redis
print("TEST 1: Direct socket connection to Redis")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 6379))
    if result == 0:
        print("✅ Redis listening on port 6379")
        sock.close()
    else:
        print("❌ Redis not responding on port 6379")
        sys.exit(1)
except Exception as e:
    print(f"❌ Connection error: {e}")
    sys.exit(1)

# Test 2: Try redis-py via subprocess (avoid module import)
print("\nTEST 2: Redis operations via subprocess redis-cli")
import subprocess
try:
    # PING test
    result = subprocess.run(['redis-cli', 'PING'], capture_output=True, text=True, timeout=2)
    if result.stdout.strip() == 'PONG':
        print("✅ redis-cli PING successful")
    else:
        print(f"❌ Unexpected PING response: {result.stdout}")
        sys.exit(1)

    # SET/GET test
    subprocess.run(['redis-cli', 'SET', 'phase1_test', 'success'], timeout=2)
    result = subprocess.run(['redis-cli', 'GET', 'phase1_test'], capture_output=True, text=True, timeout=2)
    if 'success' in result.stdout:
        print("✅ redis-cli SET/GET successful")
    else:
        print(f"❌ SET/GET failed: {result.stdout}")
        sys.exit(1)

    # Cleanup
    subprocess.run(['redis-cli', 'DEL', 'phase1_test'], timeout=2)

except subprocess.TimeoutExpired:
    print("❌ redis-cli timeout")
    sys.exit(1)
except FileNotFoundError:
    print("❌ redis-cli not found in PATH")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n✅ All Phase 1 Redis connectivity tests PASSED")
