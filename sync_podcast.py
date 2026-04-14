import feedparser
import requests
import json
import os
from huggingface_hub import HfApi

# Cấu hình
RSS_URL = "https://www.spreaker.com/show/6422189/episodes/feed"
HF_REPO = "ten-tai-khoan-cua-ban/audio-backup" # Thay bằng ID Dataset của bạn
HF_TOKEN = os.getenv("HF_TOKEN")
JSON_FILE = "playlist.json"

api = HfApi()

def sync():
    # 1. Đọc playlist hiện tại
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        playlist = json.load(f)
    
    existing_urls = [item['original_url'] for item in playlist]

    # 2. Lấy dữ liệu từ RSS Spreaker
    feed = feedparser.parse(RSS_URL)
    new_items = []

    for entry in reversed(feed.entries): # Duyệt từ cũ đến mới
        original_url = entry.enclosures[0].href
        
        if original_url not in existing_urls:
            title = entry.title
            file_name = f"{entry.id}.mp3".replace(":", "_") # Tạo tên file an toàn
            
            print(f"Đang xử lý tập mới: {title}")

            # 3. Tải file từ Spreaker (IP GitHub ở Mỹ nên không bị chặn)
            response = requests.get(original_url)
            with open(file_name, "wb") as f:
                f.write(response.content)

            # 4. Đẩy lên Hugging Face
            api.upload_file(
                path_or_fileobj=file_name,
                path_in_repo=f"audio/{file_name}",
                repo_id=HF_REPO,
                repo_type="dataset",
                token=HF_TOKEN
            )

            # 5. Tạo link Raw từ Hugging Face để nghe tại VN
            hf_raw_url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/audio/{file_name}"
            
            new_items.append({
                "title": title,
                "url": hf_raw_url,
                "original_url": original_url,
                "duration": entry.get("itunes_duration", "")
            })
            
            # Xóa file tạm sau khi upload
            os.remove(file_name)

    if new_items:
        # Cập nhật playlist (đưa bài mới lên đầu)
        updated_playlist = new_items + playlist
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_playlist, f, ensure_ascii=False, indent=2)
        return True
    return False

if __name__ == "__main__":
    if sync():
        print("Đã cập nhật tập mới thành công!")
    else:
        print("Không có tập mới.")
