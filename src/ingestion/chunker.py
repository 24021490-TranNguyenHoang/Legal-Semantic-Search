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

def main(argv=None):
    from src.config import CLEANED_DIR
    from src.pipeline_cli import (pipeline_parser, run_cli, staging_path, input_files,
                                  validate_records, write_jsonl, staged_run, check_message)

    def action(args):
        staging_path(args.run_dir)
        files = input_files(args.input_path, (".txt",))
        chunks = []
        for path in files:
            parsed = parse_and_chunk(str(path))
            if not parsed:
                raise ValueError(f"Parser produced no chunks: {path}")
            chunks.extend(parsed)
        validate_records(chunks)
        if args.check_only:
            check_message(len(chunks))
            return
        with staged_run(args.run_dir, "chunker", args.input_path) as (run, report):
            write_jsonl(run / "corpus_chunks.jsonl", chunks)
            report["chunk_count"] = len(chunks)
            print(f"OK: {len(chunks)} prototype chunks -> {run}")

    return run_cli(pipeline_parser("Run unchanged prototype chunker into staging", CLEANED_DIR,
                                   directory=True), action, argv)


if __name__ == "__main__":
    raise SystemExit(main())
