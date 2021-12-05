import logging
import typing
logger = logging.getLogger(__name__)
import pathlib
import sys

import fs
import typer
import lxml.etree as etree
from tqdm.auto import tqdm

import abctk.ccg2lambda.ccg2lambda_tools
import abctk.ccg2lambda.semantic_index
import abctk.ccg2lambda.semparse
import abctk.ccg2lambda.visualization_tools

app = typer.Typer()

@app.command("semparse")
def cmd_semparse(
    source: pathlib.Path = typer.Argument(
        ...,
        file_okay = True,
        dir_okay = False,
        allow_dash = True,
        help = """
            A treebank file in the JIGG xml format.
            If `-`, the file is loaded from STDIN. 
        """,
    ),
    template: pathlib.Path = typer.Argument(
        ...,
        file_okay = True,
        dir_okay = False,
    ),
    dest: pathlib.Path = typer.Argument(
        ...,
        file_okay = True, 
        dir_okay = False,
        allow_dash = True,
    ),
):
    # 1. Load sem template
    sem_index = abctk.ccg2lambda.semantic_index.SemanticIndex(
        str(template)
    )
    logger.info(f"Loaded the semantic template {template}")

    # 2. Parse JIGG XML
    parser = etree.XMLParser(remove_blank_text = True)
    source_path: str = str(source)
    if source_path == "-":
        root: etree._Element = etree.parse(
            sys.stdin,
            parser
        )
        logger.info("Loaded the trees from STDIN")
    else:
        root = etree.parse(
            source_path,
            parser
        )
        logger.info(f"Loaded the trees in {source_path}")
    sentences = root.findall(".//sentence")

    # 3. For each sentence and each of its ccg parses
    for sentence in tqdm(
        sentences,
        total = len(sentences), 
        desc = "Elaborating semantics",
    ):
        for ccg_num, _ in enumerate(sentence.xpath("./ccg"), start = 1):
            # 3-1. add sem
            sem_node = etree.Element("semantics")
            try:
                sem_tree = abctk.ccg2lambda.ccg2lambda_tools.assign_semantics_to_ccg(
                    sentence,
                    sem_index,
                    ccg_num,
                )
                abctk.ccg2lambda.semparse.filter_attributes(sem_tree)
                sem_node.extend(
                    sem_tree.xpath(".//descendant-or-self::span")
                )
                if "sem" in sem_tree.attrib and sem_tree.attrib["sem"]:
                    sem_node.set("status", "success")
                else:
                    sem_node.set("status", "failed")
                
                sem_node.set("ccg_id",
                    sentence.xpath(f'./ccg[{ccg_num}]/@id')[0]
                )
                sem_node.set("root",
                    sentence.xpath(f'./ccg[{ccg_num}]/@root')[0]
                )

            except Exception as e:
                sem_node.set("status", "failed")
                sentence_surf = " ".join(sentence.xpath("tokens/token/@surf"))

                logging.error(
                    "An error occurred during semantic assignment. "
                    f"Sentence: {sentence_surf}."
                    f"Error: {e}, "
                )

            sentence.append(sem_node)

    dest_path_str = str(dest)
    if dest_path_str == "-":
        sys.stdout.write(
            etree.tostring(
                root,
                xml_declaration = True,
                encoding = "utf-8",
                pretty_print = True
            )
        )
        logger.info("Output XML successfully dumped to STDOUT")
    else:
        root.write(
            dest_path_str,
            xml_declaration = True,
            encoding = "utf-8",
            pretty_print = True,
        )
        logger.info(f"Output XML successfully dumped into {str(dest_path_str)}")


class SemEntry(typing.NamedTuple):
    name: str
    drs_link: str
    drs_status: str

    def drs_successful(self):
        return self.drs_status == "success"

@app.command("to-drs")
def cmd_to_drs(
    source: pathlib.Path = typer.Argument(
        ...,
        file_okay = True,
        dir_okay = False,
        allow_dash = True,
        help = """
            A treebank file in the JIGG xml format.
            If `-`, the file is loaded from STDIN. 
            The file must have gone through the semparse beforehand.
        """,
    ),
    dest: pathlib.Path = typer.Argument(
        ...,
        dir_okay = True,
        exists = False,
    ),
):
    # 1. Parse JIGG XML
    parser = etree.XMLParser(remove_blank_text = True)
    source_path: str = str(source)
    if source_path == "-":
        root: etree._Element = etree.parse(
            sys.stdin,
            parser
        )
        logger.info("Loaded the trees from STDIN")
    else:
        root = etree.parse(
            source_path,
            parser
        )
        logger.info(f"Loaded the trees in {source_path}")
    sentences = root.findall(".//sentence")

    with fs.open_fs(str(dest), create = True) as folder:
        folder.makedirs("contents", recreate = True)

        links: typing.List[SemEntry] = []

        # 2. convert files
        for sent_count, sentence in enumerate(sentences):
            sent_html = abctk.ccg2lambda.visualization_tools.convert_sentence_to_mathml(
                sentence,
                drt = True,
            )
            sent_html = abctk.ccg2lambda.visualization_tools.wrap_mathml_in_html(sent_html)

            sentence_id: str = sentence.attrib.get("abc_id", str(sent_count))
            sent_path = f"contents/{sentence_id}.html"
            with folder.open(sent_path, "w") as f:
                f.write(sent_html)

            links.append(
                SemEntry(
                    name = sentence_id, 
                    drs_link = sent_path, 
                    drs_status = sentence.xpath("./semantics/@status")[0]
                )
            )

        # 3. Make an index
        with folder.open("index.html", "w") as f_index:
            f_index.write(r"""
<!DOCTYPE html>
<html lang="ja">
<head>
	<meta charset="utf-8">
	<title>Semparse Rendering</title>
</head>
<body>
<table>
    <tr>
        <th>ID</th>
        <th>DRS</th>
    </tr>
            """)
            for entry in links:
                f_index.write(rf"""
    <tr>
        <td>{entry.name}</td>
        <td><a href = "./{entry.drs_link}">{entry.drs_status}</td>
    </tr>
                """)
            f_index.write(r"""
</table>
</body>
</html>
            """)