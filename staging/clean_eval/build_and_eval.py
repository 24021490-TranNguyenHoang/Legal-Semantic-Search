import json
import os
import sys
from typing import Any

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
  sys.path.insert(0, ROOT_DIR)

from sentence_transformers import SentenceTransformer

from src.search.bm25 import BM25Searcher
from src.search.dense import DenseSearcher
from src.search.hybrid import HybridSearcher
from src.search.reranker import LegalReranker

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
EVAL_COLLECTION = "clean_eval_chunks"

CORPUS = [
    {
        "chunk_id": "clean_35_2024_d1",
        "law_id": "35.2024.QH15",
        "document_id": "35.2024.QH15",
        "law_title": "Điều 1. Phạm vi điều chỉnh",
        "article_title": "Điều 1. Phạm vi điều chỉnh",
        "law_type": "Luật",
        "year": 2024,
        "citation_path": "Luật Trật tự, an toàn giao thông đường bộ 35.2024.QH15 - Điều 1",
        "content": (
            "Phạm vi điều chỉnh Luật này quy định về quy tắc giao thông đường"
            " bộ, kết cấu hạ tầng giao thông đường bộ, phương tiện tham gia"
            " giao thông đường bộ, vận tải đường bộ và quản lý nhà nước về giao"
            " thông đường bộ."
        ),
        "chunk_text": (
            "Phạm vi điều chỉnh Luật này quy định về quy tắc giao thông đường"
            " bộ, kết cấu hạ tầng giao thông đường bộ, phương tiện tham gia"
            " giao thông đường bộ, vận tải đường bộ và quản lý nhà nước về giao"
            " thông đường bộ."
        ),
        "source_url": "",
    },
    {
        "chunk_id": "clean_35_2024_d5",
        "law_id": "35.2024.QH15",
        "document_id": "35.2024.QH15",
        "law_title": "Điều 5. Xử lý vi phạm và mức phạt hành chính",
        "article_title": "Điều 5. Xử lý vi phạm và mức phạt hành chính",
        "law_type": "Luật",
        "year": 2024,
        "citation_path": "Luật Trật tự, an toàn giao thông đường bộ 35.2024.QH15 - Điều 5",
        "content": (
            "Người điều khiển phương tiện giao thông vi phạm quy tắc giao thông"
            " đường bộ như vượt đèn đỏ, đi ngược chiều hoặc chạy quá tốc độ sẽ"
            " bị xử phạt vi phạm hành chính theo nghị định quy định hiện hành."
            " Các hành vi đua xe trái phép, lạng lách, đánh võng trên đường bộ"
            " sẽ bị tịch thu phương tiện và truy cứu trách nhiệm hình sự tùy"
            " theo mức độ vi phạm."
        ),
        "chunk_text": (
            "Người điều khiển phương tiện giao thông vi phạm quy tắc giao thông"
            " đường bộ như vượt đèn đỏ, đi ngược chiều hoặc chạy quá tốc độ sẽ"
            " bị xử phạt vi phạm hành chính theo nghị định quy định hiện hành."
            " Các hành vi đua xe trái phép, lạng lách, đánh võng trên đường bộ"
            " sẽ bị tịch thu phương tiện và truy cứu trách nhiệm hình sự tùy"
            " theo mức độ vi phạm."
        ),
        "source_url": "",
    },
    {
        "chunk_id": "clean_168_2024_d1",
        "law_id": "168.2024.NĐ-CP",
        "document_id": "168.2024.NĐ-CP",
        "law_title": "Điều 1. Quy định xử phạt vi phạm quy tắc giao thông đường bộ",
        "article_title": (
            "Điều 1. Quy định xử phạt vi phạm quy tắc giao thông đường bộ"
        ),
        "law_type": "Nghị định",
        "year": 2024,
        "citation_path": "Nghị định 168/2024/NĐ-CP - Điều 1",
        "content": (
            "Quy định xử phạt vi phạm quy tắc giao thông đường bộ. Phạt tiền từ"
            " 4.000.000 đồng đến 6.000.000 đồng đối với người điều khiển xe ô"
            " tô vượt đèn đỏ, không chấp hành hiệu lệnh của đèn tín hiệu giao"
            " thông. Phạt tiền từ 800.000 đồng đến 1.000.000 đồng đối với người"
            " điều khiển xe mô tô, xe gắn máy vượt đèn đỏ hoặc đi vào đường cấm."
        ),
        "chunk_text": (
            "Quy định xử phạt vi phạm quy tắc giao thông đường bộ. Phạt tiền từ"
            " 4.000.000 đồng đến 6.000.000 đồng đối với người điều khiển xe ô"
            " tô vượt đèn đỏ, không chấp hành hiệu lệnh của đèn tín hiệu giao"
            " thông. Phạt tiền từ 800.000 đồng đến 1.000.000 đồng đối với người"
            " điều khiển xe mô tô, xe gắn máy vượt đèn đỏ hoặc đi vào đường cấm."
        ),
        "source_url": "",
    },
    {
        "chunk_id": "clean_168_2024_d2",
        "law_id": "168.2024.NĐ-CP",
        "document_id": "168.2024.NĐ-CP",
        "law_title": "Điều 2. Vi phạm nồng độ cồn khi điều khiển phương tiện",
        "article_title": "Điều 2. Vi phạm nồng độ cồn khi điều khiển phương tiện",
        "law_type": "Nghị định",
        "year": 2024,
        "citation_path": "Nghị định 168/2024/NĐ-CP - Điều 2",
        "content": (
            "Điều khiển xe trên đường mà trong máu hoặc hơi thở có nồng độ cồn"
            " vượt quá quy định sẽ bị xử phạt tiền, tước quyền sử dụng giấy"
            " phép lái xe hoặc trừ điểm giấy phép lái xe theo từng mức nồng độ"
            " cồn đối với người điều khiển xe mô tô, xe gắn máy và xe ô tô."
        ),
        "chunk_text": (
            "Điều khiển xe trên đường mà trong máu hoặc hơi thở có nồng độ cồn"
            " vượt quá quy định sẽ bị xử phạt tiền, tước quyền sử dụng giấy"
            " phép lái xe hoặc trừ điểm giấy phép lái xe theo từng mức nồng độ"
            " cồn đối với người điều khiển xe mô tô, xe gắn máy và xe ô tô."
        ),
        "source_url": "",
    },
    {
        "chunk_id": "clean_168_2024_d3",
        "law_id": "168.2024.NĐ-CP",
        "document_id": "168.2024.NĐ-CP",
        "law_title": "Điều 3. Vi phạm tốc độ và đội mũ bảo hiểm",
        "article_title": "Điều 3. Vi phạm tốc độ và đội mũ bảo hiểm",
        "law_type": "Nghị định",
        "year": 2024,
        "citation_path": "Nghị định 168/2024/NĐ-CP - Điều 3",
        "content": (
            "Người điều khiển xe mô tô, xe gắn máy không đội mũ bảo hiểm cho"
            " người đi mô tô, xe máy hoặc đội mũ bảo hiểm không cài quai đúng"
            " quy cách bị xử phạt hành chính. Người điều khiển phương tiện chạy"
            " quá tốc độ quy định bị xử phạt tiền tùy theo mức độ vượt tốc độ."
        ),
        "chunk_text": (
            "Người điều khiển xe mô tô, xe gắn máy không đội mũ bảo hiểm cho"
            " người đi mô tô, xe máy hoặc đội mũ bảo hiểm không cài quai đúng"
            " quy cách bị xử phạt hành chính. Người điều khiển phương tiện chạy"
            " quá tốc độ quy định bị xử phạt tiền tùy theo mức độ vượt tốc độ."
        ),
        "source_url": "",
    },
]

QUERIES = [
    {
        "id": "q1",
        "query": "vượt đèn đỏ phạt bao nhiêu tiền",
        "relevant_chunk_ids": ["clean_168_2024_d1", "clean_35_2024_d5"],
    },
    {
        "id": "q2",
        "query": "nồng độ cồn xe máy mức phạt",
        "relevant_chunk_ids": ["clean_168_2024_d2"],
    },
    {
        "id": "q3",
        "query": "không đội mũ bảo hiểm chạy quá tốc độ",
        "relevant_chunk_ids": ["clean_168_2024_d3", "clean_35_2024_d5"],
    },
    {
        "id": "q4",
        "query": "phạm vi điều chỉnh giao thông đường bộ",
        "relevant_chunk_ids": ["clean_35_2024_d1"],
    },
]


def _prepare_eval_collection(qm: Any, vectors_with_payloads: list) -> None:
  """Tạo/tái tạo collection tạm clean_eval_chunks và upsert vector."""
  if hasattr(qm, "collection_name"):
    qm.collection_name = EVAL_COLLECTION
  elif hasattr(qm, "default_collection"):
    qm.default_collection = EVAL_COLLECTION

  if hasattr(qm, "recreate_collection"):
    try:
      qm.recreate_collection(collection_name=EVAL_COLLECTION, vector_size=768)
    except TypeError:
      qm.recreate_collection(vector_size=768)
  elif hasattr(qm, "create_collection"):
    try:
      qm.create_collection(
          collection_name=EVAL_COLLECTION, vector_size=768, recreate=True
      )
    except TypeError:
      qm.create_collection(vector_size=768, recreate=True)

  vectors = [item["vector"] for item in vectors_with_payloads]
  payloads = [item["payload"] for item in vectors_with_payloads]
  ids = [item["id"] for item in vectors_with_payloads]

  if hasattr(qm, "upsert_chunks"):
    try:
      qm.upsert_chunks(vectors, payloads)
      return
    except Exception:
      pass

  if hasattr(qm, "client"):
    from qdrant_client.models import PointStruct

    qdrant_points = [
        PointStruct(id=i, vector=v, payload=p)
        for i, v, p in zip(ids, vectors, payloads)
    ]
    qm.client.upsert(collection_name=EVAL_COLLECTION, points=qdrant_points)
def main() -> None:
  os.makedirs(OUT_DIR, exist_ok=True)
  corpus_path = os.path.join(OUT_DIR, "corpus.json")
  queries_path = os.path.join(OUT_DIR, "queries.json")
  report_path = os.path.join(OUT_DIR, "eval_report.json")

  with open(corpus_path, "w", encoding="utf-8") as f:
    json.dump(CORPUS, f, ensure_ascii=False, indent=2)
  with open(queries_path, "w", encoding="utf-8") as f:
    json.dump(QUERIES, f, ensure_ascii=False, indent=2)

  model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")
  base_dense = DenseSearcher()
  qm = getattr(base_dense, "qdrant_manager", None) or getattr(
      base_dense, "client", None
  )

  points = [
      {
          "id": idx + 1,
          "vector": model.encode(
              doc["content"], normalize_embeddings=True
          ).tolist(),
          "payload": doc,
      }
      for idx, doc in enumerate(CORPUS)
  ]
  _prepare_eval_collection(qm, points)

  dense = DenseSearcher(
      qdrant_manager=qm if hasattr(base_dense, "qdrant_manager") else None,
      embed_fn=lambda q: model.encode(q, normalize_embeddings=True).tolist(),
  )
  if hasattr(dense, "collection_name"):
    dense.collection_name = EVAL_COLLECTION

  bm25 = BM25Searcher(corpus_path=corpus_path, strict=True)
  hybrid = HybridSearcher(bm25_searcher=bm25, dense_searcher=dense)
  reranker = LegalReranker()

  report = []
  for q in QUERIES:
    q_text = q["query"]
    b_res = bm25.search(q_text, top_k=2)
    d_res = dense.search(q_text, top_k=2)
    h_res = hybrid.search(q_text, top_k=2)
    r_cands = hybrid.search(q_text, top_k=4)
    r_res = reranker.rerank(q_text, r_cands, top_k=2)

    row = {
        "id": q["id"],
        "query": q_text,
        "expected": q["relevant_chunk_ids"],
        "bm25_top1": b_res[0].get("chunk_id") if b_res else None,
        "dense_top1": d_res[0].get("chunk_id") if d_res else None,
        "hybrid_top1": h_res[0].get("chunk_id") if h_res else None,
        "rerank_top1": r_res[0].get("chunk_id") if r_res else None,
    }
    report.append(row)
    print(
        f"{row['id']} | exp={row['expected']} | bm25={row['bm25_top1']} |"
        f" dense={row['dense_top1']} | hyb={row['hybrid_top1']} |"
        f" rr={row['rerank_top1']}"
    )

  with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
  print("SAVED:", report_path)


if __name__ == "__main__":
  main()