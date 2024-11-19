from __future__ import annotations

import typing as t

import pytest
from commitizen import git

from cz_version_bump.thanks import Thanker

if t.TYPE_CHECKING:
    from pytest_httpserver import HTTPServer


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INPUT_GITHUB_TOKEN", "my_gh_token")


def test_thanker(httpserver: HTTPServer) -> None:
    org = "my_gh_org"
    repo = "my_gh_repo"
    base_url = httpserver.url_for("/")

    httpserver.expect_request(
        f"/repos/{org}/{repo}",
        method="GET",
    ).respond_with_json(
        {
            "id": 12,
            "name": repo,
            "organization": {"id": 34, "login": org},
            "url": f"{base_url}repos/{org}/{repo}",
        },
    )

    httpserver.expect_request(
        f"/orgs/{org}",
        method="GET",
    ).respond_with_json(
        {
            "id": 34,
            "login": org,
            "url": f"{base_url}orgs/{org}",
        },
    )

    httpserver.expect_request(
        f"/orgs/{org}/members",
        method="GET",
    ).respond_with_json(
        [
            {"id": 1, "login": "user1"},
            {"id": 2, "login": "user2"},
            {"id": 3, "login": "user3"},
        ]
    )

    sha = "abc123"
    title = "chore: I am a commit title"
    commit = git.GitCommit(sha, title)

    httpserver.expect_request(
        f"/repos/{org}/{repo}/commits/{commit.rev}",
        method="GET",
    ).respond_with_json(
        {
            "sha": commit.rev,
            "commit": {
                "author": {
                    "name": "Johnny Appleseed",
                    "email": "j.appleseed@example.com",
                    "date": "2021-01-01T00:00:00Z",
                },
            },
            "author": {
                "id": 101,
                "login": "jappleseed",
                "url": f"{base_url}users/j.appleseed",
            },
        },
    )

    thanker = Thanker(f"{org}/{repo}", base_url=base_url)
    assert thanker.thanks_message(commit) == " -- _**Thanks @jappleseed!**_"
