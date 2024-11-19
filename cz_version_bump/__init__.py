from __future__ import annotations

import os
import re
import typing as t
from collections import OrderedDict
from textwrap import dedent

try:
    from jinja2 import Template
except ImportError:
    from string import Template

from commitizen import defaults, git
from commitizen.cz.base import BaseCommitizen

from cz_version_bump.git import repo_name_from_git_remote
from cz_version_bump.thanks import Thanker

if t.TYPE_CHECKING:
    from commitizen.defaults import Questions

issue_id_pattern = re.compile(r"\s+\(#(\d+)\)$")


class MeltanoCommitizen(BaseCommitizen):
    bump_pattern = r"^(feat|fix|refactor|perf|break|docs|ci|chore|style|revert|test|build|packaging)(\(.+\))?(!)?"  # noqa: E501
    bump_map: t.ClassVar = OrderedDict(
        (
            (
                r"^break",
                defaults.MINOR,
            ),  # A major release can only be created explicitly.
            (r"^feat", defaults.MINOR),
            (r"^fix", defaults.PATCH),
            (r"^refactor", defaults.PATCH),
            (r"^perf", defaults.PATCH),
            (r"^docs", defaults.PATCH),
            (r"^ci", defaults.PATCH),
            (r"^chore", defaults.PATCH),
            (r"^style", defaults.PATCH),
            (r"^revert", defaults.PATCH),
            (r"^test", defaults.PATCH),
            (r"^build", defaults.PATCH),
            (r"^packaging", defaults.PATCH),
        )
    )
    commit_parser = r"^(?P<change_type>feat|fix|refactor|perf|break|docs|packaging)(?:\((?P<scope>[^()\r\n]*)\)|\()?(?P<breaking>!)?:\s(?P<message>.*)?"  # noqa: E501
    schema_pattern = r"(feat|fix|refactor|perf|break|docs|ci|chore|style|revert|test|build|packaging)(?:\((?P<scope>[^()\r\n]*)\)|\()?(?P<breaking>!)?:(\s.*)"  # noqa: E501
    schema = dedent(
        """
        <type>(<scope>): <subject>
        <BLANK LINE>
        <body>
        <BLANK LINE>
        (BREAKING CHANGE: )<footer>
    """
    ).strip("\n")
    change_type_order = [  # noqa: RUF012
        "BREAKING CHANGES",
        "✨ New",
        "🐛 Fixes",
        "⚙️ Under the Hood",
        "⚡ Performance Improvements",
        "📚 Documentation Improvements",
        "📦 Packaging changes",
    ]
    change_type_map = {  # noqa: RUF012
        "break": "BREAKING CHANGES",
        "feat": "✨ New",
        "fix": "🐛 Fixes",
        "refactor": "⚙️ Under the Hood",
        "docs": "📚 Documentation Improvements",
        "perf": "⚡ Performance Improvements",
        "packaging": "📦 Packaging changes",
    }

    def __init__(self: MeltanoCommitizen, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.repo_name = os.environ.get(
            "GITHUB_REPOSITORY", repo_name_from_git_remote()
        )
        self.thanker = Thanker(self.repo_name)

    def questions(self: MeltanoCommitizen) -> Questions:
        """Questions regarding the commit message."""
        return [
            {
                "type": "list",
                "name": "change_type",
                "choices": [
                    {"value": "feat", "name": "feat: A new feature."},
                    {"value": "fix", "name": "fix: A bug fix."},
                    {
                        "value": "refactor",
                        "name": "refactor: A code change that neither fixes a bug nor adds a feature.",  # noqa: E501
                    },
                    {
                        "value": "perf",
                        "name": "perf: A code change that improves performance.",
                    },
                    {"value": "docs", "name": "docs: A documentation change."},
                    {"value": "break", "name": "break: A breaking change."},
                    {
                        "value": "chore",
                        "name": "chore: A change that doesn't affect the meaning of the codebase.",  # noqa: E501
                    },
                    {"value": "style", "name": "style: A code style change."},
                    {"value": "revert", "name": "revert: Revert to a commit."},
                    {"value": "test", "name": "test: A test change."},
                    {"value": "build", "name": "build: A build system change."},
                    {"value": "ci", "name": "ci: A change to CI/CD."},
                    {
                        "value": "packaging",
                        "name": "packaging: A change to how the project is packaged or distributed.",  # noqa: E501
                    },
                ],
                "message": "Select the type of change you are committing",
            },
            {
                "type": "input",
                "name": "message",
                "message": "Subject",
            },
        ]

    def message(self: MeltanoCommitizen, answers: dict) -> str:
        """Format the git message."""
        message_template = Template("{{change_type}}: {{message}}")
        if getattr(Template, "substitute", None):
            return message_template.substitute(**answers)
        return message_template.render(**answers)

    def changelog_message_builder_hook(
        self: MeltanoCommitizen,
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

        # Capitalize the first letter of the message. If the message begins
        # with punctuation, it is unaffected.
        message = message[:1].upper() + message[1:]

        try:
            # Convert to int then back to str to validate that it is an integer:
            issue_id = str(int(issue_id_pattern.findall(message)[0]))
            message = issue_id_pattern.sub("", message)
        except Exception:  # noqa: BLE001, S110
            pass
        else:
            # NOTE: The "issue ID" will usually be for a pull request. GitHub considers
            # PRs to be issues in their APIs, but not vice versa.
            parsed_message["message"] = (
                f"[#{issue_id}](https://github.com/{self.repo_name}/issues/{issue_id}) {message}"  # noqa: E501
            )

        # Remove the scope because we are too inconsistent with them.
        parsed_message["scope"] = None

        # Thank third-party contributors:
        parsed_message["message"] += self.thanker.thanks_message(commit)

        # Remove the commit message body because is isn't needed for the changelog, and
        # can cause formatting issues if present.
        commit.body = ""

        return parsed_message

    def changelog_hook(
        self: MeltanoCommitizen,
        full_changelog: str,
        partial_changelog: str | None,
    ) -> str:
        """Perform custom action at the end of changelog generation.

        full_changelog: The full changelog about to being written into the file.
        partial_changelog: The new content in the changelog.

        Return:
            The full changelog.
        """
        return full_changelog
