"""Versioned lexical tokenizer shared by documents and queries; no model imports."""
import re
import unicodedata

VERSION = "vi-unicode-lexical.v1"
PATTERN = r"\d+(?:[.,]\d+)+|[^\W_]+(?:[/-][^\W_]+)*|%"


def validate_config(config):
    expected = {"tokenizer_version": VERSION, "normalization": "NFC", "lowercase": True,
                "whitespace": "unicode_to_single_space", "stemming": False,
                "stopword_removal": False, "token_pattern": PATTERN}
    if any(k not in config or type(config[k]) is not type(v) or config[k] != v for k, v in expected.items()):
        raise ValueError("Unsupported lexical tokenizer configuration")


def tokenize(text, config):
    validate_config(config)
    if not isinstance(text, str):
        raise ValueError("Lexical input must be a string")
    prepared = " ".join(unicodedata.normalize("NFC", text).lower().split())
    return re.findall(PATTERN, prepared, re.UNICODE)
