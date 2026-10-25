import json
import os
from src.ingestion.parser import parse_legal_text


def create_chunks_from_articles(articles, document_id="35.2024.QH15", document_name="Luật Đường bộ 2024"):
    """
    Nhận vào danh sách các điều luật đã parse và chuyển đổi thành danh sách các chunk 
    kèm theo metadata đầy đủ.
    """
    chunks = []
    for art in articles:
        article_number = art["article_number"]
        article_title = art["article_title"]
        content = art["content"]

        # Tạo một chunk đại diện cho toàn bộ điều luật (hoặc bạn có thể chia nhỏ hơn theo Khoản)
        chunk_id = f"{document_id}_art_{article_number}"
        
        chunk_data = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "document_name": document_name,
            "article_number": article_number,
            "article_title": article_title,
            "chunk_text": f"{article_title}\n{content}",
            "metadata": {
                "source": document_id,
                "type": "article"
            }
        }
        chunks.append(chunk_data)

    return chunks

if __name__ == "__main__":
    sample_file = "data/processed/cleaned/35.2024.QH15_cleaned.txt"
    
    if os.path.exists(sample_file):
        # 1. Parse văn bản thành các Điều
        articles = parse_legal_text(sample_file)
        
        # 2. Tạo chunks từ các Điều đó
        chunks = create_chunks_from_articles(articles)
        
        print(f"Đã tạo thành công {len(chunks)} chunks kèm metadata từ file luật.")
        if chunks:
            print("\n--- Ví dụ Chunk đầu tiên kèm Metadata ---")
            print(json.dumps(chunks[0], ensure_ascii=False, indent=2))
    else:
        print(f"Không tìm thấy file mẫu tại {sample_file}")