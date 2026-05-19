import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "llm_web_agent"
sys.path.insert(0, str(AGENT_DIR))


def reload_config(monkeypatch, **env):
    for key in (
        "LOCAL_LM_URL",
        "LOCAL_LM_MODEL",
        "SEARXNG_URL",
        "MAX_SEARCH_RESULTS",
        "REQUEST_TIMEOUT",
    ):
        monkeypatch.delenv(key, raising=False)

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop("config", None)
    return importlib.import_module("config")


def test_config_uses_local_first_defaults(monkeypatch):
    config = reload_config(monkeypatch)

    assert config.LOCAL_LM_URL == "http://127.0.0.1:1234/v1/chat/completions"
    assert config.LOCAL_LM_MODEL is None
    assert config.SEARXNG_URL == "http://127.0.0.1:8080"
    assert config.MAX_SEARCH_RESULTS == 5
    assert config.REQUEST_TIMEOUT == 15


def test_config_reads_environment_overrides(monkeypatch):
    config = reload_config(
        monkeypatch,
        LOCAL_LM_URL="http://127.0.0.1:11434/v1/chat/completions",
        LOCAL_LM_MODEL="llama3.2",
        SEARXNG_URL="http://127.0.0.1:8888",
        MAX_SEARCH_RESULTS="9",
        REQUEST_TIMEOUT="30",
    )

    assert config.LOCAL_LM_URL == "http://127.0.0.1:11434/v1/chat/completions"
    assert config.LOCAL_LM_MODEL == "llama3.2"
    assert config.SEARXNG_URL == "http://127.0.0.1:8888"
    assert config.MAX_SEARCH_RESULTS == 9
    assert config.REQUEST_TIMEOUT == 30


def test_config_falls_back_for_invalid_numeric_overrides(monkeypatch, capsys):
    config = reload_config(
        monkeypatch,
        MAX_SEARCH_RESULTS="not-a-number",
        REQUEST_TIMEOUT="-1",
    )

    assert config.MAX_SEARCH_RESULTS == 5
    assert config.REQUEST_TIMEOUT == 15
    captured = capsys.readouterr()
    assert "MAX_SEARCH_RESULTS" in captured.err
    assert "REQUEST_TIMEOUT" in captured.err
