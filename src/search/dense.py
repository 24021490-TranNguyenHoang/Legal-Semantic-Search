import os
import sys
from typing import Any, Callable, Dict, List, Optional

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)
from src.config import get_config
from src.database.qdrant_client import LegalQdrantManager


class DenseSearcher:
  """Tìm kiếm ngữ nghĩa vector trên Qdrant."""

  def __init__(
      self,
      model_name: str = "bkai-foundation-models/vietnamese-bi-encoder",
      qdrant_manager: Optional[LegalQdrantManager] = None,
      embed_fn: Optional[Callable[[str], List[float]]] = None,
  ):
    cfg = get_config()
    self.model_name = model_name
    self.vector_size = cfg.qdrant_vector_size
    self.qdrant_manager = qdrant_manager or LegalQdrantManager(
        host=cfg.qdrant_host,
        port=cfg.qdrant_port,
        collection_name=cfg.qdrant_collection,
        vector_size=cfg.qdrant_vector_size,
        create_if_missing=False,
    )
    self._embed_fn = embed_fn
    self._model: Any = None

  def _encode_query(self, query_text: str) -> List[float]:
    if self._embed_fn is not None:
      vec = self._embed_fn(query_text)
      return [float(x) for x in vec]

    if self._model is None:
      from sentence_transformers import SentenceTransformer

      self._model = SentenceTransformer(self.model_name)

    vec = self._model.encode(query_text, normalize_embeddings=True)
    if hasattr(vec, "tolist"):
      vec = vec.tolist()
    return [float(x) for x in vec]

  def search(
      self,
      query_text: str,
      document_id_filter: Optional[str] = None,
      law_type_filter: Optional[str] = None,
      year_filter: Optional[int] = None,
      top_k: int = 3,
  ) -> List[Dict[str, Any]]:
    if not query_text or not query_text.strip() or top_k <= 0:
      return []

    query_vector = self._encode_query(query_text)
    points = self.qdrant_manager.search_with_filter(
        query_vector=query_vector,
        document_id_filter=document_id_filter,
        law_type_filter=law_type_filter,
        year_filter=year_filter,
        top_k=top_k,
    )

    formatted_results: List[Dict[str, Any]] = []
    for pt in points:
      payload = pt.payload if isinstance(pt.payload, dict) else {}
      formatted_results.append({
          **payload,
          "id": pt.id,
          "score": float(pt.score) if pt.score is not None else 0.0,
          "search_mode": "dense",
      })
    return formatted_results