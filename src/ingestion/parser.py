import os
import re
import json


def parse_legal_text(file_path):
  """Hàm đọc file văn bản luật đã làm sạch và bóc tách thành các Điều luật."""
  if not os.path.exists(file_path):
    print(f"Không tìm thấy file: {file_path}")
    return []

  with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

  # Regex nhận diện các Điều luật (Ví dụ: "Điều 1.", "Điều 15:", ...)
  article_pattern = re.compile(
      r"(Điều\s+\d+[\.\s*].*?)(?=Điều\s+\d+[\.\s*]|\Z)", re.S
  )
  raw_articles = article_pattern.findall(content)

  parsed_articles = []
  for index, art_text in enumerate(raw_articles):
    lines = art_text.strip().split("\n")
    article_title = lines[0].strip()  # Tên Điều (VD: Điều 1. Phạm vi điều chỉnh)
    article_body = "\n".join(lines[1:]).strip()  # Nội dung bên dưới

    # Trích xuất số hiệu điều bằng regex
    art_num_match = re.search(r"Điều\s+(\d+)", article_title)
    article_number = int(art_num_match.group(1)) if art_num_match else index + 1

    parsed_articles.append({
        "article_number": article_number,
        "article_title": article_title,
        "content": article_body,
    })

  return parsed_articles


if __name__ == "__main__":
  # Kiểm tra file mẫu trong thư mục data/processed/cleaned (nếu có)
  # Bạn có thể thay đổi đường dẫn cho phù hợp với dữ liệu thực tế của bạn
  sample_file = "data/processed/cleaned/35.2024.QH15_cleaned.txt"

  # Nếu chưa có file data thực tế, bạn có thể tạo một file test nhỏ để thử nghiệm
  if os.path.exists(sample_file):
    results = parse_legal_text(sample_file)
    print(f"Đã bóc tách thành công {len(results)} điều luật từ {sample_file}")
    if results:
      print("\n--- Ví dụ Điều đầu tiên ---")
      print(json.dumps(results[0], ensure_ascii=False, indent=2))
  else:
    print(
        f"Chưa tìm thấy file mẫu tại {sample_file}. Hãy đảm bảo bạn đã đặt file"
        " dữ liệu vào đúng thư mục."
    )