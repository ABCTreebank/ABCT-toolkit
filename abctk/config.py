import psutil
import pathlib

DIR_RUNTIME = pathlib.Path(__file__).parent / "runtime"

CONF_DEFAULT = {
    "bin-sys": {
        "m4": "m4", #"m4",
        "sed": "sed",
        "java": "java",
    },
    "bin-custom": {
        "abc-relabel": DIR_RUNTIME / "abc-relabel", 
        "tsurgeon_script": DIR_RUNTIME / "tsurgeon_script",
    },
    "runtimes": {
        "pre-relabel": DIR_RUNTIME / "pre-relabel.tsgn",
        "simplify-tag": DIR_RUNTIME / "simplify-tag.sed",
        "tregex": DIR_RUNTIME / "stanford-tregex.jar",
    },
    "max_process_num": len(psutil.Process().cpu_affinity())
}