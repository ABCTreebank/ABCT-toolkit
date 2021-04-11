import enum
import re
import typing

import jaconv

_re_Mainichi95_KEY_VAL = re.compile(r"^＼(?P<key>..)＼(?P<val>.*)$")
_Mainichi95_KEY_of_hankaku_val = (
    "ID", "C0", "AD", "AE", "AF", 
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

_Mainichi95_bracket_begin = "（＜「【"
_Mainichi95_bracket_end = "）＞」】"
_Mainichi95_sent_end = "。】"
_re_Mainichi95_sent_sub = re.compile(
    r"(^――|（.*?[^０１２３４５６７８９].*?）|＝[^,]*＝|＝[^。]*$|＝.*写真。$)"
)

class Mainichi95_Sentence(typing.NamedTuple):
    ID: str
    sentence: str

    @staticmethod
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

    @staticmethod
    def _filter_sent(sent: str) -> str:
        """
        [Internal] Filter a sentence so that headings and parentheses are removed.

        Excerpt from the original perl code::
            文，文内で削除するもの

            ・"【"，"◇"，"▽"，"●"，"＜"，"《"で始まる文は全体を削除
            ・"。"が内部に5回以上または長さ512バイト以上(多くは引用文)は全体を削除
            ・文頭の"　"，"　――";
            ・"（…）"の削除，ただし，"（１）"，"（２）"の場合は残す
            ・"＝…＝"の削除，ただし間に"，"がくればRESET
            ・"＝…(文末)"で，文末に"。"がないか，"…"が"写真。"であれば除削
            ・（１）…（２） という箇条書きがあるもの
        """
        # strip spaces
        sent = sent.strip()

        # exclude headings and excessively long sentences
        if sent[0] in "【◇▽●＜《" or sent.count("。") >= 5 or len(sent) >= 256:
            return ""
        # === END IF ===

        # remove redundant parts
        return _re_Mainichi95_sent_sub.sub("", sent)
    # === END ===

    @classmethod
    def iterate_from_stream(
        cls, 
        source: typing.TextIO
    ) -> typing.Iterator["Mainichi95_Sentence"]:
        """
        Extract (only) sentences from the Mainichi-Shimbun 1995 corpus (MAI95.TXT).
        """
        article_C0 = ""
        sent_counter = 1

        for line in map(str.strip, source):
            if line:
                line_parsed = _Mainichi95_Keyval.from_line(line)
                key = line_parsed.key

                if key == "C0":
                    # new arcitle
                    article_C0 = line_parsed.val
                    sent_counter = 1
                elif key == "T2":
                    for sent in filter(
                        None,
                        map(
                            cls._filter_sent,
                            cls._tokenize_sent(line_parsed.val)
                        )
                    ):
                        yield cls(ID = f"{article_C0}-{sent_counter:03}", sentence = sent)
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


