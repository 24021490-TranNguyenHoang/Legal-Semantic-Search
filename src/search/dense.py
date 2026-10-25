import os
import sys
from sentence_transformers import SentenceTransformer

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)
from src.database.qdrant_client import LegalQdrantManager


class DenseSearcher:

  def __init__(self, model_name="all-MiniLM-L6-v2"):
    print(f"Đang tải mô hình embedding cho tìm kiếm: {model_name}...")
    self.model = SentenceTransformer(model_name)
    self.qdrant_manager = LegalQdrantManager()

  def search(self, query_text, document_id_filter=None, top_k=3):
    # 1. Chuyển câu hỏi của người dùng thành vector
    query_vector = self.model.encode(query_text).tolist()

    # 2. Tìm kiếm trong Qdrant (có hỗ trợ lọc metadata)
    results = self.qdrant_manager.search_with_filter(
        query_vector=query_vector,
        document_id_filter=document_id_filter,
        top_k=top_k,
    )

    # 3. Định dạng lại kết quả trả về cho dễ đọc
    formatted_results = []
    for res in results:
      formatted_results.append({
          "score": res.score,
          "chunk_id": res.payload.get("chunk_id"),
          "document_id": res.payload.get("document_id"),
          "document_name": res.payload.get("document_name"),
          "article_number": res.payload.get("article_number"),
          "article_title": res.payload.get("article_title"),
          "chunk_text": res.payload.get("chunk_text"),
      })
    return formatted_results


if __name__ == "__main__":
  searcher = DenseSearcher()
  query = "Quy định về phạm vi điều chỉnh giao thông"
  print(f"\nĐang tìm kiếm với câu hỏi: '{query}'")
  res = searcher.search(query)
  for idx, item in enumerate(res):
    print(
        f"\n[Kết quả {idx+1}] (Score: {item['score']:.4f}) -"
        f" {item['article_title']}"
    )
    print(f"Nội dung: {item['chunk_text']}")