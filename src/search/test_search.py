"""Legacy Dense demo; not an evaluation suite. Import does not run the demo."""
from pathlib import Path
from src.config import EMBEDDED_FILE, EMBEDDING_MODEL_NAME
from src.pipeline_cli import (read_records, run_cli, search_parser, validate_search_args)


def cosine_similarity(a, b):
    import numpy as np
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search(args):
    validate_search_args(args)
    chunks = read_records(args.input_path, vectors=True)
    import numpy as np
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    query_vector = model.encode(args.query, normalize_embeddings=True)
    # Preserve legacy dot-product ranking; this remains separate from the Hybrid encoder.
    results = [(np.dot(query_vector, np.array(item["vector"])), item) for item in chunks]
    results.sort(key=lambda x: x[0], reverse=True)
    for rank, (score, item) in enumerate(results[:args.top_k], start=1):
        print(f"[{rank}] {score:.4f} - {item.get('citation_path')}")
        print((item.get("original_text") or item.get("enriched_text"))[:300])


def main(argv=None):
    parser = search_parser("Run legacy Dense demo (not a benchmark)")
    parser.add_argument("--input", type=Path, default=EMBEDDED_FILE, dest="input_path")
    return run_cli(parser, search, argv)


if __name__ == "__main__":
    raise SystemExit(main())
