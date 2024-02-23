"""Utility to automatically highlight third-party contributions in the changelog."""

from __future__ import annotations

import os
import re
from typing import Iterable
from warnings import warn

from commitizen import git
from github import Auth, Consts, Github


class Thanker:
    co_author_pattern = re.compile(r"<(.*)>$")

    def __init__(self, repo_name: str, base_url: str = Consts.DEFAULT_BASE_URL) -> None:
        github_token = os.environ.get(
            "INPUT_GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN", None)
        )
        if github_token is None:
            warn(
                "No GitHub token provided - changelog may include "
                "thanks for first-party contributors"
            )
        self.agent = Github(auth=Auth.Token(github_token), base_url=base_url)
        self.repo = self.agent.get_repo(repo_name)
        # NOTE: The org object obtained from `self.repo.organization` has the wrong URL, so we
        # retrieve it using `get_organization` instead to get one that isn't broken.
        self.org = self.agent.get_organization(self.repo.organization.login)
        self.org_members = {member.login for member in self.org.get_members()}

    def thanks_message(self, commit: git.GitCommit) -> str:
        usernames = [
            f"@{username}" for username in self.third_party_contributors(commit)
        ]
        if not usernames:
            return ""
        template = " -- _**Thanks {}!**_"
        if len(usernames) == 1:
            return template.format(usernames[0])
        return template.format(f"{', '.join(usernames[:-1])}, and {usernames[-1]}")

    def third_party_contributors(self, commit: git.GitCommit) -> Iterable[str]:
        for contributor in self.contributors(commit):
            if contributor not in self.org_members:
                yield contributor

    def contributors(self, commit: git.GitCommit) -> Iterable[str]:
        github_commit = self.repo.get_commit(commit.rev)
        yield github_commit.author.login
        # FIXME: Cannot thank co-authors automatically until `email_to_github_username` is implemented.
        # yield from self.co_authors(github_commit.commit.message)

    def co_authors(self, commit_message: str) -> Iterable[str]:
        co_author_lines = {
            line
            for line in commit_message.splitlines()
            if line.startswith("Co-authored-by: ")
        }
        for line in co_author_lines:
            yield self.email_to_github_username(
                self.co_author_pattern.search(line).group(1)
            )

    # TODO: This method should use memoization - https://pypi.org/project/methodtools/
    def email_to_github_username(self, email: str) -> str:
        # TODO: Find a reliable way to get the GitHub username linked to a given email address.
        # The user search API was tried, but it cannot find many users given their public primary
        # GitHub emails. I'm not sure why it is not reliable, or what conditions make it work.
        raise NotImplementedError
