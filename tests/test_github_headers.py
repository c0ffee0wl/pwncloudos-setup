"""Tests for src.core.github.auth_headers."""
import pytest
from src.core.github import auth_headers


def test_no_token_returns_empty(monkeypatch):
    """auth_headers() returns {} when neither GITHUB_TOKEN nor GH_TOKEN is set."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert auth_headers() == {}


def test_github_token_returns_bearer(monkeypatch):
    """auth_headers() returns a Bearer header when GITHUB_TOKEN is set."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "abc123")
    assert auth_headers() == {"Authorization": "Bearer abc123"}


def test_gh_token_honored_without_github_token(monkeypatch):
    """auth_headers() uses GH_TOKEN when GITHUB_TOKEN is absent."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", "gh_secret")
    assert auth_headers() == {"Authorization": "Bearer gh_secret"}
