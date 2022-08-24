from __future__ import annotations

import os
import re

from commitizen import git
from commitizen.cz.base import BaseCommitizen
from commitizen.defaults import Questions

issue_id_pattern = re.compile(r"\s+\(#(\d+)\)$")


class MeltanoCommitizen(BaseCommitizen):
    commit_parser = r"^(?P<change_type>feat|fix|refactor|perf|break|docs)(?:\((?P<scope>[^()\r\n]*)\)|\()?(?P<breaking>!)?:\s(?P<message>.*)?"
    change_type_order = [
        "BREAKING CHANGES",
        "✨ New",
        "🐛 Fixes",
        "⚙️ Under the Hood",
        "⚡ Performance Improvements",
        "📚 Documentation Improvements",
    ]
    change_type_map = {
        "break": "BREAKING CHANGES",
        "feat": "✨ New",
        "fix": "🐛 Fixes",
        "refactor": "⚙️ Under the Hood",
        "docs": "📚 Documentation Improvements",
        "perf": "⚡ Performance Improvements",
    }

    def questions(self) -> Questions:
        """Questions regarding the commit message."""
        return []

    def message(self, answers: dict) -> str:
        """Format your git message."""
        return ""

    def changelog_message_builder_hook(
        self,
        parsed_message: dict[str, str],
        commit: git.GitCommit,
    ) -> dict:
        """Alter each git log line of the changelog.

        Parameters:
            parsed_message: The commit message as parsed by `self.commit_parser`.
            commit: The commit object from which the message was obtained.

        Returns:
            The updated parsed commit message to be written into the changelog.
        """
        message = parsed_message["message"]
        try:
            # Convert to int then back to str to validate that it is an integer:
            issue_id = str(int(issue_id_pattern.findall(message)[0]))
            message = issue_id_pattern.sub("", message)
        except Exception:
            pass
        else:
            repo = os.environ["GITHUB_REPOSITORY"]
            # NOTE: The "issue ID" will usually be for a pull request. GitHub considers PRs to be
            # issues in their APIs, but not vice versa.
            parsed_message[
                "message"
            ] = f"[#{issue_id}](https://github.com/{repo}/issues/{issue_id}) {message}"

        # Remove the scope because we are too inconsistent with them.
        parsed_message["scope"] = None

        # Remove the commit message body because is isn't needed for the changelog, and can cause
        # formatting issues if present.
        commit.body = ""

        return parsed_message

    def changelog_hook(self, full_changelog: str, partial_changelog: str | None) -> str:
        """Perform custom action at the end of changelog generation.

        full_changelog: The full changelog about to being written into the file.
        partial_changelog: The new content in the changelog.

        Return:
            The full changelog.
        """
        return full_changelog


# This variable is how Commitizen finds our customizations.
# See: https://commitizen-tools.github.io/commitizen/customization
discover_this = MeltanoCommitizen
