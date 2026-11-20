import os
import sys
from typing import Any, Dict, List, Optional

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)
from src.config import get_config
from src.search.bm25 import BM25Searcher
from src.search.dense import DenseSearcher


def _doc_key(item: Dict[str, Any], fallback_idx: int) -> str:
  chunk_id = item.get("chunk_id")
  if chunk_id is not None and str(chunk_id).strip():
    return f"chunk:{str(chunk_id).strip()}"

  law_id = str(item.get("law_id") or item.get("document_id") or "").strip()
  citation = str(
      item.get("citation_path")
      or item.get("article_title")
      or item.get("article_number")
      or ""
  ).strip()
  if law_id and citation:
    return f"ref:{law_id}|{citation}"

  text = str(item.get("content") or item.get("chunk_text") or "").strip()
  if text:
    return f"text:{law_id}|{text[:80]}"

  return f"idx:{fallback_idx}"


class HybridSearcher:
  """Kết hợp tìm kiếm từ khóa (BM25) và tìm kiếm ngữ nghĩa (Dense) bằng RRF."""

  def __init__(
      self,
      bm25_searcher: Optional[BM25Searcher] = None,
      dense_searcher: Optional[DenseSearcher] = None,
      rrf_k: int = 60,
  ):
    cfg = get_config()
    self.default_top_k = cfg.default_top_k
    self.rrf_k = max(1, int(rrf_k))
    self.bm25_searcher = bm25_searcher or BM25Searcher(
        corpus_path=cfg.bm25_corpus_path,
        strict=False,
    )
    self.dense_searcher = dense_searcher or DenseSearcher()

  def search(
      self,
      query_text: str,
      document_id_filter: Optional[str] = None,
      law_type_filter: Optional[str] = None,
      year_filter: Optional[int] = None,
      top_k: Optional[int] = None,
      alpha: float = 0.5,
      candidate_multiplier: int = 3,
  ) -> List[Dict[str, Any]]:
    if not query_text or not query_text.strip():
      return []

    k = top_k if top_k is not None else self.default_top_k
    if k <= 0:
      return []

    fetch_k = max(k * max(1, candidate_multiplier), 10)
    clamped_alpha = max(0.0, min(1.0, float(alpha)))
    dense_weight = clamped_alpha
    bm25_weight = 1.0 - clamped_alpha

    bm25_results: List[Dict[str, Any]] = []
    dense_results: List[Dict[str, Any]] = []

    if self.bm25_searcher is not None and getattr(
        self.bm25_searcher, "corpus_loaded", False
    ):
      bm25_results = self.bm25_searcher.search(
          query_text=query_text,
          document_id_filter=document_id_filter,
          law_type_filter=law_type_filter,
          year_filter=year_filter,
          top_k=fetch_k,
      )
      bm25_results = [
          item
          for item in bm25_results
          if float(item.get("score", 0.0)) > 0.0
      ]

    if self.dense_searcher is not None:
      try:
        dense_results = self.dense_searcher.search(
            query_text=query_text,
            document_id_filter=document_id_filter,
            law_type_filter=law_type_filter,
            year_filter=year_filter,
            top_k=fetch_k,
        )
      except Exception:
        dense_results = []

    fused: Dict[str, Dict[str, Any]] = {}

    for rank, item in enumerate(bm25_results, start=1):
      key = _doc_key(item, rank)
      rrf_contrib = bm25_weight * (1.0 / (self.rrf_k + rank))
      if key not in fused:
        fused[key] = {
            **item,
            "rrf_score": rrf_contrib,
            "bm25_rank": rank,
            "bm25_score": float(item.get("score", 0.0)),
            "dense_rank": None,
            "dense_score": None,
        }
      else:
        fused[key]["rrf_score"] += rrf_contrib
        fused[key]["bm25_rank"] = rank
        fused[key]["bm25_score"] = float(item.get("score", 0.0))

    for rank, item in enumerate(dense_results, start=1):
      key = _doc_key(item, rank)
      rrf_contrib = dense_weight * (1.0 / (self.rrf_k + rank))
      if key not in fused:
        fused[key] = {
            **item,
            "rrf_score": rrf_contrib,
            "bm25_rank": None,
            "bm25_score": None,
            "dense_rank": rank,
            "dense_score": float(item.get("score", 0.0)),
        }
      else:
        fused[key]["rrf_score"] += rrf_contrib
        fused[key]["dense_rank"] = rank
        fused[key]["dense_score"] = float(item.get("score", 0.0))
        for field in (
            "content",
            "chunk_text",
            "law_id",
            "law_title",
            "citation_path",
            "source_url",
        ):
          if not fused[key].get(field) and item.get(field):
            fused[key][field] = item[field]

    ranked_items = sorted(
        fused.values(),
        key=lambda x: float(x.get("rrf_score", 0.0)),
        reverse=True,
    )[:k]

    for entry in ranked_items:
      entry["score"] = float(entry["rrf_score"])
      entry["search_mode"] = "hybrid"

    return ranked_items