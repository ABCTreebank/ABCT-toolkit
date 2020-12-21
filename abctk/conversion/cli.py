import typing
import enum
import logging
logger = logging.getLogger(__name__)

import pathlib
import click

import abctk.config as CONF
from . import core


# ========================
# Misc
# ========================
class FileList:
    files: typing.List[pathlib.Path]

    def __init__(self, paths: typing.Iterable[pathlib.Path]):
        self.files = list(paths)
    # === END ===

    @classmethod
    def from_folder(cls, path: typing.Union[str, pathlib.PurePath]) -> "FileList":
        path_to_check: pathlib.Path

        if isinstance(path, pathlib.Path):
            path_to_check = path
        elif isinstance(path, pathlib.PurePath):
            path_to_check = pathlib.Path(path)
        elif isinstance(path, str):
            path_to_check = pathlib.Path(path.strip())
        else:
            raise TypeError()
        # === END IF ===

        if not path_to_check.is_dir():
            raise ValueError()
        else:
            pass
        # === END IF ===

        return cls(
            filter(
                lambda p: p.is_file(), 
                path_to_check.glob("**/*")
            )
        )
    # === END ===

    @classmethod
    def from_file_list(
        cls, 
        flist: typing.Iterable[
            typing.Union[
                str,
                pathlib.PurePath
            ]
        ]
    ) -> "FileList":
        res: typing.List[pathlib.Path] = []

        for f in flist:
            path_to_check: pathlib.Path

            if isinstance(f, pathlib.Path):
                path_to_check = f
            elif isinstance(f, pathlib.PurePath):
                path_to_check = pathlib.Path(f)
            elif isinstance(f, str):
                path_to_check = pathlib.Path(f.strip())
            else:
                raise TypeError()
            # === END IF ===

            if path_to_check.is_file():
                pass
            else:
                raise ValueError(f"The path {f} is not a file")
            # === END IF ===
        
            res.append(path_to_check)
        # === END FOR f ===

        return cls(res)
    # === END ===

    def iterate_absolute(self) -> typing.Iterator[typing.Tuple[pathlib.Path, pathlib.Path]]:
        return map(lambda p: p.absolute(), self.files)
    # === END ===

    def iterate_truncating_commonprefix(self) -> typing.Iterator[pathlib.PurePath]:
        files_abs: typing.List[pathlib.Path] = list(self.iterate_absolute())

        parents_abs_path_parts: typing.Iterator[typing.List[str]] = map(
            lambda p: p.parent.parts,
            files_abs
        )

        common_prefixes_num: int = sum(
            map(
                lambda _: 1,
                filter(
                    lambda s: len(s) == 1,
                    map(set, zip(*(parents_abs_path_parts)))
                )
            )
        )

        for fabs in files_abs:
            yield (fabs, pathlib.PurePath("/".join(fabs.parts[common_prefixes_num:])))
        # === END FOR fabs ===
    # === END ===
# === END CLASS ===

# ========================
# Commandline Components
# ========================

class SourceMode(enum.Enum):
    FOLDER = "folder"
    FILELIST = "filelist"
    STDIN = "stdin"
# === END CLASS ===

class SourceParamType(click.ParamType):
    name = "source"

    def convert(self, value: str, param, ctx) -> typing.Tuple[SourceMode, typing.Optional[str]]:
        if not value:
            self.fail(
                "expected a specification of the input source, but got an empty one",
                param,
                ctx
            )
        # === END IF ===

        value_analyzed: typing.List[str] = value.split(":", maxsplit = 1)
        mode: str = value_analyzed[0]

        if mode == SourceMode.FOLDER.value:
            if len(value_analyzed) < 2:
                self.fail(
                    "expect a folder after the source specification, but got none",
                    param,
                    ctx
                )
            else:
                return (SourceMode.FOLDER, value_analyzed[1])
            # === END IF ===
        elif mode == SourceMode.FILELIST.value:
            return (SourceMode.FILELIST, None)
        elif mode == SourceMode.STDIN.value:
            return (SourceMode.STDIN, None)
        else:
            self.fail(
                "expect a type of the input source (folder, filelist, or stdin), but got "
                f"{mode}",
                param,
                ctx
            )
        # === END IF ===

        return (None, None) # by default
    # === END ===
# === END CLASS ===

@click.command()
@click.argument(
    "source",
    type = SourceParamType()
)
@click.argument(
    "destination",
    type = click.Path(file_okay = False, dir_okay = True)
)
@click.option(
    "-o", "--overwrite/--no-overwrite", "can_overwrite",
    default = False,
)
@click.option(
    "-c", "--config", "user_config",
    type = click.File(mode = "r"),
    help = "Path to the user custom option file (in the YAML format)."
)
@click.option(
    "-d", "--debug/--no-debug", "is_debug",
    default = False,
)
@click.option(
    "-l", "--log-level", "log_level",
    type = str,
    default = logging.WARNING,
)
@click.option(
    "--logfile", "logfile",
    type = click.Path(
        exists = False, 
        file_okay = True,
        dir_okay = False,
        writable = True
    ),
    default = None,
    help = """
        Path to the log file. No output if not set.
    """
)
def cmd_main(
    source: typing.Tuple[SourceMode, typing.Optional[str]],
    destination: pathlib.Path,
    can_overwrite: bool, 
    user_config: typing.TextIO,
    is_debug: bool,
    log_level: str,
    logfile: typing.Optional[typing.TextIO],
) -> typing.NoReturn:
    """\b
        SOURCE is the source of Keyaki trees that are to be converted into ABC Trees.
        Format of SOURCE: either one of the following:
        - folder:<path>
            where <path> is a path to a folder that contains Keyaki tree files
        - filelist
            where a list of paths of Keyaki tree files, separated by line breaks, is given to STDIN
        - stdin
            trees loaded from STDIN 

        DESTINATION is a path to a folder that stores the resulting files.
        DESTINATION must be empty unless the `overwrite' flag is on.
        When SOURCE is stdin, DESTINATION is ignored 

        \b
        Patterns:
        - abc-convert folder:some/treebank another/destination
        - ls -d some/treebank/**/*.psd | abc-convert filelist another/destination 
        - cat some trees*.psd | abc-convert stdin - > result.psd
    """
    # Configure logging
    # TODO: is this working?
    if isinstance(log_level, int):
        if log_level > 0:
            pass
        else:
            logging.error("Value not in the range for the --log-level option")
            raise ValueError()
        # === END IF ===
    elif isinstance(log_level, str):
        if log_level.isdigit:
            log_level = int(log_level)
        else:
            log_level = str.upper(log_level)
        # === END IF ===
    else:
        logging.error("Wrong type for the --log-level option")
        raise TypeError()
    # === END IF ===
    
    if logfile:
        logging.basicConfig(
            filename = logfile,
            level = log_level,
        )
        logger.info("Verbose log enabled")
    else:
        logger.setLevel(log_level)
    # === END IF ===

    # Build config
    from dictknife import deepmerge
    import ruamel.yaml
    yaml = ruamel.yaml.YAML()
    import xdg
    import os

    CONFIG: typing.Dict[str, typing.Any] = CONF.CONF_DEFAULT
    path_config_user: pathlib.Path = xdg.xdg_config_home() / "ABCTreebank.yaml"
    if os.path.exists(path_config_user):
        with open(path_config_user, "r") as cu:
            CONFIG = deepmerge(CONFIG, cu, mode = "merge")
        # === END WITH cu ===
    # === END IF ===

    if user_config:
        CONFIG = deepmerge(CONFIG, user_config, mode = "merge")
    # === END IF ===

    # Check the system runtimes
    import sys

    runtime_check_res: int = core.check_runtimes(CONFIG["bin-sys"])
    if runtime_check_res:
        sys.exit(runtime_check_res)
    else:
        pass
    # === END IF ===

    # Find the source
    mode, folder = source
    flist: typing.Optional[FileList]

    if mode == SourceMode.FOLDER:
        # mode: FOLDER, folder: Path, flist = files in folder
        flist = FileList.from_folder(folder)
    elif mode == SourceMode.FILELIST:
        # mode: FILELIST, folder: None, flist = parsed from stdin
        flist = FileList.from_file_list(sys.stdin)
    elif mode == SourceMode.STDIN:
        # mode: FILELIST, folder: None, flist = None
        flist = None
    # === END IF ===

    if flist:
        import multiprocessing as mp
        import tqdm
        
        os.makedirs(destination, exist_ok = True)
        proc_num: int = CONFIG["max_process_num"]
        with mp.Pool(processes = proc_num) as pool:
            logger.info(f"Number of processes: {proc_num}")

            flist_dest_expanded: typing.List[
                typing.Tuple[pathlib.Path, pathlib.Path, int]
            ] = list(
                (src, destination / fn, os.path.getsize(src)) 
                for src, fn 
                in flist.iterate_truncating_commonprefix()
            )
            files_total_size: int = sum(
                map(lambda x: x[2], flist_dest_expanded)
            )
            
            jobs = pool.imap_unordered(
                __conv_file_wrapper,
                flist_dest_expanded
            )
            with tqdm.tqdm(
                total = files_total_size, 
                unit = "B",
                unit_scale = True,
                unit_divisor = 1024
            ) as pb:
                pb.write("Converting Keyaki trees into ABC trees:")
                for res, src_size in jobs:
                    pb.update(src_size)
            # === END WITH pb ===
        # === END FOR path_src, filename_res ===
    else:
        core.convert_keyaki_to_abc(
            sys.stdin, "<STDIN>",
            sys.stdout, "<STDOUT>"
        )
    # === END IF ===
# === END ===

def __conv_file_wrapper(arg_tuple):
    return (
        core.convert_keyaki_file_to_abc(arg_tuple[0], arg_tuple[1]),
        arg_tuple[2]
    )
# === END ===