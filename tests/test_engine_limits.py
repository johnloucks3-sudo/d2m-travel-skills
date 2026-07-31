import tempfile
import os
import time
import json
from pathlib import Path
import pytest
from core.relay.engine_limits import record_call, usage, check_headroom, DEFAULT_CAPS

@pytest.fixture
def temp_ledger():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_ledger.jsonl"

def test_record_and_usage(temp_ledger):
    record_call('OC', tokens=100, ok=True, task='test1', ledger_path=temp_ledger)
    record_call('OC', tokens=50, ok=False, task='test2', ledger_path=temp_ledger)
    
    stats = usage('OC', ledger_path=temp_ledger)
    assert stats['hour'] == 2
    assert stats['day'] == 2

def test_independence(temp_ledger):
    cap_hourly = DEFAULT_CAPS['OC']['hourly']
    
    for _ in range(cap_hourly):
        record_call('OC', ledger_path=temp_ledger)
        
    headroom_oc = check_headroom('OC', ledger_path=temp_ledger)
    assert not headroom_oc['ok']
    
    headroom_ag = check_headroom('AG', ledger_path=temp_ledger)
    assert headroom_ag['ok']
    assert headroom_ag['hour_used'] == 0

def test_corrupt_ledger(temp_ledger):
    temp_ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_ledger, 'w') as f:
        f.write("not json\n{bad_json}\n")
        
    stats = usage('OC', ledger_path=temp_ledger)
    assert stats['hour'] == 0
    assert stats['day'] == 0
    
    headroom = check_headroom('OC', ledger_path=temp_ledger)
    assert headroom['ok']
    
def test_missing_ledger(temp_ledger):
    stats = usage('OC', ledger_path=temp_ledger)
    assert stats['hour'] == 0
    assert stats['day'] == 0
    
def test_never_crash(temp_ledger):
    temp_ledger.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(temp_ledger.parent, 0o444)
    
    try:
        record_call('OC', ledger_path=temp_ledger)
        usage('OC', ledger_path=temp_ledger)
        check_headroom('OC', ledger_path=temp_ledger)
    finally:
        os.chmod(temp_ledger.parent, 0o777)

def test_time_windows(temp_ledger):
    row_old = {
        'ts': time.time() - 7200,
        'engine': 'OC',
        'tokens': 0,
        'ok': True,
        'task': 'old'
    }
    with open(temp_ledger, 'a') as f:
        json.dump(row_old, f)
        f.write('\n')
        
    row_recent = {
        'ts': time.time() - 600,
        'engine': 'OC',
        'tokens': 0,
        'ok': True,
        'task': 'recent'
    }
    with open(temp_ledger, 'a') as f:
        json.dump(row_recent, f)
        f.write('\n')
        
    stats = usage('OC', ledger_path=temp_ledger)
    assert stats['hour'] == 1
    assert stats['day'] == 2
