"""Versioned PhoBERT input preparation and exact slow-tokenizer diagnostics.

No heavy dependency is imported until the explicit offline child is called.
Legal content/source offsets never pass back through this transformation.
"""
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unicodedata

from src.config import BASE_DIR, STAGING_DIR
from src.preview_tokens import MODEL_ID, REVISION, inspect_assets
from src.source_contracts import digest

VERSION = "phobert-pyvi-input.v1"


def segmenter_binding():
    spec = importlib.util.find_spec("pyvi")
    if not spec:
        raise ValueError("Missing PyVi: install requirements-stage6.txt; no fallback segmentation")
    root = Path(next(iter(spec.submodule_search_locations)))
    return {"packages": {p: importlib.metadata.version(p) for p in ["pyvi", "sklearn-crfsuite", "python-crfsuite", "scikit-learn", "numpy", "scipy"]},
            "assets": {name: digest((root/name).read_bytes()) for name in ["ViTokenizer.py", "models/pyvi3.pkl", "models/words.txt"]}}


def require_config(config, tokenizer_dir):
    if (config["preprocessing_version"] != VERSION or config["model_id"] != MODEL_ID or config["model_revision"] != REVISION
            or config["whitespace"] != "unicode_whitespace_to_single_space" or config["segmentation"] != "pyvi"
            or config["normalization"] != "NFC" or config["lowercase"] is not False
            or config["add_special_tokens"] is not True or config["truncation"] is not False
            or config["model_max_tokens"] != 256 or config["roles"] != ["document", "query"]
            or config["segmenter_binding"] != segmenter_binding()
            or config["tokenizer_assets"] != inspect_assets(tokenizer_dir)):
        raise ValueError("Encoder model/preprocessing/package/asset configuration mismatch")


def preprocess_text(text, segmenter):
    """Same text operation for query and document; segmenter is ViTokenizer.tokenize.

    Prove every non-whitespace character is retained in order, allowing only
    inserted word-boundary underscores; never rewrite the original argument.
    """
    flat = " ".join(unicodedata.normalize("NFC", text).split())
    if not flat:
        raise ValueError("Empty encoder input")
    segmented = " ".join(segmenter(flat).split())
    original = "".join(flat.split())
    transformed = "".join(segmented.split())
    i = 0
    for char in transformed:
        if i < len(original) and char == original[i]:
            i += 1
        elif char != "_":
            raise ValueError("Segmentation changed non-whitespace content")
    if i != len(original):
        raise ValueError("Segmentation lost source characters")
    return segmented


def diagnose_text(tokenizer, text):
    """No native offsets: expose offsets only after exact BPE reconstruction.

    This verifies the installed slow PhoBERT algorithm, not heuristic substring
    search for decoded <unk>. On mismatch, token positions remain available but
    character/lexeme ranges stay null.
    """
    encoded = tokenizer(text, truncation=False, padding=False, add_special_tokens=True, return_special_tokens_mask=True)
    ids = encoded["input_ids"]
    pieces = tokenizer.tokenize(text)
    reconstructed, ranges = [], []
    for m in re.finditer(r"\S+\n?", text):
        bpe = tokenizer.bpe(m.group()).split(" ")
        literals = [p[:-2] if p.endswith("@@") else p for p in bpe]
        exact = "".join(literals) == m.group()
        position = m.start()
        for piece, literal in zip(bpe, literals):
            reconstructed.append(piece)
            ranges.append({"char_start": position, "char_end": position+len(literal), "source_fragment": literal,
                           "lexeme": m.group(), "lexeme_start": m.start(), "lexeme_end": m.end()} if exact else None)
            position += len(literal)
    matched = (pieces == reconstructed and ids == tokenizer.build_inputs_with_special_tokens(tokenizer.convert_tokens_to_ids(pieces))
               and len(ids) == len(pieces)+2 and encoded["special_tokens_mask"] == [1]+[0]*len(pieces)+[1])
    tokens = [tokenizer.cls_token] + pieces + [tokenizer.sep_token] if matched else tokenizer.convert_ids_to_tokens(ids)
    unknowns = []
    for i, token_id in enumerate(ids):
        if token_id == tokenizer.unk_token_id:
            proof = ranges[i-1] if matched and 0 < i < len(ids)-1 else None
            unknowns.append({"token_position": i, "token_id": token_id, "token_piece": tokens[i],
                             "source": proof, "character_mapping_method": "verified_phobert_regex_and_exact_bpe_roundtrip" if proof else "unavailable"})
    return {"tokens_with_special": len(ids), "special_token_count": sum(encoded["special_tokens_mask"]),
            "special_tokens": [tokenizer.cls_token, tokenizer.sep_token], "unknown_tokens": len(unknowns), "unknowns": unknowns,
            "token_ids": ids, "token_pieces": tokens, "token_position_basis": "zero_based_including_special_tokens",
            "native_offset_mapping": False, "bpe_reconstruction_exact": matched,
            "token_ids_sha256": digest(json.dumps(ids, separators=(",", ":")).encode("utf8"))}


WORKER = r'''
import importlib.util, importlib.metadata, sys, json, os, tempfile, platform
from pathlib import Path
probe = importlib.util.find_spec
blocked = {'torch', 'torchvision', 'torchaudio', 'tensorflow', 'jax', 'flax'}
importlib.util.find_spec = lambda name,*a,**kw: None if name.split('.')[0] in blocked else probe(name,*a,**kw)
req=json.load(sys.stdin)
scratch=Path(req['scratch']).resolve()
tempfile.tempdir=str(scratch)
# Cache Windows platform metadata before the readonly/network audit; SciPy asks
# for platform.machine. This is not encoder/model initialization.
platform.uname()
def audit(event,args):
    if event == 'import' and args[0].split('.')[0] in blocked:
        raise RuntimeError('Encoder/inference imports forbidden')
    if (event.startswith('socket.') and event != 'socket.gethostname') or event.startswith(('sqlite3.connect','subprocess.Popen')):
        raise RuntimeError('Network/database/subprocess forbidden in NLP worker')
    if event=='open' and ((isinstance(args[1],str) and any(c in args[1] for c in 'wax+')) or (args[2]&3)):
        if not isinstance(args[0],int) and scratch not in Path(args[0]).resolve().parents:
            raise RuntimeError('Only CRF scratch writes permitted')
sys.addaudithook(audit)
from transformers import PhobertTokenizer
from transformers.models.phobert import tokenization_phobert
from pyvi import ViTokenizer
from src.encoder_input import preprocess_text, diagnose_text
from src.source_contracts import digest
t=PhobertTokenizer.from_pretrained(req['tokenizer_dir'],local_files_only=True)
try:
    offset_probe=t('kiểm tra',return_offsets_mapping=True)
    native_offsets='offset_mapping' in offset_probe and offset_probe['offset_mapping'] is not None
except NotImplementedError:
    native_offsets=False
if native_offsets:
    raise RuntimeError('Offset capability changed; review diagnostic contract')
rows=[]
for text in req['texts']:
    prepared=preprocess_text(text,ViTokenizer.tokenize)
    rows.append({'input_sha256':digest(text.encode('utf8')),'encoder_text':prepared,
                 'encoder_text_sha256':digest(prepared.encode('utf8')),
                 'before':diagnose_text(t,text),'whitespace_only':diagnose_text(t,' '.join(text.split())),
                 'after':diagnose_text(t,prepared)})
assert not any(m in sys.modules for m in blocked)
json.dump({'rows':rows,'runtime':{'tokenizer_class':type(t).__name__,
 'transformers_version':importlib.metadata.version('transformers'),
 'implementation_sha256':digest(Path(tokenization_phobert.__file__).read_bytes()),
 'special_tokens_single':t.num_special_tokens_to_add(pair=False),'special_tokens_pair':t.num_special_tokens_to_add(pair=True),
 'tokenizer_model_max_length':t.model_max_length,'max_position_embeddings':json.loads((Path(req['tokenizer_dir'])/'config.json').read_text())['max_position_embeddings'],
 'native_offset_mapping':False,'inference_loaded':False,'network_used':False,'crf_scratch_only':True}},sys.stdout,ensure_ascii=False)
'''


def encode_inputs(texts, config, tokenizer_dir, *, role="document"):
    """Prepare/count exactly the future encoder input. Does not encode vectors.

    A single configuration/function handles query and document. Retrieval is not
    wired in this stage; callers must enforce this binding when integrating it.
    """
    if role not in {"document", "query"}:
        raise ValueError("Unknown encoder role")
    require_config(config, tokenizer_dir)
    root = STAGING_DIR.resolve()
    if root != STAGING_DIR.absolute():
        raise ValueError("Scratch staging must not be redirected")
    with tempfile.TemporaryDirectory(prefix="stage6-worker-", dir=root) as scratch:
        if root not in Path(scratch).resolve().parents:
            raise ValueError("Scratch outside workspace staging")
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", WORKER], cwd=BASE_DIR,
                              input=json.dumps({"texts": texts, "tokenizer_dir": str(Path(tokenizer_dir).resolve()), "scratch": scratch}, ensure_ascii=False),
                              capture_output=True, text=True, encoding="utf8", timeout=60, env=env)
        if proc.returncode:
            raise ValueError("Preprocessing/tokenizer worker failed: " + proc.stderr[-2500:])
        result = json.loads(proc.stdout)
    for r in result["rows"]:
        r.update(role=role, preprocessing_version=VERSION, model_max_tokens=config["model_max_tokens"], truncation=False,
                 tokens_with_special=r["after"]["tokens_with_special"], unknown_tokens=r["after"]["unknown_tokens"])
    result["segmenter_binding"] = config["segmenter_binding"]
    result["preprocessing_version"] = VERSION
    return result
