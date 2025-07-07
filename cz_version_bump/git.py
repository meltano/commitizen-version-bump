import subprocess


def repo_name_from_git_remote() -> str:
    git_remote_output = subprocess.run(
        ("git", "remote", "-v"),
        stdout=subprocess.PIPE,
        text=True,
        check=False,
    ).stdout
    github_remote = next(x for x in git_remote_output.split() if "github.com" in x)

    # git@github.com:meltano/meltano.git -> meltano/meltano
    return github_remote.split(":")[-1][:-4]
