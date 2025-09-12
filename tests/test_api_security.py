import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure repository root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def reload_server_with_env(env: dict):
    os.environ.update(env)
    # Ensure a clean import
    if 'agent.server' in globals():
        import sys
        sys.modules.pop('agent.server', None)
    mod = importlib.import_module('agent.server')
    importlib.reload(mod)
    return mod


def test_controller_status_no_token():
    mod = reload_server_with_env({
        'AGENT_TOKEN': '',
        'AGENT_HOST': '127.0.0.1',
    })
    client = TestClient(mod.app)
    # status endpoint is GET and open
    r = client.get('/api/status')
    assert r.status_code == 200
    j = r.json()
    assert 'ok' in j


def test_controller_token_required_and_ok():
    token = 'test123'
    mod = reload_server_with_env({
        'AGENT_TOKEN': token,
        'AGENT_HOST': '127.0.0.1',
    })
    client = TestClient(mod.app)
    # Missing token should 401
    r = client.post('/api/command', json={'action':'status'})
    assert r.status_code == 401
    # With token OK
    r = client.post('/api/command', headers={'X-Agent-Token': token}, json={'action':'status'})
    assert r.status_code == 200
    assert r.json().get('ok') is True


def test_controller_rate_limit():
    token = 't'
    mod = reload_server_with_env({
        'AGENT_TOKEN': token,
        'AGENT_HOST': '127.0.0.1',
        'RATE_LIMIT': '2/2',
    })
    client = TestClient(mod.app)
    h = {'X-Agent-Token': token}
    for i in range(2):
        r = client.post('/api/command', headers=h, json={'action':'status'})
        assert r.status_code == 200
    r = client.post('/api/command', headers=h, json={'action':'status'})
    assert r.status_code == 429


def test_mobile_token_and_validation():
    token = 'tok'
    import agent
    mod = reload_server_with_env({
        'AGENT_TOKEN': token,
        'MOBILE_HOST': '127.0.0.1',
    })
    # Import mobile app
    m = importlib.import_module('mobile_server')
    importlib.reload(m)
    client = TestClient(m.app)
    # Missing token
    r = client.post('/api/agent', json={'input': 'hello'})
    assert r.json().get('ok') is False
    # With token and JSON
    r = client.post('/api/agent', headers={'X-Agent-Token': token}, json={'input': 'hello'})
    assert r.json().get('ok') is True


def test_controller_dictate_length_limit():
    token = 't2'
    mod = reload_server_with_env({
        'AGENT_TOKEN': token,
        'AGENT_HOST': '127.0.0.1',
        'MAX_TEXT_LEN': '10',
    })
    client = TestClient(mod.app)
    h = {'X-Agent-Token': token}
    r = client.post('/api/command', headers=h, json={'action':'dictate', 'payload':{'text':'01234567890'}})
    assert r.status_code == 413


def test_mobile_requires_json_content_type():
    token = 'tok2'
    import mobile_server as m
    importlib.reload(m)
    os.environ['AGENT_TOKEN'] = token
    client = TestClient(m.app)
    r = client.post('/api/agent', headers={'X-Agent-Token': token}, data='input=hello')
    assert r.status_code == 415


def test_controller_dictate_path_executes():
    token = 't3'
    mod = reload_server_with_env({
        'AGENT_TOKEN': token,
        'AGENT_HOST': '127.0.0.1',
        'MAX_TEXT_LEN': '4000',
    })
    client = TestClient(mod.app)
    r = client.post('/api/command', headers={'X-Agent-Token': token}, json={'action':'dictate', 'payload':{'text':'hello world'}})
    # Should respond 200 with JSON structure, ok may be False depending on backend
    assert r.status_code == 200
    j = r.json()
    assert 'ok' in j
    assert 'running' in j


def test_perf_endpoint():
    mod = reload_server_with_env({
        'AGENT_TOKEN': '',
        'AGENT_HOST': '127.0.0.1',
    })
    client = TestClient(mod.app)
    r = client.get('/api/perf')
    assert r.status_code == 200
    j = r.json()
    assert j.get('ok') is True
    assert 'perf' in j


def test_docs_guard_with_token():
    token = 'secret'
    mod = reload_server_with_env({
        'AGENT_TOKEN': token,
        'AGENT_HOST': '127.0.0.1',
    })
    client = TestClient(mod.app)
    r = client.get('/docs')
    assert r.status_code == 401
    r = client.get('/docs', headers={'X-Agent-Token': token})
    assert r.status_code in (200, 307, 308)  # FastAPI may redirect
