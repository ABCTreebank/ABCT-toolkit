import click
import pathlib
import abctk.conversion.cli as cli_conv

cmd_main = click.Group(name = "ABC Treebank Toolkit")
cmd_main.add_command(cli_conv.cmd_main, name = "conv")

@cmd_main.command(name = "version")
def cmd_ver():
    import abctk
    print(abctk.__version__)

    import git
    try:
        repo = git.Repo(
            pathlib.Path(__file__).parent / ".."
        )
    except git.InvalidGitRepositoryError:
        pass
    else:
        is_modified: str = "Yes" if repo.is_dirty() else "No"
        r_head = repo.head

        print(
            rf"""Git Dev Info:
- Location: {r_head.abspath}
- Head: {r_head.ref}@{r_head.commit.hexsha}
- Modified: {is_modified}
            """
        )
    # === END TRY ===