# abctk: Toolkit for ABC Treebank
## Overview
This repository provides a comprehensive kit of tools 
    that are necessary for generating, tailoring and utilizing ABC Treebank data.
The CLI interface and most of the functionalities are implemented with Python 3.6.
Part of the functionalities are implemented by other langauges but all wrapped with Python.

## Requirements
### In runtime
- System: Linux, tested with Debian 11 (bullseye)
- Need to be installed beforehand:
    - Java JRE (the version requirement aligns with that of [Stanford Tregex 4.2.0](https://nlp.stanford.edu/software/tregex.shtml))
    - m4
    - sed
    - Python (tested with 3.6.12) and that required packages listed in `pyproject.toml`
- Automatically prepared in building the python bdist
    - [Stanford Tregex](https://nlp.stanford.edu/software/tregex.shtml) (tested with 4.2.0)
- Optional dependencies:
    - (language models)

### In development
Besides those named above,

- Python [Poetry](https://python-poetry.org/) (tested with 1.1.4)
- Haskell [Stack](https://docs.haskellstack.org/) (tested with 2.5.1)

are also required.

## Installation & Usage
### As a user
A wheel package is provided for every release in the release page.
Using [pipx](https://pipxproject.github.io/pipx/) is recommended 
    so that the running environment can be isolated,
    avoiding to affect other Python packages.

```sh 
pipx install <package>.whl

# invoke the CLI
abctk --help
```

### As a developer
This repository is organized with [Poetry](https://python-poetry.org/).

```sh
git clone https://github.com/ABCTreebank/ABCT-toolkit
cd ABCT-toolkit
poetry install
```

This repository also provides a VS Code devcontainer (based on Docker)
    containing all necessary components for development.

## Usage
Refer to the help document of the `abctk` command.

## The internal pipeline
TBW

## LICENSE
See the [LICENSE](./LICENSE) file.

## Credits
This package reuses the following codes:
- [Prof. Alastair Butler's](http://www.compling.jp/ajb129/index.html#) 
    [wrapper of Tsurgeon](http://npcmj.ninjal.ac.jp/interfaces/tsurgeon_script) 
    (included in Standford Tregex)
- [Prof. Yoshikawa Masashi's](https://masashi-y.github.io/) python scripts for AllenNLP model training and parsing
- [Mr. Vijith Assar]'s [lit](https://github.com/vijithassar/lit)
