import os
import re
import unicodedata

def clean_text(text: str) -> str:
    """Làm sạch văn bản, chuẩn hóa font và loại bỏ các thành phần rác."""
    # 1. Chuẩn hóa bảng mã tiếng Việt về chuẩn Unicode dựng sẵn (NFC)
    text = unicodedata.normalize('NFC', text)
    
    # 2. Danh sách các cụm từ hành chính/tiêu đề trang lặp lại cần loại bỏ
    boilerplates = [
        r"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        r"Độc lập\s*[-–—]\s*Tự do\s*[-–—]\s*Hạnh phúc",
        r"CHỦ TỊCH QUỐC HỘI",
        r"Trần Thanh Mẫn",
        r"TM\.\s*CHÍNH PHỦ",
        r"KT\.\s*THỦ TƯỚNG",
        r"PHÓ THỦ TƯỚNG",
        r"Trần Hồng Hà",
        r"Người ký:\s*CỔNG THÔNG TIN ĐIỆN TỬ.*?(\+07:00)",
        r"Email:\s*thongtinchinhphu@chinhphu\.vn",
        r"Cơ quan:\s*VĂN PHÒNG CHÍNH PHỦ",
        r"Thời gian ký:.*?\+07:00",
        r"Luật số:\s*\d+/\d+/QH\d+",
        r"Số:\s*\d+/\d+/NĐ-CP"
    ]
    for bp in boilerplates:
        text = re.sub(bp, '', text, flags=re.IGNORECASE | re.DOTALL)
        
    # 3. Loại bỏ dòng chỉ chứa số trang (ví dụ dòng chỉ có '12' hoặc ' 3 ')
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    
    # 4. Chuẩn hóa khoảng trắng ngang (tab/space thừa)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 5. Loại bỏ các dòng trống liên tiếp nhưng giữ cấu trúc xuống dòng
    text = re.sub(r'\n\s*\n+', '\n', text)
    
    return text.strip()

def read_docx(file_path: str) -> str:
    """Trích xuất nội dung văn bản từ tệp DOCX."""
    import docx
    doc = docx.Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)

def read_pdf(file_path: str) -> str:
    """Trích xuất nội dung văn bản từ tệp PDF."""
    import pdfplumber
    extracted_pages = []
    with pdfplumber.open(file_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                extracted_pages.append(page_text)
    return "\n".join(extracted_pages)

def extract_and_clean(file_path: str) -> str:
    """Đọc và làm sạch văn bản theo định dạng tệp."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.docx':
        raw_text = read_docx(file_path)
    elif ext == '.pdf':
        raw_text = read_pdf(file_path)
    else:
        raise ValueError(f"Định dạng {ext} không được hỗ trợ.")
    return clean_text(raw_text)

def main(argv=None):
    from src.config import RAW_DIR
    from src.pipeline_cli import (pipeline_parser, run_cli, staging_path,
                                  input_files, staged_run, check_message)

    def action(args):
        staging_path(args.run_dir)
        files = input_files(args.input_path, (".docx", ".pdf"))
        names = [f"{p.stem}_cleaned.txt".casefold() for p in files]
        if len(set(names)) != len(names):
            raise ValueError("Input filenames would create duplicate cleaned outputs")
        # Read the entire batch before creating any output.
        cleaned = []
        for path in files:
            text = extract_and_clean(str(path))
            if not text.strip():
                raise ValueError(f"No extracted text: {path}")
            cleaned.append((path, text))
        if args.check_only:
            check_message(len(cleaned))
            return
        with staged_run(args.run_dir, "cleaner", args.input_path) as (run, report):
            target = run / "cleaned"
            target.mkdir()
            for path, text in cleaned:
                with (target / f"{path.stem}_cleaned.txt").open(
                        "x", encoding="utf-8", newline="\n") as output:
                    output.write(text)
            report["file_count"] = len(cleaned)
            print(f"OK: {len(cleaned)} cleaned files -> {target}")

    return run_cli(pipeline_parser("Extract/clean prototype sources into staging", RAW_DIR,
                                   directory=True), action, argv)


if __name__ == "__main__":
    raise SystemExit(main())
