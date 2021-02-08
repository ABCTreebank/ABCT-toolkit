import typing

import datetime
import functools
import logging
logger = logging.getLogger(__name__)
import pathlib
import sys

import click

def create_folder_time(prefix: str, to_make: bool = True):
    return create_folder_time_multiple(
        prefixes = (prefix, ), to_make = to_make
    )[prefix]
# === END ===

def create_folder_time_multiple(
    prefixes: typing.Iterable[str],
    to_make: bool = True,
) -> typing.Dict[str, pathlib.Path]:
    prefixes_set = set(prefixes)

    if prefixes_set:
        logger.info(
            "Going to create the following folders: "
            + ", ".join(prefixes_set)
        )
    else:
        logger.info(
            "No folders need to be created automatically"
        )
        return {}
    # === END IF ===

    dt_now = datetime.datetime.now()
    dest_folders = dict(
        (pfx, pathlib.Path(pfx + dt_now.isoformat())) 
        for pfx in prefixes_set
    )
    dest_folders_vals = dest_folders.values()

    while any(f.is_dir() for f in dest_folders_vals):
        dt_now = datetime.datetime.now()
        dest_folders = dict(
            (pfx, pathlib.Path(pfx + dt_now.isoformat())) 
            for pfx in prefixes_set
        )
        dest_folders_vals = dest_folders.values()
    # === END WHILE ===
    
    for f in dest_folders_vals:
        f.mkdir(parents = True)
    # === END FOR f ===

    return dest_folders
# === END ===

class FileList:
    """
    A Manager handling lists of paths.
    """
    files: typing.List[pathlib.Path]

    def __init__(self, paths: typing.Iterable[pathlib.Path]):
        self.files = list(paths)
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

    def iterate_absolute(self) -> typing.Iterator[pathlib.Path]:
        return map(lambda p: p.absolute(), self.files)
    # === END ===

    def iterate_truncating_commonprefix(self) -> typing.Iterator[
        typing.Tuple[
            pathlib.Path,
            pathlib.PurePath,
        ]
    ]:
        files_abs: typing.List[pathlib.Path] = list(self.iterate_absolute())

        parents_abs_path_parts: typing.Iterator[typing.Tuple[str, ...]] = map(
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

BATCH_PROCESS_ON_TREE = typing.Callable[
    [
        click.Context,
        str, # source_type
        typing.Optional[str], # destination
        bool, # can_overwrite
        bool, # if_gen_intermediate
        typing.Optional[str] # intermediate_dir
    ],
    None
]

class CmdTemplate_Batch_Process_on_Tree(click.Command):
    OPTIONS_NORMAL: typing.Tuple[click.Option, ...] = (
        click.Option(
            param_decls = [
                "-i",
                "--input", "--source", "source_type",
            ],
            type = click.Choice(
                choices = ("rawtrees", "filelist"),
                case_sensitive = False,
            ),
            default = "rawtrees",
            help = """Designating your data source.

\b
- `rawtrees' means that input Keyaki trees are provided directry from STDIN.
- `filelist' indicates that STDIN provides a list of paths to Keyaki tree files.

Default to `rawtrees'. Case insensitive."""
        ),
        click.Option(
            param_decls = [
                "-o", "--output", "--to", "--destination", "destination",
            ],
            type = click.Path(file_okay = False, dir_okay = True),
            help = """Path to a folder that stores the resulting files.
Since this program yields results in multiple files in different formats, 
it is always needed to have a storage folder.
Default to `./result_(timestamp)`.
            """
        ),
        click.Option(
            param_decls = [
                "--allow-overwrite/--no-allow-overwrite", "if_allow_overwrite",
            ],
            default = False,
        ),
    )

    OPTIONS_INTERMEDIATE: typing.Tuple[click.Option, ...] = (
        click.Option(
            param_decls = [
                "--intermediate/--no-intermediate", "if_gen_intermediate",
            ],
            default = False,
            help = """When specified, 
the program will generate
intermediate products of the conversion process
that facilitate development and debugging.""",
        ),
        click.Option(
            param_decls = [
                "--intermediate-dir", "intermediate_dir",
            ],
            type = click.Path(file_okay = False, dir_okay = True),
            default = None,
            help = """The path to intermediate logs.
This option has no effect 
unless the `--intermediate' flag is set on.""",
        )
    )

    def __init__(
        self,
        name: str,
        logger_orig: logging.Logger,
        folder_prefix: str,
        with_intermediate: bool,
        callback_preprocessing: typing.Optional[
#            typing.Callable[[dict, typing.Any], int]
            typing.Callable
        ],
        callback_process_filelist: typing.Optional[
            typing.Callable
#            typing.Callable[
#                [
#                    dict, 
#                    pathlib.Path, 
#                    typing.Optional[pathlib.Path], 
#                    FileList,
#                    P.kwargs
#                ], 
#                int,
#            ]
        ],
        callback_process_rawtrees: typing.Optional[
#            typing.Callable[
#                [dict, pathlib.Path,typing.Any], 
#                int,
#            ]
            typing.Callable
        ],
        **kwargs
    ):
        if kwargs.get("callback"):
            raise ValueError("Callback must be empty!")
        # === END IF ===

        super().__init__(name, **kwargs)
        self.logger_orig = logger_orig
        self.folder_prefix = folder_prefix
        self.callback_preprocessing = callback_preprocessing
        self.callback_process_filelist = callback_process_filelist
        self.callback_process_rawtrees = callback_process_rawtrees

        if with_intermediate:
            self.params = [
                *self.OPTIONS_NORMAL, 
                *self.OPTIONS_INTERMEDIATE,
            ]
            self.callback = self._template_procedure
        else:
            self.params = list(self.OPTIONS_NORMAL)
            self.callback = functools.partial(
                self._template_procedure,
                if_gen_intermediate = False,
                intermediate_dir = None,
            )
        # === END IF ===
    # === END ===

    def _template_procedure(
        self,
        source_type: str,
        destination: typing.Optional[str],
        if_allow_overwrite: bool,
        if_gen_intermediate: bool,
        intermediate_dir: typing.Optional[str],
        **kwargs,
    ) -> None:
        logger.info(
            "Command template invoked; "
            f"Template class: {self.__class__.__name__}, "
            f"Command name: {self.name}"
        )
        ctx = click.get_current_context()
        CONFIG = ctx.obj["CONFIG"]

        if self.callback_preprocessing:
            logger.info(
                "Command template is calling the preprocessing callback"
            )
            res_code: int = self.callback_preprocessing(CONFIG, **kwargs)

            if res_code:
                logger.info(
                    "The preprocessing callback ended up returning an error "
                    f"(code: {res_code})"
                )
                ctx.exit(res_code)
            # === END IF ===
            logger.info(
                "The preprocessing callback has succeeded"
            )
        # === END IF ===

        if source_type == "filelist":
            logger.info(
                "The type of source: filelist"
            )

            if not self.callback_process_filelist:
                return
            # === END IF ===

            dir_prefix_result: str = f"result_{self.folder_prefix}_"
            dir_prefix_log: str = f"log_{self.folder_prefix}_"

            res_folders: typing.Dict[str, pathlib.Path]
        
            res_folders = create_folder_time_multiple(
                filter(
                    None,
                    (
                        dir_prefix_result 
                            if not destination else None, 
                        dir_prefix_log 
                            if if_gen_intermediate and not intermediate_dir
                            else None,
                    )
                )
            )
            if destination:
                result_conv_parsed = pathlib.Path(destination)
                if result_conv_parsed.is_dir():
                    # Check if the folder is empty or not
                    pass
                else: 
                    result_conv_parsed.mkdir(parents = True)
                # === END IF ===

                res_folders[dir_prefix_result] = result_conv_parsed
            else:
                pass
            # === END IF ===

            if if_gen_intermediate and intermediate_dir:
                intermediate_parsed = pathlib.Path(intermediate_dir)

                if intermediate_parsed.is_dir():
                    # Check if the folder is empty or not
                    pass
                else: 
                    intermediate_parsed.mkdir(parents = True)
                # === END IF ===

                res_folders[dir_prefix_log] = intermediate_parsed
            else:
                pass
            # === END IF ===

            logger.info(
                "The destination folders are created; "
                f"Path to result files: {res_folders.get(dir_prefix_result, 'N/A')}, "
                f"Path to intermediate files: {res_folders.get(dir_prefix_log, 'N/A')}"
            )
            # === END IF ===

            flist: FileList = FileList.from_file_list(sys.stdin)

            # ------------------------
            # Execute the callback
            # ------------------------
            res_code = self.callback_process_filelist(
                CONFIG, 
                res_folders[dir_prefix_result],
                res_folders.get(dir_prefix_log),
                flist,
                **kwargs,
            )

            if res_code:
                ctx.exit(res_code)
            # === END IF ===
        elif source_type == "rawtrees":
            # ------------------------
            # Skip if no callback
            # ------------------------
            if not self.callback_process_rawtrees:
                return 
            # === END IF ===

            # ------------------------
            # Create an intermed folder if required
            # ------------------------
            log_pfx: typing.Optional[pathlib.Path]

            if if_gen_intermediate:
                if intermediate_dir:
                    intermediate_dir_parsed = pathlib.Path(intermediate_dir)
                    if intermediate_dir_parsed.is_dir():
                    # Check if the folder is empty or not
                        pass
                    else: 
                        intermediate_dir_parsed.mkdir(parents = True)
                    # === END IF ===
                    log_pfx = intermediate_dir_parsed / "rawtrees"
                else:
                    log_pfx = create_folder_time("log_conv") / "rawtrees"
                # === END IF ===
            else:
                log_pfx = None
            # === END IF ===

            # ------------------------
            # Execute the callback
            # ------------------------
            res_code = self.callback_process_rawtrees(
                conf = CONFIG,
                dir_log = log_pfx,
                **kwargs
            )

            if res_code:
                ctx.exit(res_code)
            # === END ===
        else:
            self.logger_orig.error(
                "Invalid CLI option: `source_type' must be either `stdin` or `filelist', "
                f"but {source_type} is given."
            )
            raise ValueError()
        # === END IF ===
    # === END ===
