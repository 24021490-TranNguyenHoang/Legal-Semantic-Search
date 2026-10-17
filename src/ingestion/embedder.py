import json

from src.config import CHUNKS_FILE, EMBEDDING_MODEL_NAME, EMBEDDING_MAX_LENGTH
from src.pipeline_cli import (pipeline_parser, run_cli, read_records, search_text,
                              staging_path, staged_run, validate_records, check_message)


def mean_pooling(model_output, attention_mask):
    import torch
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask


def embed_and_save(input_path, run_dir, *, check_only=False):
    staging_path(run_dir)
    items = read_records(input_path)
    if check_only:
        check_message(len(items))
        return
    # Keep the prototype model, pooling and truncation policy unchanged in stage 1.
    with staged_run(run_dir, "embedder", input_path) as (run, report):
        import torch
        from transformers import AutoTokenizer, AutoModel
        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME)
        model = AutoModel.from_pretrained(EMBEDDING_MODEL_NAME)
        pending = run / "corpus_embedded.jsonl.partial"
        with pending.open("x", encoding="utf-8", newline="\n") as output:
            for item in items:
                encoded = tokenizer(search_text(item), padding=True, truncation=True,
                                    max_length=EMBEDDING_MAX_LENGTH, return_tensors="pt")
                with torch.no_grad():
                    model_output = model(**encoded)
                result = dict(item, vector=mean_pooling(model_output, encoded["attention_mask"])[0].tolist())
                validate_records([result], vectors=True)
                output.write(json.dumps(result, ensure_ascii=False) + "\n")
        pending.rename(run / "corpus_embedded.jsonl")
        report["record_count"] = len(items)
        print(f"OK: embeddings -> {run}")


def main(argv=None):
    def action(args):
        embed_and_save(args.input_path, args.run_dir, check_only=args.check_only)
    return run_cli(pipeline_parser("Build prototype embeddings into staging", CHUNKS_FILE),
                   action, argv)


if __name__ == "__main__":
    raise SystemExit(main())
