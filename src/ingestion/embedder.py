import os
import sys
from sentence_transformers import SentenceTransformer

# Thêm đường dẫn gốc để import các module khác trong project
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

from src.database.qdrant_client import LegalQdrantManager
from src.ingestion.chunker import create_chunks_from_articles
from src.ingestion.parser import parse_legal_text


def process_and_store_pipeline():
  # 1. Đường dẫn file luật mẫu (đảm bảo file này đã tồn tại ở bước 1)
  sample_file = "data/processed/cleaned/35.2024.QH15_cleaned.txt"

  if not os.path.exists(sample_file):
    print(f"Không tìm thấy file: {sample_file}")
    print("Hãy chắc chắn bạn đã tạo file dữ liệu mẫu ở Bước 1 nhé.")
    return

  print("-> [1/4] Đang tiến hành parse văn bản luật...")
  articles = parse_legal_text(sample_file)

  print("-> [2/4] Đang tạo chunks và gán metadata...")
  chunks = create_chunks_from_articles(
      articles, document_id="35.2024.QH15", document_name="Luật Đường bộ 2024"
  )

  print("-> [3/4] Đang tải mô hình embedding (all-MiniLM-L6-v2)...")
  # Mô hình này tạo ra vector 384 chiều, phù hợp với cấu hình Qdrant
  model = SentenceTransformer("all-MiniLM-L6-v2")

  # Lấy danh sách nội dung text từ các chunk để đem đi mã hóa thành vector
  texts_to_embed = [chunk["chunk_text"] for chunk in chunks]

  print("Đang chuyển đổi văn bản thành vector embedding...")
  vectors = model.encode(texts_to_embed).tolist()

  print("-> [4/4] Đang kết nối và lưu trữ dữ liệu lên Qdrant...")
  qdrant_manager = LegalQdrantManager()
  qdrant_manager.upsert_chunks(chunks, vectors)

  print("🎉 Hoàn tất toàn bộ pipeline nạp dữ liệu lên Vector DB thành công!")


if __name__ == "__main__":
  process_and_store_pipeline()