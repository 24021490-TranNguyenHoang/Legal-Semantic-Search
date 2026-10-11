import os
import re
import json

# THÊM HÀM NÀY VÀO ĐÂY
def enrich_context(law_title, chapter_title, article_title, chunk_content):
    law = law_title.strip()
    chapter = chapter_title.strip() if chapter_title else ""
    article = article_title.strip()
    content = chunk_content.strip()
    
    if chapter:
        return f"Theo {law}, {chapter}, {article} quy định: {content}"
    return f"Theo {law}, {article} quy định: {content}"

def determine_doc_info(filename: str):
    """
    Tự động xác định mã luật, số hiệu và tên văn bản
    khớp chính xác với tên file trong thư mục raw_data của bạn.
    """
    fn = filename.lower()
    if "168" in fn:
        return "168/2024/NĐ-CP", "Nghị định 168/2024/NĐ-CP", "2025-01-01"
    elif "165" in fn:
        return "165/2024/NĐ-CP", "Nghị định 165/2024/NĐ-CP", "2025-01-01"
    elif "35" in fn:
        return "35/2024/QH15", "Luật Đường bộ", "2025-01-01"
    elif "36" in fn or "trat tu" in fn:
        return "36/2024/QH15", "Luật Trật tự, an toàn giao thông đường bộ", "2025-01-01"
    else:
        return "VBPL_GIAO_THONG", "Văn bản quy phạm pháp luật giao thông", "2025-01-01"

def parse_and_chunk(file_path: str):
    filename = os.path.basename(file_path)
    law_id, law_title, effective_date = determine_doc_info(filename)
    
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.split('\n')
    chunks = []
    
    current_chapter = ""
    current_article_id = ""
    current_article_title = ""
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # 1. Nhận diện Chương
        chap_match = re.match(r'^(Chương\s+[IVXLCDM\d]+)(?:\.\s*|\s*[-–—:]\s*|\s+)(.*)?', line, re.IGNORECASE)
        if chap_match:
            chap_num = chap_match.group(1).title()
            chap_title = chap_match.group(2).strip() if chap_match.group(2) else ""
            if not chap_title and i + 1 < len(lines):
                next_l = lines[i+1].strip()
                if not re.match(r'^(Điều\s+\d+|Mục\s+)', next_l, re.IGNORECASE):
                    chap_title = next_l
                    i += 1
            current_chapter = f"{chap_num}\n{chap_title}".strip(" -")
            i += 1
            continue

        # 2. Nhận diện Điều
        art_match = re.match(r'^(Điều\s+(\d+[a-z]?))\.\s*(.*)', line, re.IGNORECASE)
        if art_match:
            current_article_id = art_match.group(1).title()
            current_article_title = art_match.group(3).strip()
            
            j = i + 1
            intro_lines = []
            has_clause = False
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                if re.match(r'^(Điều\s+\d+|Chương\s+[IVXLCDM\d]+|Mục\s+)', next_line, re.IGNORECASE):
                    break
                if re.match(r'^\d+\.\s+', next_line):
                    has_clause = True
                    break
                intro_lines.append(next_line)
                j += 1
            
            # Nếu Điều không chia Khoản -> lưu cả Điều thành 1 Chunk
            if not has_clause and intro_lines:
                content = " ".join(intro_lines)
                citation = f"{law_title} > {current_chapter} > {current_article_id}" if current_chapter else f"{law_title} > {current_article_id}"
                c_id = f"{law_id.replace('/', '_').replace('.', '_')}_{current_article_id.replace(' ', '_')}".lower()
                
                # --- SỬ DỤNG HÀM ENRICH CONTEXT Ở ĐÂY ---
                original_text_str = f"{current_article_id}. {current_article_title}: {content}".strip()
                enriched_text_str = enrich_context(law_title, current_chapter, current_article_title, content)
                
                chunks.append({
                    "chunk_id": c_id,
                    "law_id": law_id,
                    "law_title": law_title,
                    "chapter": current_chapter or None,
                    "article_id": current_article_id,
                    "article_title": current_article_title or None,
                    "clause_id": None,
                    "point_id": None,
                    "citation_path": citation,
                    "original_text": original_text_str,   # Đổi từ "text" thành "original_text"
                    "enriched_text": enriched_text_str,   # Thêm trường "enriched_text"
                    "effective_date": effective_date,
                    "expire_date": None,
                    "status": "active"
                })
            i = j
            continue

        # 3. Nhận diện Khoản (1. , 2. ...)
        clause_match = re.match(r'^(\d+)\.\s+(.*)', line)
        if clause_match and current_article_id:
            clause_num = clause_match.group(1)
            clause_id = f"Khoản {clause_num}"
            content_lines = [clause_match.group(2)]
            
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                if re.match(r'^(Điều\s+\d+|Chương\s+[IVXLCDM\d]+|Mục\s+|\d+\.\s+)', next_line, re.IGNORECASE):
                    break
                content_lines.append(next_line)
                j += 1
                
            content = " ".join(content_lines)
            citation = f"{law_title} > {current_chapter} > {current_article_id} > {clause_id}" if current_chapter else f"{law_title} > {current_article_id} > {clause_id}"
            c_id = f"{law_id.replace('/', '_').replace('.', '_')}_{current_article_id.replace(' ', '_')}_k{clause_num}".lower()
            
            full_chunk_text = f"{current_article_id}. {current_article_title}\n{clause_id}: {content}".strip()
            
            # --- SỬ DỤNG HÀM ENRICH CONTEXT Ở ĐÂY ---
            enriched_text_str = enrich_context(law_title, current_chapter, current_article_title, content)
            
            chunks.append({
                "chunk_id": c_id,
                "law_id": law_id,
                "law_title": law_title,
                "chapter": current_chapter or None,
                "article_id": current_article_id,
                "article_title": current_article_title or None,
                "clause_id": clause_id,
                "point_id": None,
                "citation_path": citation,
                "original_text": full_chunk_text,     # Đổi từ "text" thành "original_text"
                "enriched_text": enriched_text_str,   # Thêm trường "enriched_text"
                "effective_date": effective_date,
                "expire_date": None,
                "status": "active"
            })
            i = j
            continue

        i += 1
        
    return chunks

if __name__ == "__main__":
    cleaned_dir = "cleaned_data"
    output_jsonl = "corpus_chunks.jsonl"
    
    print(f"[*] Đang kiểm tra thư mục: {os.path.abspath(cleaned_dir)}")
    if not os.path.exists(cleaned_dir):
        print(f"[!] Thư mục {cleaned_dir} không tồn tại!")
        exit(1)
        
    all_files = os.listdir(cleaned_dir)
    print(f"[*] Tìm thấy {len(all_files)} file: {all_files}")
    
    all_chunks = []
    txt_files = [f for f in all_files if f.endswith(".txt")]
    
    for f in txt_files:
        p = os.path.join(cleaned_dir, f)
        print(f"[*] Đang cắt chunk cho: {f}...")
        res = parse_and_chunk(p)
        print(f"    -> Tạo thành công: {len(res)} chunks.")
        all_chunks.extend(res)
        
    with open(output_jsonl, "w", encoding="utf-8") as out:
        for chk in all_chunks:
            out.write(json.dumps(chk, ensure_ascii=False) + "\n")
            
    print(f"\n[+] TẤT CẢ HOÀN TẤT!")
    print(f"[+] Tổng số chunks xuất ra: {len(all_chunks)} chunks.")
    print(f"[+] Đã lưu tại tệp: '{output_jsonl}'")