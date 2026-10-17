import pickle

from src.config import CHUNKS_FILE
from src.pipeline_cli import (pipeline_parser, run_cli, read_records, search_text,
                              staging_path, staged_run, check_message)


def build_and_save_bm25(input_path, run_dir, *, check_only=False):
    staging_path(run_dir)
    items = read_records(input_path)
    corpus = [search_text(item).strip() for item in items]
    tokens = [text.lower().split() for text in corpus]
    if check_only:
        check_message(len(items))
        return
    with staged_run(run_dir, "bm25", input_path) as (run, report):
        from rank_bm25 import BM25Okapi
        data = {"bm25_model": BM25Okapi(tokens),
                "chunk_ids": [item["chunk_id"] for item in items], "corpus": corpus}
        with (run / "bm25_index.pkl.partial").open("xb") as output:
            pickle.dump(data, output)
        (run / "bm25_index.pkl.partial").rename(run / "bm25_index.pkl")
        report["record_count"] = len(items)
        print(f"OK: BM25 prototype index -> {run}")


def main(argv=None):
    def action(args):
        build_and_save_bm25(args.input_path, args.run_dir, check_only=args.check_only)
    return run_cli(pipeline_parser("Build prototype BM25 into staging", CHUNKS_FILE), action, argv)


if __name__ == "__main__":
    raise SystemExit(main())
