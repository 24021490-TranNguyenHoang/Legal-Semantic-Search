import sys
from src.search.legal_retriever import LegalRetriever

# Đảm bảo mã hóa console UTF-8 trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    print("[*] Đang khởi tạo mô hình và kết nối cơ sở dữ liệu...")
    retriever = LegalRetriever()
    
    # Câu hỏi thử nghiệm mặc định
    query = "vượt đèn đỏ bị phạt như nào"
    print(f"\n[?] Câu hỏi người dùng: '{query}'\n")
    
    print("[*] Đang phân tích ý định và thực hiện Hybrid Search...")
    analysis, results = retriever.search(query, top_k=3)
    
    print("=" * 80)
    print("KẾT QUẢ PHÂN TÍCH NGỮ NGHĨA:")
    print("=" * 80)
    print(f"- Hành vi vi phạm nhận diện: {analysis['matched_violations'] or 'Quy tắc chung'}")
    print(f"- Ý định hỏi chế tài xử phạt: {'Có (Tra cứu mức phạt)' if analysis['is_penalty'] else 'Không'}")
    print(f"- Phương tiện phát hiện: {analysis['vehicle_label'] or 'Áp dụng chung mọi phương tiện'}")
    print(f"- Truy vấn mở rộng pháp lý: {analysis['expanded_query']}")
    print("=" * 80)
    print("KẾT QUẢ TÌM KIẾM ĐÃ TỐI ƯU (HYBRID + LEGAL RESCORING):")
    print("=" * 80)
    
    for rank, item in enumerate(results, start=1):
        fine = f" | Mức phạt: {item['fine_amount']}" if item.get('fine_amount') else ""
        vehicle = f" | Đối tượng: {item.get('vehicle_type', '')}"
        print(f"\n[Top {rank}] - Điểm phù hợp: {item['score']:.4f}{fine}{vehicle}")
        print(f"Trích dẫn: {item.get('citation_path')}")
        print(f"Văn bản: {item.get('law_title')} ({item.get('law_id')})")
        print(f"Nội dung:\n{item.get('original_text')[:300]}...\n")

if __name__ == "__main__":
    main()