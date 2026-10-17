from src.config import COLLECTION_NAME, EMBEDDED_FILE, EMBEDDING_DIMENSION
from src.pipeline_cli import (pipeline_parser, run_cli, read_records, staging_path,
                              staged_run, check_message)


def build_qdrant(input_path, run_dir, *, check_only=False):
    staging_path(run_dir)
    items = read_records(input_path, vectors=True)
    if check_only:
        check_message(len(items))
        return
    # Only write inside an exclusively created run. Never delete a collection.
    with staged_run(run_dir, "qdrant", input_path) as (run, report):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        fields = ("chunk_id", "law_id", "law_title", "chapter", "article_id",
                  "article_title", "clause_id", "citation_path", "original_text",
                  "enriched_text", "effective_date", "status")
        points = [PointStruct(id=i, vector=item["vector"],
                              payload={k: item.get(k) for k in fields})
                  for i, item in enumerate(items)]
        client = QdrantClient(path=str(run / "qdrant_db"))
        try:
            if client.collection_exists(COLLECTION_NAME):
                raise ValueError("Collection already exists; refusing to replace it")
            client.create_collection(collection_name=COLLECTION_NAME,
                                     vectors_config=VectorParams(size=EMBEDDING_DIMENSION,
                                                                 distance=Distance.COSINE))
            for start in range(0, len(points), 100):
                client.upsert(collection_name=COLLECTION_NAME,
                              points=points[start:start + 100], wait=True)
        finally:
            client.close()
        report["point_count"] = len(items)
        print(f"OK: staged Qdrant -> {run}")


def main(argv=None):
    def action(args):
        build_qdrant(args.input_path, args.run_dir, check_only=args.check_only)
    return run_cli(pipeline_parser("Build isolated prototype Qdrant into staging", EMBEDDED_FILE),
                   action, argv)


if __name__ == "__main__":
    raise SystemExit(main())
