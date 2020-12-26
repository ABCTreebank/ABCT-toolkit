import typing

import pathlib

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