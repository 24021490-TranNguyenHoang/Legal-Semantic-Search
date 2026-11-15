import os
import json
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from sentence_transformers import SentenceTransformer

def parse_metadata_from_filename(filename):
    """Tự động suy luận Metadata từ tên file văn bản luật"""
    name = filename.replace("_cleaned.txt", "").replace(".txt", "")
    
    # Xác định loại văn bản
    if "QH" in name or "Luật" in name:
        law_type = "Luật"
    elif "NĐ" in name or "Nghị định" in name:
        law_type = "Nghị định"
    elif "TT" in name or "Thông tư" in name:
        law_type = "Thông tư"
    else:
        law_type = "Văn bản khác"
        
    # Xác định năm ban hành (tìm cụm 4 chữ số năm, ví dụ 2024)
    year = 2024 # Mặc định theo đồ án
    for part in name.split('.'):
        if part.isdigit() and len(part) == 4:
            year = int(part)
            
    return {
        "document_id": name,
        "law_type": law_type,
        "year": year
    }

def main():
    print("🚀 Bắt đầu quá trình nạp tài liệu kèm Metadata chuyên sâu...")
    
    cleaned_dir = "data/processed/cleaned"
    if not os.path.exists(cleaned_dir):
        print(f"❌ Không tìm thấy thư mục: {cleaned_dir}")
        return

    all_files = [f for f in os.listdir(cleaned_dir) if f.endswith(".txt")]
    if not all_files:
        print(f"❌ Không tìm thấy file văn bản .txt nào trong {cleaned_dir}")
        return

    all_chunks = []

    for filename in all_files:
        file_path = os.path.join(cleaned_dir, filename)
        print(f"📂 Đang xử lý file và trích xuất Metadata: {filename}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        meta = parse_metadata_from_filename(filename)
        
        # Chia chunk theo Điều luật
        raw_articles = raw_text.split("Điều ")
        for article in raw_articles[1:]:
            lines = article.strip().split("\n")
            article_title = f"Điều {lines[0]}"
            article_content = "\n".join(lines)
            
            all_chunks.append({
                "document_id": meta["document_id"],
                "law_type": meta["law_type"],
                "year": meta["year"],
                "article_title": article_title,
                "chunk_text": article_content
            })

    print(f"📦 Tổng cộng đã gom và gán metadata cho {len(all_chunks)} điều luật.")

    # Khởi tạo Qdrant Client và Model Embedding
    client = QdrantClient(host="localhost", port=6333)
    collection_name = "legal_documents"
    
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

    model = SentenceTransformer("all-MiniLM-L6-v2")

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
    print(f"✅ Đã nạp thành công {len(points)} vectors kèm Metadata lên Qdrant!")

    os.makedirs("data/processed", exist_ok=True)
    with open("data/processed/chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=4)
    print("💾 Đã lưu dữ liệu chunks.json thành công!")

if __name__ == "__main__":
    main()