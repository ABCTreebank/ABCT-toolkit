import enum
import functools
import logging
logger = logging.getLogger(__name__)

import pathlib
import re
import typing

import jaconv

class Corpus_Identifier(typing.NamedTuple):
    corpus: str
    ID: str

    def to_tsv_line_with_sentence(self, sentence: str):
        return f"{self.corpus}\t{self.ID}\t{sentence}\n"
    
    @classmethod
    def from_tsv_line_with_sentence(cls, line: str) -> typing.Tuple["Corpus_Identifier", str]:
        corpus, ID, sent = line.split("\t")
        return cls(corpus, ID), sent
# === END CLASS ===

Corpora_Sentences = typing.Dict[Corpus_Identifier, str]

def load_corpora_sentences_from_tsv_stream(
    source: typing.TextIO
) -> Corpora_Sentences:
    return dict(
        map(
            Corpus_Identifier.from_tsv_line_with_sentence,
            filter(None, map(lambda s: s.strip("\n"), source)),
        )
    )
# === END ===

_re_Mainichi95_KEY_VAL = re.compile(r"^＼(?P<key>..)＼(?P<val>.*)$")
_Mainichi95_KEY_of_hankaku_val = (
    "ID", "C0", "AD", "AE", "AF", 
)

_Mainichi95_bracket_begin = "（＜「【"
_Mainichi95_bracket_end = "）＞」】"
_Mainichi95_sent_end = "。】"
_re_Mainichi95_sent_sub = re.compile(
    r"(^――|^[◇▽●]+|（[^）]*?[^０１２３４５６７８９）][^）]*?）|＝[^,，、]*＝|＝[^。]*$|＝.*写真。$)"
)
_re_Mainichi95_ID_filter = re.compile(
    r"9501(01|03)"
)

class _Mainichi95_Keyval(typing.NamedTuple):
    key: str
    val: str
    
    @classmethod
    def from_line(cls, line: str):
        parsed = _re_Mainichi95_KEY_VAL.match(line)

        if parsed:
            key = jaconv.zen2han(
                parsed.group("key"),
                kana = False, ascii = True, digit = True
            )
            if key in _Mainichi95_KEY_of_hankaku_val:
                val = jaconv.zen2han(
                    parsed.group("val"),
                    kana = False, ascii = True, digit = True,
                )
            else:
                val = parsed.group("val")
            # === END IF ===

            return cls(key, val)
        else:
            raise ValueError
    # === END ===
# === END CLASS ===

def extract_sentences_from_Mainichi95(
    source: typing.TextIO,
    ID_filter: typing.Callable[[str], bool] = (
        lambda s: bool(_re_Mainichi95_ID_filter.match(s))
    )
) -> typing.Iterator[typing.Tuple[Corpus_Identifier, str]]:
    """
    Extract (only) sentences from the Mainichi-Shimbun 1995 corpus (MAI95.TXT).
    """
    def _tokenize_sent(line: str) -> typing.Iterator[str]:
        """
        [Internal] Split a given line by sentences.
        A sentence is a slice of the given line ended 
        with either `。` or `】`.
        These two punctuations are counted only when
        they are not contained in a parenthesis.
        """
        bracket_count = 0
        sent_beginning = 0

        for i, char in enumerate(line):
            if char in _Mainichi95_bracket_begin:
                bracket_count += 1
            elif char in _Mainichi95_bracket_end:
                bracket_count -= 1
            # === END IF ===
            if char in _Mainichi95_sent_end and not bracket_count:
                yield line[sent_beginning:(i + 1)]
                sent_beginning = i + 1
            # === END IF ===
        # === END FOR i, char ===

        if len(line) - sent_beginning > 1:
            # trailing characters
            yield line[sent_beginning:]
    # === END ===

    def _filter_sent(
        sent: str,
        is_950103004_002: bool = False,
    ) -> str:
        """
        [Internal] Filter a sentence so that headings and parentheses are removed.

        Excerpt from the original perl code::
            文，文内で削除するもの

            ・"【"，"◇"，"▽"，"●"，"＜"，"《"で始まる文は全体を削除
            注：（◇，▽，●は採用例があるので，全体を削除することはしない．記号のみを削除）

            ・"。"が内部に5回以上または長さ512バイト以上(多くは引用文)は全体を削除（削除する必要がないので，しない）

            ・文頭の"　"，"　――";

            ・"（…）"の削除，ただし，"（１）"，"（２）"の場合は残す

            ・"＝…＝"の削除，ただし間に"，"がくればRESET
            注："、"も。

            ・"＝…(文末)"で，文末に"。"がないか，"…"が"写真。"であれば除削
            注："950103004-002"の文末（＝⛔⛔⛔⛔）はKeyakiに必要のようだ．この関数の外で処理しなければならない．

            ・（１）…（２） という箇条書きがあるもの
            注：意図が不明．未実装．
        """
        # strip spaces
        sent = sent.strip()

        # exclude headings and excessively long sentences
        if sent[0] in "【＜《" or sent.count("。") >= 5 or len(sent) >= 256:
            return ""
        # === END IF ===

        return _re_Mainichi95_sent_sub.sub("", sent)
    # === END ===

    article_C0 = ""
    sent_counter = 1
    to_read_inside = False

    for line in map(str.strip, source):
        if line:
            line_parsed = _Mainichi95_Keyval.from_line(line)
            key = line_parsed.key

            if key == "C0":
                # new arcitle
                article_C0 = line_parsed.val
                sent_counter = 1
                to_read_inside = ID_filter(article_C0)
            elif to_read_inside and key == "T2":
                for sent in map(
                    _filter_sent,
                    _tokenize_sent(line_parsed.val)
                ):
                    if article_C0 == "950103004" and sent_counter == 2:
                        # exception, leave untouched
                        # "950103004-002"の文末（＝⛔⛔⛔⛔）は必要．
                        yield (
                            Corpus_Identifier(
                                corpus = "MAI",
                                ID = f"{article_C0}-{sent_counter:03}",
                            ),
                            line_parsed.val.strip()
                        )
                    elif sent:
                        yield (
                            Corpus_Identifier(
                                corpus = "MAI",
                                ID = f"{article_C0}-{sent_counter:03}",
                            ),
                            sent
                        )
                    else:
                        # empty sentence
                        # no yielding
                        pass
                    # === END IF ===

                    sent_counter += 1
            else:
                # just ignore
                pass
            # === END IF ===
        else:
            # empty line
            # just ignore
            pass
        # === END IF ===
    # === END FOR ===
# === END ===

def extract_from_corpora(
    corpus_Mai95: typing.Union[str, pathlib.Path],
) -> typing.Iterator[typing.Tuple[Corpus_Identifier, str]]:
    # Mainichi '95
    logger.info(f"Opening the Mainichi '95 corpus at {corpus_Mai95}")
    with open(corpus_Mai95, "r") as h_Mai95:
        logger.info(
            f"Succesfully opened the Mainichi '95 corpus at {corpus_Mai95}; "
            "Going to extract sentences"
        )
        yield from extract_sentences_from_Mainichi95(h_Mai95)
    logger.info("Complete extracting sentence from the Mainichi '95 corpus")
    
    # BCCWJ

    # CSJ
    # SIDB
