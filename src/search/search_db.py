from pathlib import Path
from src.config import CHUNKS_FILE, QDRANT_PATH
from src.pipeline_cli import run_cli, search_parser, validate_search_args


def search(args):
    from src.search.legal_retriever import LegalRetriever
    validate_search_args(args)
    print("[*] Đang khởi tạo mô hình và kết nối cơ sở dữ liệu...")
    retriever = LegalRetriever(args.input_path, args.qdrant_path)

    try:
        # Truy vấn do người chạy cung cấp
        query = args.query
        print(f"\n[?] Câu hỏi người dùng: '{query}'\n")

        print("[*] Đang phân tích ý định và thực hiện Hybrid Search...")
        analysis, results = retriever.search(query, top_k=args.top_k)

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
    finally:
        retriever.client.close()


def main(argv=None):
    parser = search_parser("Run existing prototype Hybrid retrieval (not a benchmark)")
    parser.add_argument("--input", type=Path, default=CHUNKS_FILE, dest="input_path")
    parser.add_argument("--qdrant-path", type=Path, default=Path(QDRANT_PATH))
    return run_cli(parser, search, argv)


if __name__ == "__main__":
    raise SystemExit(main())
