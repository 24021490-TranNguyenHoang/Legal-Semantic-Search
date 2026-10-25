import os
import json
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from sentence_transformers import SentenceTransformer

def main():
    print("🚀 Bắt đầu quá trình nạp toàn bộ tài liệu luật vào hệ thống...")
    
    cleaned_dir = "data/processed/cleaned"
    if not os.path.exists(cleaned_dir):
        print(f"❌ Không tìm thấy thư mục: {cleaned_dir}")
        return

    # Lấy danh sách tất cả các file .txt trong thư mục
    all_files = [f for f in os.listdir(cleaned_dir) if f.endswith(".txt")]
    
    if not all_files:
        print(f"❌ Không tìm thấy file văn bản .txt nào trong {cleaned_dir}")
        return

    all_chunks = []
    global_id = 0

    # Duyệt qua từng file để đọc và cắt chunk
    for filename in all_files:
        file_path = os.path.join(cleaned_dir, filename)
        print(f"📂 Đang xử lý file: {filename}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Dùng tên file làm document_id (bỏ phần đuôi _cleaned.txt)
        doc_id = filename.replace("_cleaned.txt", "").replace(".txt", "")
        
        # Chia chunk theo Điều luật
        raw_articles = raw_text.split("Điều ")
        for article in raw_articles[1:]:
            lines = article.strip().split("\n")
            article_title = f"Điều {lines[0]}"
            article_content = "\n".join(lines)
            
            all_chunks.append({
                "document_id": doc_id,
                "article_title": article_title,
                "chunk_text": article_content
            })

    print(f"📦 Tổng cộng đã gom được {len(all_chunks)} điều luật từ tất cả các file.")

    # Khởi tạo Qdrant Client và Model Embedding
    client = QdrantClient(host="localhost", port=6333)
    collection_name = "legal_documents"
    
    # Tạo collection nếu chưa có
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Vector hóa và Upsert lên Qdrant
    points = []
    for i, chunk in enumerate(all_chunks):
        vector = model.encode(chunk["chunk_text"]).tolist()
        points.append({
            "id": i,
            "vector": vector,
            "payload": chunk
        })

    client.upsert(
        collection_name=collection_name,
        points=points
    )
    print(f"✅ Đã nạp thành công {len(points)} vectors từ tất cả các file lên Qdrant!")

    # Lưu file chunks.json tổng hợp để phục vụ cho BM25 Search
    os.makedirs("data/processed", exist_ok=True)
    with open("data/processed/chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=4)
    print("💾 Đã lưu toàn bộ dữ liệu vào chunks.json cho BM25 thành công!")

if __name__ == "__main__":
    main()