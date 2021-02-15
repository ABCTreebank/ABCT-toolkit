import typing

import datetime
import functools
import logging
logger = logging.getLogger(__name__)
import multiprocessing as mp
import os
import pathlib
import sys
import tqdm

import click

def create_folder_time(
    prefix: str, 
    to_make: bool = True
) -> pathlib.Path:
    """Create a single folder named with 

    Arguments
    ---------
    prefix: str
    
    Returns
    -------
    path: pathlib.Path

    """
    return create_folder_time_multiple(
        prefixes = (prefix, ), to_make = to_make
    )[prefix]
# === END ===

def create_folder_time_multiple(
    prefixes: typing.Iterable[str],
    to_make: bool = True,
) -> typing.Dict[str, pathlib.Path]:
    """Create more than one folder named with THE SAME timestamp.

    Arguments
    ---------
    prefixes: iterable of str

    Returns
    -------
    folders: dict of str to pathlib.Path
    """
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

class CmdTemplate_Batch_Process_on_Tree(click.Command):
    """A template of Click commands 
        that deal with both STDIN inputs 
        and a file list to be batch processed in the same way.

    Attributes
    ----------
    name: str
        The name of the command.

    logger_orig: logging.Logger,
        The logger that belongs to the command.

    folder_prefix: str,
        A prefix attached to folders to be created.

    with_intermediate: bool,
        True if the command has intermediate traces to be dumped out.
        If true, a set of command options pertaning to these will be added.

    callback_preprocessing: typing.Callable, optional
        * conf: dict

    callback_process_file: typing.Callable, optional
        A callback function for the filelist mode.
        The function is expected to 
            take the following arguments with the exact names:
        * conf: dict
        * src: pathlib.Path
        * dest: pathlib.Path
        * log_prefix: str or pathlib.Path, optional

    callback_process_rawtrees: typing Callable, optional
        * conf: dict
        * f_src: typing.TextIO
        * f_dest: typing.TextIO
        * src_name: str
        * dest_name: str
        * log_prefix: str or pathlib.Path, optional
    """

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
        callback_process_file: typing.Optional[
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
        self.callback_process_file = callback_process_file
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
        _self_name: str = self.__class__.__name__

        logger.info(
            f"The command {self.name} is generated "
            f"by the command template {_self_name}"
        )
        ctx = click.get_current_context()
        CONFIG = ctx.obj["CONFIG"]

        if self.callback_preprocessing:
            logger.info(
                f"The command template {_self_name} "
                "is calling the preprocessing callback"
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
            self.logger_orig.info(
                "The type of source: filelist"
            )

            if not self.callback_process_file:
                logger.info(
                    "No callback for the filelist mode is given. "
                    "Nothing done "
                    "and the program is ended with vacuous success."
                )
                ctx.exit(0)
            # === END IF ===

            # ------------------------
            # Create result & intermediate folders
            # ------------------------
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

            self.logger_orig.info(
                "The destination folders are created; "
                f"Path to result files: {res_folders.get(dir_prefix_result, 'N/A')}, "
                f"Path to intermediate files: {res_folders.get(dir_prefix_log, 'N/A')}"
            )
            # === END IF ===

            # ------------------------
            # Work out the output file paths
            # ------------------------
            flist: FileList = FileList.from_file_list(sys.stdin)

            # ------------------------
            # Invoke multiprocess conversion
            # ------------------------
            proc_num: int = CONFIG["max_process_num"]
            with mp.Pool(processes = proc_num) as pool:
                self.logger_orig.info(f"Number of processes: {proc_num}")
                
                # Work out files to be processed
                flist_dest_expanded: tuple
                if if_gen_intermediate:
                    flist_dest_expanded = tuple(
                        FileConversionArgs(
                            src = src,
                            dest = res_folders[dir_prefix_result] / fn,
                            file_size = os.path.getsize(src),
                            log_prefix = res_folders[dir_prefix_log]
                        )
                        for src, fn
                        in flist.iterate_truncating_commonprefix()
                    )
                else:
                    flist_dest_expanded = tuple(
                        FileConversionArgs(
                            src = src,
                            dest = res_folders[dir_prefix_result] / fn,
                            file_size = os.path.getsize(src),
                            log_prefix = None,
                        )
                        for src, fn
                        in flist.iterate_truncating_commonprefix()
                    )
                # === END IF ===

                # Get the sum of the input files
                files_total_size: int = sum(
                    map(lambda x: x[2], flist_dest_expanded)
                )
                self.logger_orig.info(
                    f"# of the files to be processed: {len(flist_dest_expanded)}, "
                    f"The total size of the files to be processed: {files_total_size}"
                )
                
                # Create jobs
                jobs = pool.imap_unordered(
                    functools.partial(
                        _conv_file_wrapper,
                        f = self.callback_process_file,
                        conf = CONFIG,
                        **kwargs,
                    ),
                    flist_dest_expanded,
                )
                # Execute the callback per file
                with tqdm.tqdm(
                    total = files_total_size, 
                    unit = "B",
                    unit_scale = True,
                    unit_divisor = 1024
                ) as pb:
                    pb.write("Converting Keyaki trees into ABC trees:") 
                    # TODO: customize the message
                    for _return_code, src_size in jobs:
                        pb.update(src_size)
                # === END WITH pb ===
            # === END FOR path_src, filename_res ===

            ctx.exit(0)
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
                f_src = sys.stdin,
                f_dest = sys.stdout,
                src_name = "<STDIN>",
                dest_name = "<STDOUT>",
                log_prefix = log_pfx,
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

class FileConversionArgs(typing.NamedTuple):
    src: pathlib.Path
    dest: pathlib.Path
    file_size: int
    log_prefix: typing.Union[str, pathlib.Path, None]
# === END CLASS ===

def _conv_file_wrapper(
    args: FileConversionArgs,
    f: typing.Callable,
    conf: dict,
    **kwargs,
) -> typing.Tuple[int, int]:
    return (
        f(
            conf = conf, 
            src = args.src, 
            dest = args.dest,
            log_prefix = args.log_prefix,
            **kwargs,
        ),
        args.file_size,
    )
# === END ===