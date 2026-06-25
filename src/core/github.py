"""Shared GitHub API helpers.

Unauthenticated GitHub API access is limited to 60 requests/hour, which a full
tool sync/install easily exhausts. If GITHUB_TOKEN (or GH_TOKEN) is set in the
environment, send it as a Bearer token to raise the limit to 5000/hour.
"""

import os
from typing import Dict


def auth_headers() -> Dict[str, str]:
    """Return an Authorization header dict when a GitHub token is in the env, else {}."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}
