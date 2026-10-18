"""Offline tokenizer-only counts in an isolated process. No weights/inference."""
import json
import os
from pathlib import Path
import subprocess
import sys

from src.source_contracts import digest

MODEL_ID = "bkai-foundation-models/vietnamese-bi-encoder"
REVISION = "84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0"
ASSETS = ("bpe.codes", "vocab.txt", "tokenizer_config.json", "special_tokens_map.json", "config.json")

# Some installed transformers versions ignore USE_TORCH=0. Make unavailable
# optional backend probes in THIS CHILD only; deny actual imports and sockets.
WORKER = r'''
import importlib.util, importlib.metadata, sys, json
from pathlib import Path
import hashlib
probe = importlib.util.find_spec
blocked = {'torch', 'torchvision', 'torchaudio', 'tensorflow', 'jax', 'flax'}
def token_only_probe(name, *args, **kwargs):
    return None if name.split('.')[0] in blocked else probe(name, *args, **kwargs)
importlib.util.find_spec = token_only_probe
def audit(event, args):
    if event == 'import' and args[0].split('.')[0] in blocked:
        raise RuntimeError('Inference import forbidden in tokenizer-only worker')
    if event.startswith('socket.') or event.startswith('sqlite3.connect'):
        raise RuntimeError('Network/database forbidden in tokenizer-only worker')
    if event == 'open' and ((isinstance(args[1], str) and any(c in args[1] for c in 'wax+')) or (args[2] & 3)):
        raise RuntimeError('Write forbidden in tokenizer-only worker')
sys.addaudithook(audit)
from transformers import PhobertTokenizer
from transformers.models.phobert import tokenization_phobert
req = json.load(sys.stdin)
tokenizer = PhobertTokenizer.from_pretrained(req['tokenizer_dir'], local_files_only=True)
result = []
for text in req['texts']:
    ids = tokenizer(text, truncation=False, padding=False, add_special_tokens=True)['input_ids']
    raw = json.dumps(ids, separators=(',', ':')).encode('utf8')
    result.append({'tokens_with_special': len(ids), 'unknown_tokens': ids.count(tokenizer.unk_token_id),
                   'token_ids_sha256': hashlib.sha256(raw).hexdigest()})
assert not any(m in sys.modules for m in blocked)
json.dump({'counts': result, 'tokenizer_class': type(tokenizer).__name__,
           'transformers_version': importlib.metadata.version('transformers'),
           'implementation_sha256': hashlib.sha256(Path(tokenization_phobert.__file__).read_bytes()).hexdigest(),
           'special_tokens': tokenizer.num_special_tokens_to_add(pair=False),
           'truncation': False, 'word_segmentation_added': False, 'inference_loaded': False,
           'network_used': False}, sys.stdout)
'''


def default_tokenizer_dir():
    return Path.home() / ".cache/huggingface/hub/models--bkai-foundation-models--vietnamese-bi-encoder/snapshots" / REVISION


def inspect_assets(path):
    path = Path(path)
    rows = {}
    for name in ASSETS:
        data = (path / name).read_bytes()
        if not data:
            raise ValueError("Empty tokenizer asset: " + name)
        rows[name] = {"sha256": digest(data), "size_bytes": len(data)}
    config = json.loads((path / "tokenizer_config.json").read_text(encoding="utf8"))
    model = json.loads((path / "config.json").read_text(encoding="utf8"))
    if config["tokenizer_class"] != "PhobertTokenizer" or model["model_type"] != "roberta" or model["max_position_embeddings"] != 258:
        raise ValueError("Unexpected tokenizer/model profile; no automatic model change")
    return rows


def count_tokens(texts, tokenizer_dir):
    inspect_assets(tokenizer_dir)
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", WORKER],
                            input=json.dumps({"texts": texts, "tokenizer_dir": str(Path(tokenizer_dir).resolve())}, ensure_ascii=False),
                            capture_output=True, text=True, encoding="utf8", env=env, timeout=60)
    if result.returncode:
        raise ValueError("Tokenizer-only process failed: " + result.stderr[-1800:])
    return json.loads(result.stdout)
