import importlib.resources as resc
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

class SemParseRecord(typing.NamedTuple):
    abc_id: str
    ccg_num: int
    ccg: typing.Optional[etree._Element]
    semparses: typing.Dict[str, typing.Optional[etree._Element]]
    tokens: typing.Optional[etree._Element]
    surf: str

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
    dest: pathlib.Path = typer.Argument(
        ...,
        dir_okay = True,
        help = """
            The output folder.
        """,
    ),
    drs: bool = typer.Option(
        False,
    ),
    hol: bool = typer.Option(
        False,
    ),
    # template: typing.List[typing.Tuple[str, pathlib.Path]] = typer.Option(
        # [],
        # file_okay = True,
        # dir_okay = False,
    # ),
):
    # 1. Load sem template
    sem_index = {}
    if drs:
        with resc.path("abctk.ccg2lambda", "semantics_comparatives_event.yaml") as sem_index_drs_path: 
            sem_index_drs_path_str = str(sem_index_drs_path)
            sem_index["drs"] = abctk.ccg2lambda.semantic_index.SemanticIndex(
                sem_index_drs_path_str
            )
            logger.info(f"Loaded the semantic template DRS at {sem_index_drs_path_str}")
    if hol:
        with resc.path("abctk.ccg2lambda", "semantics_comparatives_hol.yaml") as sem_index_hol_path:
            sem_index_hol_path_str = str(sem_index_hol_path)
            sem_index["hol"] = abctk.ccg2lambda.semantic_index.SemanticIndex(
                sem_index_hol_path_str
            )
            logger.info(f"Loaded the semantic template HOL at {sem_index_hol_path_str}")

    if not sem_index:
        logger.warning("No semantics template is loaded")

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

    res: typing.List[SemParseRecord] = []

    # 3. For each sentence and each of its ccg parses
    for sent_count, sentence in tqdm(
        enumerate(sentences),
        total = len(sentences), 
        desc = "Elaborating semantics",
    ):
        sentence_id = sentence.attrib.get(
            "abc_id", 
            f"UNTITLED_{sent_count}"
        )

        for ccg_num, ccg in enumerate(sentence.xpath("./ccg"), start = 1):
            # 3.0. Create record
            record = SemParseRecord(
                sentence_id, ccg_num, 
                ccg,
                {},
                sentence.xpath("./tokens")[0],
                surf = abctk.ccg2lambda.visualization_tools.get_surf_from_xml_node(sentence)
            )
            res.append(record)

            # 3.1. create sem
            for sem_type, s_index in sem_index.items():
                sem_node = etree.Element("semantics")
                sem_node.set("type", sem_type)

                try:
                    sem_tree = abctk.ccg2lambda.ccg2lambda_tools.assign_semantics_to_ccg(
                        sentence,
                        s_index,
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
                record.semparses[sem_type] = sem_node

    # 4. Dump
    with fs.open_fs(str(dest), create = True) as folder:
        # 4.1. Dump sem.xml
        with folder.open("sem.xml", "w") as f_sem_xml:
            f_sem_xml.write(
                etree.tostring(
                    root,
                    #xml_declaration = True,
                    encoding = str,
                    pretty_print = True,
                )
            )
        logger.info(f"Semantics XML successfully dumped into {str(dest)}/sem.xml")

        # 4.2 Preparation
        folder.makedirs("rendered", recreate = True)
        f_index = folder.open("index.html", "w")
        headers_sem_types = "\n".join(
            rf"<th>{sem_type}</th>"
            for sem_type in sem_index.keys()
        )

        f_index.write(
            rf"""
        <!DOCTYPE html>
<html lang="ja">
<head>
	<meta charset="utf-8">
	<title>Semparse Results</title>
</head>
<body>
<table>
    <tr>
        <th>ABC ID</th>
        <th>CCG parses</th>
        {headers_sem_types}
    </tr>
            """
        )

        # 4.3 rendering
        try:
            for record in tqdm(
                res,
                total = len(res), 
                desc = "Rendering semantics in HTML",
            ):
                sent_path = f"rendered/{record.abc_id}-{record.ccg_num}.html"
                f_index.write(fr"""
    <tr>
        <td><a href="./{sent_path}">{record.abc_id}</a></td>
        <td>{record.ccg_num}</td>
                """
                )
                with folder.open(sent_path, "w") as f_sent:
                    sent_html = ""
                    for sem_type, sem_xml in record.semparses.items():
                        sent_html += f"<h2>{sem_type}</h2>"
                        sent_html += abctk.ccg2lambda.visualization_tools.convert_sentence_to_mathml_2(
                                sentence_label = f"{record.abc_id}-{record.ccg_num}",
                                sentence_text = record.surf,
                                xml_ccg = record.ccg,
                                xml_sem = sem_xml,
                                xml_tokens = record.tokens,
                                is_drt = sem_type == "drs",
                            )

                        status = sem_xml.attrib["status"] if sem_xml else "NO OUTPUT"

                        f_index.write(
                            fr"""
        <td>{status}</td>
                            """
                        )
                    # === END FOR sem_type, sem_xml ===
                    
                    sent_html = abctk.ccg2lambda.visualization_tools.wrap_mathml_in_html(sent_html)
                    f_sent.write(sent_html)
                # === END WITH f_sent ===

                f_index.write("</tr>")
            # === END FOR record ===
            f_index.write(r"""
</table>
</body>
</html>
            """)
        finally:
            if f_index: f_index.close()
