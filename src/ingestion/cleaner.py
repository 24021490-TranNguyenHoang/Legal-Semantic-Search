import os
import re
import unicodedata
import pdfplumber
import docx

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
    doc = docx.Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)

def read_pdf(file_path: str) -> str:
    """Trích xuất nội dung văn bản từ tệp PDF."""
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

if __name__ == "__main__":
    raw_dir = "raw_data"
    output_dir = "cleaned_data"
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(raw_dir):
        print(f"[!] Thư mục '{raw_dir}' chưa tồn tại. Vui lòng tạo thư mục và đưa các tệp văn bản vào.")
    else:
        files = [f for f in os.listdir(raw_dir) if f.lower().endswith(('.pdf', '.docx'))]
        if not files:
            print(f"[!] Không tìm thấy tệp .pdf hoặc .docx nào trong '{raw_dir}'.")
        else:
            for filename in files:
                input_path = os.path.join(raw_dir, filename)
                base_name = os.path.splitext(filename)[0]
                output_path = os.path.join(output_dir, f"{base_name}_cleaned.txt")
                
                print(f"[*] Đang xử lý: {filename}...")
                try:
                    cleaned_content = extract_and_clean(input_path)
                    with open(output_path, "w", encoding="utf-8") as out_f:
                        out_f.write(cleaned_content)
                    print(f"    -> Đã lưu văn bản sạch: {output_path} ({len(cleaned_content)} ký tự)")
                except Exception as e:
                    print(f"    [X] Lỗi khi xử lý {filename}: {e}")
            print("\n[+] Đã hoàn thành xử lý toàn bộ dữ liệu thô!")