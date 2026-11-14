"""本地演示后端冒烟测试：起随机端口服务，校验接口与录入拒绝口径（离线）。"""
from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from literature.server import Handler


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def _call(srv, method, path, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
    resp = conn.getresponse()
    data = json.loads(resp.read().decode("utf-8"))
    conn.close()
    return resp.status, data


def test_sources_listed(server):
    status, data = _call(server, "GET", "/api/sources")
    assert status == 200
    keys = [x["key"] for x in data["sources"]]
    assert set(keys) == {"lit", "demo", "smoke"}


def test_records_smoke_count(server):
    status, data = _call(server, "GET", "/api/records?source=smoke")
    assert status == 200 and data["count"] == 5


def test_matrix_and_verify_offline(server):
    _, mat = _call(server, "GET", "/api/matrix?source=smoke")
    assert mat["columns"][0] == "序号" and mat["count"] == 5
    _, ver = _call(server, "GET", "/api/verify?source=smoke")
    assert ver["summary"]["total"] == 5
    assert ver["summary"]["ok"] == 0  # 离线不联网，不记通过


def test_ingest_rejects_missing_year(server, tmp_path, monkeypatch):
    monkeypatch.setattr("literature.server.DEMO_OUT", tmp_path)
    status, data = _call(server, "POST", "/api/ingest", {"records": [
        {"id": "t-001", "title": "合法条目", "year": "2024", "status": "new"},
        {"id": "t-002", "title": "缺年份", "status": "new"},
    ]})
    assert status == 200
    assert data["total"] == 2 and data["imported"] == 1 and data["rejected"] == 1
    assert "year" in data["errors"][0]["errors"][0]


def test_index_html_served(server):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
    conn.request("GET", "/")
    resp = conn.getresponse()
    html = resp.read().decode("utf-8")
    conn.close()
    assert resp.status == 200 and "文献交付工作台" in html
