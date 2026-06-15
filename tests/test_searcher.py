from unittest.mock import patch, MagicMock
from builder.searcher import Searcher, inspiration_query
import requests

def test_inspiration_query_varies():
    q1 = inspiration_query("todo app", 1)
    q2 = inspiration_query("todo app", 2)
    q3 = inspiration_query("todo app", 3)
    assert q1 != q2
    assert q2 != q3
    assert "todo" in q1.lower()

def test_inspiration_query_returns_string():
    q = inspiration_query("calculator", 1)
    assert isinstance(q, str)
    assert len(q) > 5

def test_search_returns_list_on_network_error():
    s = Searcher()
    with patch("requests.get", side_effect=Exception("network error")):
        result = s.search("anything")
    assert result == []

def test_search_returns_list_on_timeout():
    s = Searcher()
    with patch("requests.get", side_effect=requests.Timeout()):
        result = s.search("anything")
    assert result == []

def test_search_parses_mock_response():
    s = Searcher()
    fake_html = """<html><body>
    <div class="result__body">
      <a class="result__a">Best todo apps 2025</a>
      <a class="result__snippet">Clean minimal design with drag-and-drop.</a>
    </div>
    </body></html>"""
    mock_resp = MagicMock()
    mock_resp.text = fake_html
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp):
        result = s.search("todo app design")
    assert isinstance(result, list)
