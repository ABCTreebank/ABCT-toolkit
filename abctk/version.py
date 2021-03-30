import abctk
import pathlib
import sys
PY_VER = sys.version_info

if PY_VER >= (3, 7):
    import importlib.resources as importlib_resources
else:
    import importlib_resources
# === END IF ===
import typing

import git

def get_version_info() -> typing.Dict[str, typing.Any]:
    res = dict()

    res["version"] = abctk.__version__

    # ------------

    try:
        repo = git.Repo(
            importlib_resources.files("abctk") / ".."
        )
        r_head = repo.head
        res["git_info"] = {
            "location":     r_head.abspath,
            "head":         f"{r_head.ref}@{r_head.commit.hexsha}",
            "is_modified":  repo.is_dirty()
        }
    except git.InvalidGitRepositoryError:
        pass

    return res
# === END ===

def pprint_version_info() -> str:
    info = get_version_info()
    res = f"{info['version']}\n"
    

    git_info = info.get("git_info", None)

    if git_info:
        res += f"""
Git Dev Info:
- Location: {git_info["location"]}
- Head:     {git_info["head"]}
- Modified: {'Yes' if git_info["is_modified"] else 'No'}
"""
    # === END IF ===

    return res