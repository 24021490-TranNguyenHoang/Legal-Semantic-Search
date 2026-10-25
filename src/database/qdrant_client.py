import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Thêm đường dẫn gốc để import module nếu cần
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)


class LegalQdrantManager:

  def __init__(
      self, host="localhost", port=6333, collection_name="vietnamese_laws"
  ):
    self.client = QdrantClient(host=host, port=port)
    self.collection_name = collection_name
    self._init_collection()

  def _init_collection(self, vector_size=384):
    """Khởi tạo collection trên Qdrant nếu chưa tồn tại (Mặc định vector_size=384 cho mô hình embedding)."""
    collections = self.client.get_collections().collections
    exists = any(col.name == self.collection_name for col in collections)

    if not exists:
      self.client.create_collection(
          collection_name=self.collection_name,
          vectors_config=models.VectorParams(
              size=vector_size, distance=models.Distance.COSINE
          ),
      )
      print(f"Đã tạo thành công Qdrant Collection: {self.collection_name}")
    else:
      print(f"Collection '{self.collection_name}' đã tồn tại trên Qdrant.")

  def upsert_chunks(self, chunks, vectors):
    """Đẩy các chunk và vector embedding kèm metadata lên Qdrant."""
    points = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
      points.append(
          models.PointStruct(
              id=i + 1,
              vector=vector,
              payload={
                  "chunk_id": chunk["chunk_id"],
                  "document_id": chunk["document_id"],
                  "document_name": chunk["document_name"],
                  "article_number": chunk["article_number"],
                  "article_title": chunk["article_title"],
                  "chunk_text": chunk["chunk_text"],
                  **chunk["metadata"],
              },
          )
      )

    self.client.upsert(collection_name=self.collection_name, points=points)
    print(f"Đã upsert thành công {len(points)} điểm dữ liệu lên Qdrant!")

  def search_with_filter(
      self, query_vector, document_id_filter=None, top_k=3
  ):
    """Tìm kiếm vector kết hợp với điều kiện lọc metadata (hỗ trợ lọc theo số hiệu văn bản)."""
    query_filter = None
    if document_id_filter:
      query_filter = models.Filter(
          must=[
              models.FieldCondition(
                  key="document_id",
                  match=models.MatchValue(value=document_id_filter),
              )
          ]
      )

    # Sử dụng query_points để tương thích với qdrant-client bản mới
    search_result = self.client.query_points(
        collection_name=self.collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
    )
    return search_result.points


if __name__ == "__main__":
  print("Đang kiểm tra kết nối Qdrant...")
  try:
    manager = LegalQdrantManager()
    print("Kết nối Qdrant thành công!")
  except Exception as e:
    print(
        f"Không thể kết nối tới Qdrant. Hãy đảm bảo Qdrant đang chạy (qua"
        f" Docker): {e}"
    )