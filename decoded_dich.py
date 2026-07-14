# -*- coding: utf-8 -*-

import sys
import os
import re
import time
import json
import shutil
from typing import List, Tuple, Optional, Any
from functools import wraps
from difflib import SequenceMatcher

# Cài đặt thư viện: pip install PyQt6 python-dotenv openai google-generativeai
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QTextEdit, QProgressBar, QGroupBox,
    QRadioButton, QMessageBox, QFormLayout, QCheckBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTabWidget
)
from PyQt6.QtCore import QThread, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QFont

from dotenv import load_dotenv, set_key, find_dotenv
from openai import OpenAI, APIError
import google.generativeai as genai
import httpx

# ================== HTTPX WRAPPER FOR OPENAI (BYPASS SDK BUG) ==================
class HTTPXOpenAIClient:
    """
    Wrapper để gọi OpenAI API trực tiếp bằng HTTPX.
    Dùng để bypass bug của OpenAI SDK trên Windows.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.timeout = REQUEST_TIMEOUT
    
    def chat_completion(self, model: str, system_prompt: str, user_prompt: str) -> str:
        """Gọi chat completion API trực tiếp qua HTTPX"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'] or ""
            else:
                # Raise exception để retry decorator xử lý
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                raise Exception(error_msg)

# ================== CẤU HÌNH & HẰNG SỐ ==================
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite", "gemini-2.0-flash"]
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
GROK_MODELS = ["grok-3", "grok-3-mini", "grok-2"]

DEFAULT_SYSTEM_PROMPT = (
    "Bạn là dịch giả chuyên nghiệp phim tiên hiệp Trung Quốc. "
    "Dịch phụ đề từ tiếng Trung sang tiếng Việt cho TIÊN NGHỊCH (仙逆).\n\n"
    
    "【VĂN PHONG - CỰC KỲ QUAN TRỌNG】\n"
    "• Dịch THOÁT Ý, câu văn tiếng Việt TỰ NHIÊN, dễ hiểu, mượt mà\n"
    "• TUYỆT ĐỔI KHÔNG dịch word-by-word theo cấu trúc Hán\n"
    "• Giữ thuật ngữ tu tiên/cổ trang ĐÚNG theo glossary (cảnh giới, pháp bảo, tông môn...)\n"
    "• Nhưng câu nói thường ngày phải DỄ HIỂU, không dùng Hán Việt xa lạ\n"
    "• Dùng đại từ cổ trang: ngươi, ta, hắn, nàng, Vương mỗ, lão phu\n"
    "• Dùng 'tu vy' (KHÔNG phải 'tu vi'), 'vy sư' (KHÔNG phải 'vi sư')\n\n"
    
    "【CẤM DÙNG CẤU TRÚC HÁN VIỆT KHÓ HIỂU】\n"
    "• 之前/chi tiền → 'trước đó', 'trước kia'\n"
    "• 此刻/thử khắc → 'lúc này', 'giờ đây'\n"
    "• 一个/nhất cá → 'một'\n"
    "• 已然/dĩ nhiên → 'đã'\n"
    "• 施法/thi pháp → 'dùng phép', 'thi triển'\n"
    "• 进入/tiến nhập → 'đi vào', 'bước vào'\n"
    "• 以后/dĩ hậu → 'sau này', 'về sau'\n"
    "• 此/thử → 'này', 'đây'\n"
    "• 其/kỳ → 'của hắn/nàng', bỏ nếu thừa\n"
    "• 之中/chi trung → 'trong', 'bên trong'\n"
    "• 一股/nhất bàn → 'một luồng', 'một làn'\n"
    "• 不知尽头/bất tri tẫn đầu → 'không biết điểm dừng'\n"
    "• 默默地/mặc mặc địa → 'lặng lẽ'\n"
    "• 区区/khu khu → 'chỉ là', 'cái'\n"
    "• 之力/chi lực → 'sức mạnh của'\n"
    "• KHÔNG dùng cấu trúc 'X chi Y' → thay bằng 'Y của X' hoặc diễn đạt tự nhiên\n"
    "• VD: '此刻从远处天地间传到之一股浩荡仙气' → 'Lúc này từ xa tận trời đất có một luồng tiên khí hùng hậu truyền đến'\n\n"
    
    "【OCR NOISE】\n"
    "• Phụ đề có thể chứa lỗi OCR. Suy đoán nghĩa đúng từ ngữ cảnh\n"
    "• 噶去/嘎去 = chết, 嘎人/噶人 = giết người, 设有 = 没有\n"
    "• Text lặp/rác → chỉ dịch phần có nghĩa\n"
    "• KHÔNG BAO GIỜ để nguyên ký tự Trung trong bản dịch\n\n"
    
    "【TÊN RIÊNG & XƯNG HÔ】\n"
    "• Dùng CHÍNH XÁC bảng thuật ngữ kèm theo. Đây là yêu cầu bắt buộc\n"
    "• Giữ nhất quán tên riêng, xưng hô theo nguyên văn\n\n"
    
    "【ĐỊNH DẠNG - NGHIÊM NGẶT】\n"
    "• Input: [số]|text tiếng Trung. Output: [cùng số]|text tiếng Việt\n"
    "• CHỈ trả về danh sách đã dịch, không giải thích"
)

# Các thông số có thể điều chỉnh
REQUEST_TIMEOUT = 180  # giây (tăng vì batch lớn hơn)
MAX_RETRIES = 5
RETRY_BASE_SLEEP = 2.5 # giây
CONTEXT_OVERLAP = 8    # Số block cuối của batch trước dùng làm ngữ cảnh
BATCH_SIZE = 250        # Số block gửi trong 1 lần gọi API (batch lớn hơn = nhiều ngữ cảnh hơn)
FAIL_BEHAVIOR = "keep-original" # 'keep-original' hoặc 'empty'

# Biểu thức chính quy để phân tích SRT
IDX_RE = re.compile(r"^\d+$")
TS_RE = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}(?:\s+.*)?$")


# ================== PHẦN LOGIC DỊCH ==================

# [TỐI ƯU HÓA] Dùng decorator để xử lý việc thử lại (retry) khi gọi API, tránh lặp code
def api_retry_decorator(func):
    """Decorator để tự động thử lại khi gọi API thất bại."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        delay = RETRY_BASE_SLEEP
        last_exception = None
        for i in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"Lỗi API (lần {i+1}/{MAX_RETRIES}): [{error_type}] {error_msg}")
                if i < MAX_RETRIES - 1:  # Không sleep ở lần thử cuối
                    print(f"Thử lại sau {delay:.2f}s...")
                    time.sleep(delay)
                    delay *= 1.6
        # In chi tiết lỗi cuối cùng
        print(f"\n❌ TẤT CẢ {MAX_RETRIES} LẦN THỬ ĐỀU THẤT BẠI!")
        print(f"Chi tiết lỗi: {type(last_exception).__name__}: {last_exception}")
        if hasattr(last_exception, '__cause__') and last_exception.__cause__:
            print(f"Nguyên nhân gốc: {last_exception.__cause__}")
        if last_exception:
            raise last_exception
        return "" 
    return wrapper

@api_retry_decorator
def call_openai_api(client, model: str, system_prompt: str, user_prompt: str) -> str:
    """Gọi API của OpenAI (hỗ trợ cả HTTPX và SDK)."""
    if isinstance(client, HTTPXOpenAIClient):
        # Dùng HTTPX trực tiếp (bypass SDK bug)
        return client.chat_completion(model, system_prompt, user_prompt)
    else:
        # Fallback to SDK (for backward compatibility)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0.3, timeout=REQUEST_TIMEOUT
        )
        return resp.choices[0].message.content or ""

@api_retry_decorator
def call_gemini_api(client: genai, model_name: str, system_prompt: str, user_prompt: str) -> str:
    """Gọi API của Google Gemini."""
    model = client.GenerativeModel(model_name, system_instruction=system_prompt)
    resp = model.generate_content(
        user_prompt,
        generation_config=genai.types.GenerationConfig(temperature=0.3),
        request_options={'timeout': REQUEST_TIMEOUT}
    )
    return resp.text or ""

# ================== SMART GLOSSARY ==================
# ================== SMART GLOSSARY ==================
def _get_base_path():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        if os.path.isdir(os.path.join(exe_dir, "glossaries")):
            return exe_dir
        # Nếu ở root không có, thử tìm bên trong _internal (sys._MEIPASS)
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

_b = _get_base_path()
GLOSSARY_PATH = os.path.join(_b, "glossary.json")
GLOSSARIES_DIR = os.path.join(_b, "glossaries")
DEFAULT_GLOSSARY = "glossary.json"  # File mặc định trong thư mục glossaries/

def get_glossary_files() -> list:
    """Quét thư mục glossaries/ và trả về danh sách tên file .json."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        exe_glossaries = os.path.join(exe_dir, "glossaries")
        if not os.path.isdir(exe_glossaries):
            os.makedirs(exe_glossaries, exist_ok=True)
            # Copy từ bản gốc trong _internal ra ngoài
            default_internal_glossary = os.path.join(sys._MEIPASS, "glossary.json")
            if os.path.exists(default_internal_glossary):
                import shutil
                shutil.copy2(default_internal_glossary, os.path.join(exe_dir, DEFAULT_GLOSSARY))
                shutil.copy2(default_internal_glossary, os.path.join(exe_glossaries, DEFAULT_GLOSSARY))

    if not os.path.isdir(GLOSSARIES_DIR):
        os.makedirs(GLOSSARIES_DIR, exist_ok=True)
        # Copy glossary.json gốc vào thư mục glossaries/ nếu chưa có
        default_src = GLOSSARY_PATH
        default_dst = os.path.join(GLOSSARIES_DIR, DEFAULT_GLOSSARY)
        if os.path.exists(default_src) and not os.path.exists(default_dst):
            import shutil
            shutil.copy2(default_src, default_dst)
    
    files = []
    for f in sorted(os.listdir(GLOSSARIES_DIR)):
        if f.lower().endswith('.json'):
            files.append(f)
    
    # Đảm bảo file mặc định luôn đứng đầu
    if DEFAULT_GLOSSARY in files:
        files.remove(DEFAULT_GLOSSARY)
        files.insert(0, DEFAULT_GLOSSARY)
    
    return files

def get_glossary_path(filename: str) -> str:
    """Trả về đường dẫn đầy đủ của file glossary trong thư mục glossaries/."""
    return os.path.join(GLOSSARIES_DIR, filename)

def load_glossary(path: Optional[str] = None) -> dict:
    """Đọc glossary.json, trả về dict phẳng {term_cn: term_vn}."""
    if path is None:
        path = get_glossary_path(DEFAULT_GLOSSARY)
    flat = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for category in data.values():
            if isinstance(category, dict):
                flat.update(category)
        print(f"📖 Đã tải glossary: {len(flat)} thuật ngữ từ {os.path.basename(path)}")
    except FileNotFoundError:
        print(f"⚠️ Không tìm thấy file glossary tại: {path}")
    except Exception as e:
        print(f"⚠️ Lỗi khi đọc glossary: {e}")
    return flat

def find_relevant_terms(chinese_text: str, glossary: dict) -> str:
    """Scan text tiếng Trung, trả về chuỗi glossary chỉ chứa term xuất hiện trong text."""
    # Sắp xếp theo độ dài giảm dần để match term dài trước (ví dụ: 八阶大比 trước 大比)
    found = []
    for cn, vn in sorted(glossary.items(), key=lambda x: len(x[0]), reverse=True):
        if cn in chinese_text:
            found.append(f"{cn} → {vn}")
    return "\n".join(found) if found else ""

# Bảng biến thể phổ biến mà AI hay dịch sai
_COMMON_VARIANTS = {
    "tu vy": ["tu vi", "tu vĩ", "tu vỹ"],
    "vy sư": ["vi sư", "vĩ sư"],
    "muội muội": ["tiểu muội"],
    "đạo hữu": ["đạo hữu"],  # placeholder
    "lão phu": ["lão phu"],
    "cảnh giới": ["cảnh giới"],
}

def _build_variant_map(glossary: dict) -> dict:
    """Tạo bảng {variant_sai: term_đúng} từ glossary + common variants."""
    variant_map = {}
    for cn, vn in glossary.items():
        vn_lower = vn.lower()
        if vn_lower in _COMMON_VARIANTS:
            for wrong in _COMMON_VARIANTS[vn_lower]:
                if wrong.lower() != vn_lower:
                    variant_map[wrong] = vn
    # Thêm biến thể cố định
    variant_map["tu vi"] = "tu vy"
    variant_map["vi sư"] = "vy sư"
    variant_map["tiểu muội"] = "muội muội"
    return variant_map

def enforce_glossary(translated_text: str, original_text: str, glossary: dict) -> str:
    """Hậu xử lý: Ép dùng đúng thuật ngữ glossary trong bản dịch.
    
    1. Thay thế biến thể sai phổ biến (tu vi → tu vy, etc.)
    2. Với mỗi term Trung có trong text gốc, kiểm tra bản dịch có term đúng chưa.
    """
    result = translated_text
    
    # Bước 1: Sửa biến thể sai phổ biến
    variant_map = _build_variant_map(glossary)
    for wrong, correct in variant_map.items():
        # Case-insensitive replacement
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        result = pattern.sub(correct, result)
    
    # Bước 2: Ép thuật ngữ glossary - thay thế khi tìm thấy term CN trong gốc
    # Sắp xếp term dài trước để tránh replace nhầm substring
    for cn, vn in sorted(glossary.items(), key=lambda x: len(x[0]), reverse=True):
        if cn not in original_text:
            continue
        if vn in result:
            continue
        # Tìm biến thể sai: nếu term CN có trong gốc mà bản dịch không chứa vn,
        # thử tìm pinyin gần đúng. Ví dụ: "Vương Lâm" vs "Vương Lam"
        if len(vn) >= 2:
            # Tạo pattern linh hoạt: giữ con chữ đầu, cho phép sai dấu
            words = vn.split()
            if len(words) >= 2:
                # Thử tìm theo first_char + wildcard cho mỗi từ
                fuzzy_pattern = r'\b' + r'\s+'.join(
                    re.escape(w[0]) + r'[\wÀ-ỹ]+' for w in words
                ) + r'\b'
                match = re.search(fuzzy_pattern, result, re.IGNORECASE)
                if match:
                    result = result.replace(match.group(), vn)
    
    return result

# --- CÁC HÀM TIỆN ÍCH XỬ LÝ SRT ---

def parse_timestamp(ts_str: str) -> Optional[int]:
    """Chuyển timestamp SRT (HH:MM:SS,mmm) thành milliseconds."""
    m = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', ts_str.strip())
    if not m:
        return None
    h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return h * 3600000 + mi * 60000 + s * 1000 + ms

def ms_to_timestamp(ms: int) -> str:
    """Chuyển milliseconds thành timestamp SRT (HH:MM:SS,mmm)."""
    h = ms // 3600000
    ms %= 3600000
    mi = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"

def text_similarity(a: str, b: str) -> float:
    """Tính độ tương đồng giữa 2 chuỗi text (0.0 - 1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def is_meaningful_short_text(text: str) -> bool:
    """Kiểm tra text ngắn (1-2 ký tự) có ý nghĩa hay không.
    
    Trả về True nếu text có nghĩa (giữ lại), False nếu là rác (loại bỏ).
    Các ký tự Trung có nghĩa: câu cảm thán, đại từ, động từ phổ biến, etc.
    """
    text = text.strip()
    if not text:
        return False
    
    # Danh sách ký tự/từ Trung 1-2 chữ có nghĩa (giữ lại)
    MEANINGFUL_CHARS = set(
        # Câu cảm thán & trợ từ
        '啊嗯哦哈嘿嗨呀吧呢吗哇噢唉哎嘛喂呵嘘哼'
        # Đại từ
        '你我他她它们谁'
        # Động từ phổ biến
        '是好走来去看说听想要做死活打杀飞跑跳吃喝'
        # Tính từ
        '大小多少高低快慢强弱'
        # Từ phổ biến
        '不对错有无可以'
        # Số
        '一二三四五六七八九十百千万'
    )
    
    MEANINGFUL_WORDS_2CHAR = {
        '什么', '为什', '怎么', '这里', '那里', '哪里', '这个', '那个',
        '不是', '不要', '不行', '不对', '可以', '没有', '知道', '当然',  
        '前辈', '师兄', '师姐', '师父', '师傅', '道友', '少侠', '大人',
        '小心', '快走', '住手', '放手', '闭嘴', '滚开', '混蛋', '废物',
        '哈哈', '嘿嘿', '呵呵', '嗯嗯', '啊啊',
    }
    
    # 1 ký tự: kiểm tra trong danh sách
    if len(text) == 1:
        return text in MEANINGFUL_CHARS
    
    # 2 ký tự: kiểm tra từ có nghĩa HOẶC cả 2 ký tự đều có nghĩa
    if len(text) == 2:
        if text in MEANINGFUL_WORDS_2CHAR:
            return True
        # Nếu cả 2 ký tự đều là ký tự Trung có nghĩa
        if all(c in MEANINGFUL_CHARS for c in text):
            return True
        # Kiểm tra có phải ký tự Trung hợp lệ không (Unicode CJK range)
        if all('\u4e00' <= c <= '\u9fff' for c in text):
            return True  # Hầu hết từ 2 ký tự Trung đều có nghĩa
    
    return False

def deduplicate_srt_blocks(blocks: List[str], similarity_threshold: float = 0.92, 
                           max_gap_ms: int = 800) -> Tuple[List[str], int]:
    """
    Gộp các block SRT liên tiếp có text trùng lặp hoặc lỗi OCR.
    Chỉ gộp khi:
    - Block có duration < 150ms (OCR artifact) → loại bỏ
    - Block 1-2 ký tự vô nghĩa → loại bỏ
    - Text gần giống (similarity >= 0.95) → gộp (sai 1-2 ký tự do OCR)
    - Text là substring chặt (>= 70% độ dài, >= 3 ký tự) → gộp
    - Gộp timestamp: start của block đầu, end của block cuối
    - Trả về (danh sách block đã gộp, số block đã loại bỏ)
    """
    if not blocks:
        return blocks, 0
    
    # === PHASE 1: Loại bỏ block có duration quá ngắn (< 150ms) = OCR artifact ===
    phase1 = []
    short_removed = 0
    for block in blocks:
        idx, ts, text_lines = parse_block(block)
        if not idx or not ts:
            phase1.append(block)
            continue
        
        ts_match = re.match(r'(.+?)\s*-->\s*(.+)', ts)
        if not ts_match:
            phase1.append(block)
            continue
        
        start_ms = parse_timestamp(ts_match.group(1))
        end_ms = parse_timestamp(ts_match.group(2))
        
        if start_ms is None or end_ms is None:
            phase1.append(block)
            continue
        
        duration = end_ms - start_ms
        if duration < 150:
            # Block quá ngắn — OCR artifact, loại bỏ
            short_removed += 1
            continue
        
        phase1.append(block)
    
    # === PHASE 2: Loại bỏ/gộp block 1-2 ký tự vô nghĩa ===
    phase2 = []
    noise_removed = 0
    for block in phase1:
        idx, ts, text_lines = parse_block(block)
        if not idx or not ts:
            phase2.append(block)
            continue
        
        text = ' '.join(l.strip() for l in text_lines).strip()
        
        # Kiểm tra text chỉ chứa 1-2 ký tự
        # Loại bỏ whitespace để đếm ký tự thực
        clean_text = re.sub(r'\s+', '', text)
        if 0 < len(clean_text) <= 2:
            if is_meaningful_short_text(clean_text):
                # Ký tự có nghĩa → giữ lại
                phase2.append(block)
            else:
                # Ký tự rác → loại bỏ
                noise_removed += 1
        else:
            phase2.append(block)
    
    # === PHASE 3: Gộp text tương tự + substring/fragment detection ===
    merged = []
    i = 0
    similarity_removed = 0
    
    while i < len(phase2):
        idx, ts, text_lines = parse_block(phase2[i])
        if not idx or not ts:
            merged.append(phase2[i])
            i += 1
            continue
        
        current_text = ' '.join(l.strip() for l in text_lines)
        ts_match = re.match(r'(.+?)\s*-->\s*(.+)', ts)
        if not ts_match:
            merged.append(phase2[i])
            i += 1
            continue
        
        group_start_ms = parse_timestamp(ts_match.group(1))
        group_end_ms = parse_timestamp(ts_match.group(2))
        
        if group_start_ms is None or group_end_ms is None:
            merged.append(phase2[i])
            i += 1
            continue
        
        best_text = current_text  # Giữ text dài nhất trong nhóm
        best_text_lines = text_lines
        
        # Tìm các block tiếp theo giống nhau hoặc là fragment
        j = i + 1
        while j < len(phase2):
            next_idx, next_ts, next_text_lines = parse_block(phase2[j])
            if not next_idx or not next_ts:
                break
            
            next_text = ' '.join(l.strip() for l in next_text_lines)
            
            # Kiểm tra khoảng cách thời gian trước
            next_ts_match = re.match(r'(.+?)\s*-->\s*(.+)', next_ts)
            if not next_ts_match:
                break
            
            next_start_ms = parse_timestamp(next_ts_match.group(1))
            next_end_ms = parse_timestamp(next_ts_match.group(2))
            
            if next_start_ms is None or next_end_ms is None:
                break
            
            gap = next_start_ms - group_end_ms
            if gap > max_gap_ms:
                break
            
            # Kiểm tra similarity HOẶC substring (chặt chẽ)
            sim = text_similarity(best_text, next_text)
            
            # Substring check chặt: text ngắn phải chiếm >= 70% text dài
            # và phải có >= 3 ký tự thực (tránh gộp nhầm text ngắn)
            clean_best = re.sub(r'\s+', '', best_text)
            clean_next = re.sub(r'\s+', '', next_text)
            is_strict_substring = False
            if len(clean_next) >= 3 and len(clean_best) >= 3:
                if (clean_next in clean_best) or (clean_best in clean_next):
                    shorter = min(len(clean_next), len(clean_best))
                    longer = max(len(clean_next), len(clean_best))
                    is_strict_substring = (shorter / longer) >= 0.7
            
            if sim >= similarity_threshold or is_strict_substring:
                # Gộp: mở rộng end timestamp, giữ text dài nhất
                group_end_ms = next_end_ms
                if len(next_text) > len(best_text):
                    best_text = next_text
                    best_text_lines = next_text_lines
                similarity_removed += 1
                j += 1
            else:
                break
        
        # Tạo block gộp với timestamp mới và text dài nhất
        new_ts = f"{ms_to_timestamp(group_start_ms)} --> {ms_to_timestamp(group_end_ms)}"
        new_block = "\n".join([idx, new_ts] + best_text_lines)
        merged.append(new_block)
        i = j
    
    # Đánh lại số thứ tự
    renumbered = []
    counter = 1
    for block in merged:
        idx, ts, text_lines = parse_block(block)
        if idx and ts:
            renumbered.append("\n".join([str(counter), ts] + text_lines))
            counter += 1
        else:
            renumbered.append(block)
    
    total_removed = short_removed + noise_removed + similarity_removed
    return renumbered, total_removed

def clean_srt_blocks(blocks: List[str]) -> Tuple[List[str], int]:
    """
    Tiền xử lý SRT blocks trước khi gửi AI:
    - Loại bỏ block rỗng hoặc chỉ whitespace
    - Loại bỏ block chỉ chứa ký tự đặc biệt/số vô nghĩa
    - Gộp block liên tiếp text giống hệt (exact match)
    - Đánh lại số thứ tự
    Trả về (blocks đã clean, số block đã loại)
    """
    if not blocks:
        return blocks, 0
    
    cleaned = []
    removed = 0
    
    for block in blocks:
        idx, ts, text_lines = parse_block(block)
        if not idx or not ts:
            continue  # Block không hợp lệ
        
        text = ' '.join(l.strip() for l in text_lines).strip()
        
        # Loại bỏ block rỗng
        if not text:
            removed += 1
            continue
        
        # Loại bỏ block chỉ chứa ký tự đặc biệt/whitespace/số
        clean_text = re.sub(r'[\s\d.,!?;:\-_=+\[\](){}<>/*\\|@#$%^&~`\'"]+', '', text)
        if not clean_text:
            removed += 1
            continue
        
        cleaned.append(block)
    
    # Gộp block liên tiếp text giống hệt (exact match)
    if len(cleaned) > 1:
        deduped = [cleaned[0]]
        exact_removed = 0
        for i in range(1, len(cleaned)):
            prev_idx, prev_ts, prev_text_lines = parse_block(deduped[-1])
            curr_idx, curr_ts, curr_text_lines = parse_block(cleaned[i])
            
            if prev_text_lines and curr_text_lines:
                prev_text = ' '.join(l.strip() for l in prev_text_lines)
                curr_text = ' '.join(l.strip() for l in curr_text_lines)
                
                if prev_text.strip() == curr_text.strip() and prev_ts and curr_ts:
                    # Text giống hệt → gộp timestamp
                    prev_ts_match = re.match(r'(.+?)\s*-->\s*(.+)', prev_ts)
                    curr_ts_match = re.match(r'(.+?)\s*-->\s*(.+)', curr_ts)
                    
                    if prev_ts_match and curr_ts_match:
                        start_ms = parse_timestamp(prev_ts_match.group(1))
                        end_ms = parse_timestamp(curr_ts_match.group(2))
                        
                        if start_ms is not None and end_ms is not None:
                            new_ts = f"{ms_to_timestamp(start_ms)} --> {ms_to_timestamp(end_ms)}"
                            deduped[-1] = "\n".join([prev_idx, new_ts] + prev_text_lines)
                            exact_removed += 1
                            continue
            
            deduped.append(cleaned[i])
        
        cleaned = deduped
        removed += exact_removed
    
    # Đánh lại số thứ tự
    renumbered = []
    counter = 1
    for block in cleaned:
        idx, ts, text_lines = parse_block(block)
        if idx and ts:
            renumbered.append("\n".join([str(counter), ts] + text_lines))
            counter += 1
        else:
            renumbered.append(block)
    
    return renumbered, removed
def merge_ellipsis_blocks(blocks: List[str]) -> Tuple[List[str], int]:
    """
    Gộp các block có text là '...' hoặc '…' vào block trước đó.
    Mở rộng end timestamp của block trước, xóa block '...'.
    Đánh lại số thứ tự.
    Trả về (blocks đã gộp, số block đã xóa).
    """
    if not blocks:
        return blocks, 0
    
    merged = []
    removed = 0
    
    for block in blocks:
        idx, ts, text_lines = parse_block(block)
        if not idx or not ts:
            merged.append(block)
            continue
        
        # Kiểm tra text chỉ là '...' hoặc '…' (có thể có khoảng trắng)
        text = ' '.join(l.strip() for l in text_lines).strip()
        is_ellipsis = text in ('...', '…', '..', '….', '......')
        
        if is_ellipsis and merged:
            # Tìm block trước đó để gộp timestamp
            prev_idx, prev_ts, prev_text_lines = parse_block(merged[-1])
            if prev_idx and prev_ts:
                # Lấy end_time từ block hiện tại
                curr_ts_match = re.match(r'(.+?)\s*-->\s*(.+)', ts)
                prev_ts_match = re.match(r'(.+?)\s*-->\s*(.+)', prev_ts)
                
                if curr_ts_match and prev_ts_match:
                    prev_start_ms = parse_timestamp(prev_ts_match.group(1))
                    curr_end_ms = parse_timestamp(curr_ts_match.group(2))
                    
                    if prev_start_ms is not None and curr_end_ms is not None:
                        # Mở rộng end_time của block trước
                        new_ts = f"{ms_to_timestamp(prev_start_ms)} --> {ms_to_timestamp(curr_end_ms)}"
                        merged[-1] = "\n".join([prev_idx, new_ts] + prev_text_lines)
                        removed += 1
                        continue
        
        merged.append(block)
    
    # Đánh lại số thứ tự
    renumbered = []
    counter = 1
    for block in merged:
        idx, ts, text_lines = parse_block(block)
        if idx and ts:
            renumbered.append("\n".join([str(counter), ts] + text_lines))
            counter += 1
        else:
            renumbered.append(block)
    
    return renumbered, removed

def split_srt_blocks(srt_text: str) -> List[str]:
    """Tách chuỗi SRT thành các khối (block) riêng lẻ."""
    # Loại bỏ BOM (Byte Order Mark) ở đầu file nếu có
    srt_text = srt_text.lstrip('\ufeff')
    return [b.strip() for b in re.split(r"\n\s*\n", srt_text.strip()) if b.strip()]

def join_srt_blocks(blocks: List[str]) -> str:
    """Nối các khối SRT lại thành một chuỗi hoàn chỉnh."""
    return "\n\n".join(blocks) + "\n"

def parse_block(block: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    """Phân tích một khối SRT để lấy số thứ tự, thời gian và nội dung."""
    lines = block.splitlines()
    if len(lines) >= 2 and IDX_RE.match(lines[0]) and TS_RE.match(lines[1]):
        return lines[0], lines[1], lines[2:]
    return None, None, [block] # Trả về nguyên khối nếu định dạng không chuẩn

def sanitize_output(text: str) -> str:
    """Dọn dẹp text trả về từ API."""
    text = text.strip()
    if (text.startswith('"') and text.endswith('"')) or \
       (text.startswith('“') and text.endswith('”')):
        return text[1:-1].strip()
    return text

# Regex để phát hiện timestamp SRT bị lẫn vào text dịch
_SRT_ARTIFACT_RE = re.compile(
    r'^\s*\d+\s+\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s*'
)

def sanitize_translated_line(line: str) -> str:
    """Dọn dẹp một dòng text đã dịch, loại bỏ SRT artifacts."""
    # Loại bỏ dạng: "76 00:02:13,199 --> 00:02:14,599 text dịch"
    cleaned = _SRT_ARTIFACT_RE.sub('', line)
    # Loại bỏ thẻ cite
    cleaned = re.sub(r'</?cite[^>]*>', '', cleaned)
    # Loại bỏ dấu ngoặc đơn bao quanh toàn bộ
    cleaned = cleaned.strip()
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def force_line_count(translated_text: str, original_line_count: int) -> List[str]:
    """Điều chỉnh số dòng của bản dịch cho khớp với số dòng của bản gốc."""
    lines = [line.strip() for line in translated_text.splitlines() if line is not None]
    
    # Nếu số dòng bằng nhau, trả về luôn
    if len(lines) == original_line_count:
        return lines
    
    # Nếu ít dòng hơn, tách dòng dài nhất ra
    if len(lines) < original_line_count:
        full_text = " ".join(lines)
        # Tách câu thông minh hơn dựa vào dấu câu
        parts = re.split(r'(?<=[.!?…,;])\s+', full_text)
        parts = [p.strip() for p in parts if p.strip()]

        while len(parts) < original_line_count:
            if not parts: parts = [""]
            # Tìm đoạn dài nhất để tách
            longest_idx = max(range(len(parts)), key=lambda i: len(parts[i]))
            chunk = parts.pop(longest_idx)
            mid_point = len(chunk) // 2
            # Tìm khoảng trắng gần điểm giữa nhất để tách
            split_pos = chunk.rfind(' ', 0, mid_point) + 1 or mid_point
            parts.insert(longest_idx, chunk[:split_pos].strip())
            parts.insert(longest_idx + 1, chunk[split_pos:].strip())
        return parts[:original_line_count]

    # Nếu nhiều dòng hơn, gộp dòng cuối lên
    while len(lines) > original_line_count:
        last_line = lines.pop()
        lines[-1] = f"{lines[-1]} {last_line}".strip()
    return lines

def build_batch_prompt(compact_text: str, prev_context: str, glossary_hint: str = "", tag_characters: bool = False, character_names_hint: str = "") -> str:
    """Xây dựng prompt COMPACT: chỉ gửi [idx]|text, tiết kiệm ~40% token."""
    parts = []
    if glossary_hint:
        parts.append(
            "【THUẬT NGỮ BẮT BUỘC】\n"
            f"{glossary_hint}"
        )
    if prev_context:
        parts.append(f"【NGỮ CẢNH TRƯỚC - KHÔNG dịch lại】\n{prev_context}")
    parts.append(f"【CẦN DỊCH】\n{compact_text}")
    
    if tag_characters:
        char_list_section = ""
        if character_names_hint:
            char_list_section = (
                "【DANH SÁCH NHÂN VẬT ĐÃ BIẾT】\n"
                f"{character_names_hint}\n"
                "→ Ưu tiên dùng tên trong danh sách trên. Nếu NV mới chưa có → tự đặt tên Việt.\n\n"
            )
        parts.append(
            "→ Trả về [số]|{Tên nhân vật} text tiếng Việt. GIỮ NGUYÊN [số]. CHỈ trả kết quả.\n"
            "【BẮT BUỘC - NHẬN DIỆN NHÂN VẬT NÓI】\n"
            "Phân tích VĂN BẢN GỐC TIẾNG TRUNG để xác định ai đang nói, rồi gắn {Tên NV tiếng Việt} trước bản dịch.\n\n"
            f"{char_list_section}"
            "【QUY TẮC NHẬN DIỆN — XEM KỸ VĂN BẢN GỐC】\n"
            "1. TÌM DẤU HIỆU TRỰC TIẾP trong text gốc tiếng Trung:\n"
            "   - X道/X说/X喊/X叫/X问/X笑道/X冷声道 → X đang nói\n"
            "   - 「...」或 \"...\" (dấu ngoặc kép) → lời thoại trực tiếp\n"
            "   - Ngôi thứ nhất 我/吾/本座/老夫/本尊 → người nói tự xưng\n"
            "   → Gắn {Tên NV}. VD: [5]|{Vương Lâm} Ta sẽ không tha cho ngươi!\n\n"
            "2. KHÔNG CÓ DẤU HIỆU AI NÓI:\n"
            "   a) Nếu câu TIẾP NỐI lời thoại trước (cùng chủ ngữ, cùng ngữ cảnh) → giữ {Tên NV} trước đó\n"
            "   b) Nếu là mô tả/旁白 (miêu tả cảnh, hành động, suy nghĩ bên ngoài) → {旁白}\n"
            "   c) Nếu là mô tả suy nghĩ nội tâm của NV cụ thể (他心中想到/他暗道) → {Tên NV đó}\n\n"
            "3. HỘI THOẠI NHIỀU NGƯỜI:\n"
            "   - Đọc ngữ cảnh: A hỏi → B đáp → A hỏi lại → phân biệt rõ lượt nói\n"
            "   - Xưng hô: 义父=con nói với cha nuôi, 孩儿=con tự xưng, 你=nói với đối phương\n\n"
            "4. TÊN NHẤT QUÁN: LUÔN dùng tên tiếng Việt, không lẫn lộn CN/VN.\n"
            "5. KHI KHÔNG CHẮC → dùng {旁白}, KHÔNG đoán bừa.\n\n"
            "【VÍ DỤ ĐÚNG】\n"
            "Gốc: 王林道 可惜你杀戮不够 → [1]|{Vương Lâm} Đáng tiếc sát lục của ngươi chưa đủ.\n"
            "Gốc: 否则已可立刻打开此门 → [2]|{Vương Lâm} Bằng không, đã có thể lập tức mở cánh cửa này.\n"
            "Gốc: 计都犹豫了一下 → [3]|{旁白} Kế Đô do dự một chút.\n"
            "Gốc: 孩儿不敢有丝毫异心 → [4]|{Kế Đô} Hài nhi không dám có chút dị tâm."
        )
    else:
        parts.append(
            "→ Trả về [số]|text tiếng Việt. GIỮ NGUYÊN [số]. CHỈ trả kết quả."
        )
    return "\n\n".join(parts)

# ================== GRAMMAR PROMPT (SỬA TIẾNG TRUNG) ==================
GRAMMAR_SYSTEM_PROMPT = (
    "你是中文字幕校对专家。修正字幕中的错别字、语法错误和OCR识别错误。\n\n"
    "【输入/输出格式】\n"
    "输入: [编号]|文本\n"
    "输出: [编号]|修正后的文本（格式完全相同）\n\n"
    "【修正规则】\n"
    "• 修正错别字和语法错误\n"
    "• 修正OCR识别错误，常见混淆字包括：\n"
    "  己→已, 哪→那, 鬼→魂, 人→入, 太→大, 未→末, \n"
    "  干→于, 巳→已, 白→自, 曰→日, 壁→璧, 侯→候, \n"
    "  得→的, 地→的, 真→镇, 刀→力, 刃→刀\n"
    "• 修正标点符号错误\n"
    "• 如果相邻几行是同一句话被拆开的片段，合并成完整通顺的句子\n"
    "• 删除明显的OCR垃圾文本（乱码、无意义符号）\n\n"
    "【不要做的事】\n"
    "• 不要改变原意\n"
    "• 不要添加注释或解释\n"
    "• 保留人名、术语、专有名词\n\n"
    "【重要】\n"
    "• 必须返回所有编号，包括最后一行\n"
    "• 如果某行不需要修正，原样返回\n"
    "• 只返回 [编号]|文本 格式的列表，不要有其他内容"
)

# ================== WORKER CHO TÁC VỤ SỬA NGỮ PHÁP ==================
class GrammarWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    update_progress_bar = pyqtSignal(int)

    def __init__(self, input_path: str, api_provider: str, selected_model: str):
        super().__init__()
        self.input_path = input_path
        self.api_provider = api_provider
        self.selected_model = selected_model
        self.is_running = True

    def run(self):
        try:
            self.progress.emit(f"✏️ Bắt đầu sửa ngữ pháp...")
            self.progress.emit(f"Đang tải API key cho {self.api_provider.upper()}...")
            client = self._initialize_client()
            self.progress.emit(f"✅ Sử dụng model: {self.selected_model}")

            with open(self.input_path, "r", encoding="utf-8") as f:
                content = f.read()

            blocks = split_srt_blocks(content)
            original_count = len(blocks)
            
            # ====== BƯỚC 0: Tiền xử lý — loại block rỗng/rác (0 token) ======
            self.progress.emit(f"🧹 Tiền xử lý {original_count} block: loại block rỗng/rác...")
            blocks, cleaned = clean_srt_blocks(blocks)
            if cleaned > 0:
                self.progress.emit(f"  ✅ Loại {cleaned} block rỗng/rác → còn {len(blocks)} block")
            
            # ====== BƯỚC 1: Gộp subtitle trùng lặp (0 token, xử lý local) ======
            self.progress.emit(f"🔍 Đang quét {len(blocks)} block tìm subtitle trùng lặp...")
            blocks, removed = deduplicate_srt_blocks(blocks)
            total_blocks = len(blocks)
            total_local_removed = cleaned + removed
            
            if removed > 0:
                self.progress.emit(f"✅ Đã gộp {removed} subtitle trùng/noise → còn {total_blocks} block")
            else:
                self.progress.emit(f"✅ Không có subtitle trùng lặp.")
            
            if total_local_removed > 0:
                self.progress.emit(f"📊 Tổng loại/gộp local: {total_local_removed} block (0 token!)")
            
            # ====== BƯỚC 2: Parse blocks và sửa ngữ pháp qua AI ======
            # Parse tất cả block ra: giữ idx, ts, text riêng
            parsed_blocks = []
            for b in blocks:
                idx, ts, text_lines = parse_block(b)
                parsed_blocks.append((idx, ts, text_lines))
            
            self.progress.emit(f"📦 Sửa ngữ pháp {total_blocks} block (tối ưu token: chỉ gửi text)...")

            final_blocks = [""] * total_blocks
            # Dùng batch lớn hơn vì chỉ gửi text, tiết kiệm token
            GRAMMAR_BATCH = BATCH_SIZE * 2  
            total_batches = (total_blocks + GRAMMAR_BATCH - 1) // GRAMMAR_BATCH
            api_calls = 0
            total_input_tokens = 0
            all_changes = []  # Lưu tất cả thay đổi để hiển thị cuối

            for batch_idx in range(0, total_blocks, GRAMMAR_BATCH):
                if not self.is_running:
                    self.progress.emit("Tác vụ đã bị hủy.")
                    return

                batch_start = batch_idx
                batch_end = min(batch_idx + GRAMMAR_BATCH, total_blocks)
                batch_num = batch_idx // GRAMMAR_BATCH + 1

                self.progress.emit(f"\n✏️ Batch {batch_num}/{total_batches} (block {batch_start+1}→{batch_end})...")

                # [TỐI ƯU TOKEN] Chỉ gửi text kèm index, KHÔNG gửi timestamp
                text_lines_for_api = []
                for i in range(batch_start, batch_end):
                    idx, ts, text_lines = parsed_blocks[i]
                    if idx and text_lines:
                        text = ' '.join(l.strip() for l in text_lines)
                        text_lines_for_api.append(f"[{idx}]|{text}")
                
                if not text_lines_for_api:
                    for k in range(batch_start, batch_end):
                        final_blocks[k] = blocks[k]
                    continue
                
                compact_text = "\n".join(text_lines_for_api)
                token_est = len(compact_text) // 4
                total_input_tokens += token_est
                self.progress.emit(f"  📊 ~{token_est} tokens (chỉ text, tiết kiệm ~40%)")
                
                user_prompt = f"{compact_text}"

                try:
                    if self.api_provider in ("openai", "grok"):
                        raw_response = call_openai_api(client, self.selected_model, GRAMMAR_SYSTEM_PROMPT, user_prompt)
                    else:
                        raw_response = call_gemini_api(client, self.selected_model, GRAMMAR_SYSTEM_PROMPT, user_prompt)
                    api_calls += 1
                except Exception as e:
                    self.progress.emit(f"  ❌ Batch {batch_num} lỗi API: {e}")
                    raw_response = ""

                if not raw_response:
                    self.progress.emit(f"  ⚠️ Batch {batch_num} không có kết quả, giữ nguyên")
                    for k in range(batch_start, batch_end):
                        final_blocks[k] = blocks[k]
                else:
                    # Parse response dạng [idx]|text
                    response = sanitize_output(raw_response)
                    response = re.sub(r'^```[a-zA-Z]*\n?', '', response)
                    response = re.sub(r'\n?```$', '', response)
                    response = response.strip()
                    
                    # Parse từng dòng response (hỗ trợ nhiều format)
                    fixed_map = {}  # {idx_str: fixed_text}
                    for line in response.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        # Match format [idx]|text
                        m = re.match(r'\[(\d+)\]\|(.+)', line)
                        if m:
                            fixed_map[m.group(1)] = m.group(2).strip()
                        else:
                            # Fallback: format idx|text (không có dấu [])
                            m2 = re.match(r'(\d+)\|(.+)', line)
                            if m2:
                                fixed_map[m2.group(1)] = m2.group(2).strip()
                    
                    self.progress.emit(f"  📝 Nhận {len(fixed_map)}/{batch_end - batch_start} dòng đã sửa")
                    
                    # Ghép lại SRT với timestamp gốc
                    for i in range(batch_start, batch_end):
                        idx, ts, orig_text = parsed_blocks[i]
                        if idx and idx in fixed_map:
                            orig_joined = ' '.join(l.strip() for l in orig_text)
                            fixed_text = fixed_map[idx]
                            
                            # So sánh và log thay đổi
                            if orig_joined.strip() != fixed_text.strip():
                                self.progress.emit(f"  🔄 [{idx}] {orig_joined}")
                                self.progress.emit(f"     → {fixed_text}")
                                all_changes.append((idx, orig_joined, fixed_text))
                            
                            # Giữ nguyên số dòng text gốc
                            orig_line_count = len(orig_text)
                            fixed_lines = force_line_count(fixed_text, orig_line_count)
                            final_blocks[i] = "\n".join([idx, ts] + fixed_lines)
                        else:
                            final_blocks[i] = blocks[i]

                    self.progress.emit(f"  ✅ Batch {batch_num} hoàn tất")

                progress_pct = int(batch_end * 100 / total_blocks)
                self.update_progress_bar.emit(progress_pct)

            # Đảm bảo không có block rỗng
            for k in range(total_blocks):
                if not final_blocks[k]:
                    final_blocks[k] = blocks[k]

            # ====== BƯỚC 3: Retry cho blocks bị sót ======
            missed_indices = []
            for k in range(total_blocks):
                idx, ts, text_lines = parsed_blocks[k]
                if idx and final_blocks[k] == blocks[k]:
                    # Block vẫn giữ nguyên = API có thể đã skip
                    missed_indices.append(k)
            
            if missed_indices and self.is_running and len(missed_indices) <= total_blocks * 0.3:
                self.progress.emit(f"\n🔄 Retry {len(missed_indices)} block bị API bỏ sót...")
                
                retry_lines = []
                for k in missed_indices:
                    idx, ts, text_lines = parsed_blocks[k]
                    if idx and text_lines:
                        text = ' '.join(l.strip() for l in text_lines)
                        retry_lines.append(f"[{idx}]|{text}")
                
                if retry_lines:
                    retry_prompt = "\n".join(retry_lines)
                    try:
                        if self.api_provider in ("openai", "grok"):
                            retry_response = call_openai_api(client, self.selected_model, GRAMMAR_SYSTEM_PROMPT, retry_prompt)
                        else:
                            retry_response = call_gemini_api(client, self.selected_model, GRAMMAR_SYSTEM_PROMPT, retry_prompt)
                        api_calls += 1
                        
                        if retry_response:
                            retry_response = sanitize_output(retry_response)
                            retry_response = re.sub(r'^```[a-zA-Z]*\n?', '', retry_response)
                            retry_response = re.sub(r'\n?```$', '', retry_response)
                            retry_response = retry_response.strip()
                            
                            retry_fixed = 0
                            for line in retry_response.split('\n'):
                                line = line.strip()
                                if not line:
                                    continue
                                m = re.match(r'\[(\d+)\]\|(.+)', line)
                                if not m:
                                    m = re.match(r'(\d+)\|(.+)', line)
                                if m:
                                    r_idx = m.group(1)
                                    r_text = m.group(2).strip()
                                    # Tìm vị trí trong parsed_blocks
                                    for k in missed_indices:
                                        p_idx, p_ts, p_text = parsed_blocks[k]
                                        if p_idx == r_idx:
                                            orig_joined = ' '.join(l.strip() for l in p_text)
                                            if orig_joined.strip() != r_text.strip():
                                                self.progress.emit(f"  🔄 [{r_idx}] {orig_joined}")
                                                self.progress.emit(f"     → {r_text}")
                                                all_changes.append((r_idx, orig_joined, r_text))
                                            orig_line_count = len(p_text)
                                            fixed_lines = force_line_count(r_text, orig_line_count)
                                            final_blocks[k] = "\n".join([r_idx, p_ts] + fixed_lines)
                                            retry_fixed += 1
                                            break
                            
                            self.progress.emit(f"  ✅ Retry hoàn tất: sửa thêm {retry_fixed} block")
                    except Exception as e:
                        self.progress.emit(f"  ⚠️ Retry lỗi: {e}")

            sep_double = "═" * 40
            sep_single = "━" * 40
            self.progress.emit(f"\n{sep_double}")
            self.progress.emit(f"✏️ Đã sửa ngữ pháp {total_blocks} block trong {api_calls} lần gọi API.")
            self.progress.emit(f"💰 Tổng ~{total_input_tokens} input tokens (tiết kiệm ~40% so với gửi full SRT)")
            
            # ====== BƯỚC 4: Tổng kết các thay đổi ======
            if all_changes:
                self.progress.emit(f"\n{sep_single}")
                self.progress.emit(f"📋 TỔNG KẾT: {len(all_changes)} chỗ đã sửa:")
                self.progress.emit(sep_single)
                for idx, orig, fixed in all_changes:
                    self.progress.emit(f"  [{idx}] ❌ {orig}")
                    self.progress.emit(f"       ✅ {fixed}")
            else:
                self.progress.emit("\n✅ Không phát hiện lỗi nào cần sửa.")
            
            if total_local_removed > 0:
                self.progress.emit(f"\n🔗 Tiền xử lý: loại/gộp {total_local_removed} block (clean: {cleaned}, dedup: {removed})")
            
            self.progress.emit(sep_double)

            # Ghi file — ghi đè file gốc
            with open(self.input_path, "w", encoding="utf-8") as f:
                f.write(join_srt_blocks(final_blocks))
            self.finished.emit(self.input_path)

        except Exception as e:
            self.error.emit(f"Lỗi nghiêm trọng: {e.__class__.__name__}: {e}")

    def _initialize_client(self):
        load_dotenv(override=True)
        if self.api_provider in ("openai", "grok"):
            dotenv_path = find_dotenv()
            if not dotenv_path:
                dotenv_path = os.path.join(os.getcwd(), '.env')
            
            env_key_name = 'XAI_API_KEY' if self.api_provider == 'grok' else 'OPENAI_API_KEY'
            api_key = ""
            if os.path.exists(dotenv_path):
                with open(dotenv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith(f'{env_key_name}='):
                            api_key = line.strip().split('=', 1)[1].strip()
                            break
            if not api_key:
                api_key = os.getenv(env_key_name, "").strip()
            if not api_key:
                raise ValueError(f"Chưa cung cấp {env_key_name} trong file .env")
            client = HTTPXOpenAIClient(api_key=api_key)
            if self.api_provider == 'grok':
                client.base_url = "https://api.x.ai/v1"
            return client
        else:
            dotenv_path = find_dotenv()
            if not dotenv_path:
                dotenv_path = os.path.join(os.getcwd(), '.env')
            api_key = ""
            if os.path.exists(dotenv_path):
                with open(dotenv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('GOOGLE_API_KEY='):
                            api_key = line.strip().split('=', 1)[1].strip()
                            break
            if not api_key:
                api_key = os.getenv("GOOGLE_API_KEY", "").strip()
            if not api_key:
                raise ValueError("Chưa cung cấp GOOGLE_API_KEY")
            genai.configure(api_key=api_key)
            return genai

# ================== WORKER CHO TÁC VỤ DỊCH (ĐÃ ĐƠN GIẢN HÓA) ==================
class TranslationWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    update_progress_bar = pyqtSignal(int)
    batch_info = pyqtSignal(str)  # Chi tiết batch: "Đang dịch batch 5/20 (25%)"

    def __init__(self, input_path: str, api_provider: str, selected_model: str, system_prompt: str, glossary_path: str = None, tag_characters: bool = False, video_path: str = None, video_quality: str = "original"):
        super().__init__()
        self.input_path = input_path
        self.api_provider = api_provider
        self.selected_model = selected_model
        self.system_prompt = system_prompt
        self.is_running = True
        self.glossary_path = glossary_path
        self.glossary = {}
        self.tag_characters = tag_characters
        self.video_path = video_path  # Video file for video-assisted character tagging
        self.video_quality = video_quality  # 'original', '720p', '480p'
        self._gemini_keys = []
        self._gemini_key_idx = 0

    def run(self):
        try:
            self._start_time = time.time()  # ⏱ Bắt đầu đếm thời gian
            self._total_blocks = 0
            
            self.progress.emit(f"Đang tải API key cho {self.api_provider.upper()}...")
            client = self._initialize_client()
            self.progress.emit(f"✅ Sử dụng model: {self.selected_model}")

            with open(self.input_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Tải glossary từ file được chọn (0 token, 0 API call)
            self.glossary = load_glossary(self.glossary_path)
            glossary_name = os.path.basename(self.glossary_path) if self.glossary_path else DEFAULT_GLOSSARY
            self.progress.emit(f"📖 Đã tải {len(self.glossary)} thuật ngữ từ {glossary_name} (không tốn API call)")
            
            self.batch_info.emit("⏳ Đang chuẩn bị dịch...")
            
            # Dịch theo từng cụm với smart glossary injection (1-pass: dịch + tag NV)
            translated_blocks = self._translate_file_by_chunks(client, content, self.system_prompt)
            if not self.is_running:
                return

            # ⏱ Tính thời gian
            elapsed = time.time() - self._start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            time_str = f"{mins}p{secs:02d}s" if mins > 0 else f"{secs}s"
            self.batch_info.emit(f"✅ Dịch xong {self._total_blocks} block trong {time_str}")

            # ===== VIDEO-ASSISTED: Upload video lên Gemini để tag NV chính xác =====
            if self.tag_characters and self.video_path and os.path.isfile(self.video_path) and self.is_running:
                self.progress.emit(f"\n{'_' * 40}")
                self.progress.emit(f"🎬 VIDEO-ASSISTED: Upload video lên Gemini để tag NV chính xác...")
                translated_blocks = self._tag_with_video(client, translated_blocks)
                if not self.is_running:
                    return
                elapsed2 = time.time() - self._start_time
                mins2 = int(elapsed2 // 60)
                secs2 = int(elapsed2 % 60)
                time_str2 = f"{mins2}p{secs2:02d}s" if mins2 > 0 else f"{secs2}s"
                self.batch_info.emit(f"✅ Dịch + Video Tag NV xong trong {time_str2}")

            # Hoàn tất, ghi file
            base, _ = os.path.splitext(self.input_path)
            output_path = f"{base}_translated_{self.api_provider}.srt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(join_srt_blocks(translated_blocks))
            self.finished.emit(output_path)

        except Exception as e:
            self.error.emit(f"Lỗi nghiêm trọng: {e.__class__.__name__}: {e}")

    def _initialize_client(self):
        """Khởi tạo client API dựa trên lựa chọn."""
        # QUAN TRỌNG: Load .env và GHI ĐÈ biến môi trường hệ thống
        load_dotenv(override=True)
        
        if self.api_provider == "openai":
            # Đọc trực tiếp từ file .env để tránh bị ghi đè bởi system env
            dotenv_path = find_dotenv()
            if not dotenv_path:
                dotenv_path = os.path.join(os.getcwd(), '.env')
            
            api_key = ""
            if os.path.exists(dotenv_path):
                with open(dotenv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('OPENAI_API_KEY='):
                            api_key = line.strip().split('=', 1)[1].strip()
                            break
            
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY", "").strip()
            
            if not api_key:
                raise ValueError("Chưa cung cấp OPENAI_API_KEY trong file .env")
            
            self.progress.emit(f"🔑 Sử dụng OpenAI Key: {api_key[:25]}...{api_key[-10:]}")
            self.progress.emit("⚙️ Sử dụng HTTPX client (bypass SDK bug)")
            return HTTPXOpenAIClient(api_key=api_key)
        elif self.api_provider == "grok":
            # Grok (xAI) — API tương thích OpenAI, chỉ đổi base_url
            dotenv_path = find_dotenv()
            if not dotenv_path:
                dotenv_path = os.path.join(os.getcwd(), '.env')
            
            api_key = ""
            if os.path.exists(dotenv_path):
                with open(dotenv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('XAI_API_KEY='):
                            api_key = line.strip().split('=', 1)[1].strip()
                            break
            
            if not api_key:
                api_key = os.getenv("XAI_API_KEY", "").strip()
            
            if not api_key:
                raise ValueError("Chưa cung cấp XAI_API_KEY trong file .env (lấy tại https://console.x.ai)")
            
            self.progress.emit(f"🔑 Sử dụng Grok (xAI) Key: {api_key[:15]}...{api_key[-6:]}")
            client = HTTPXOpenAIClient(api_key=api_key)
            client.base_url = "https://api.x.ai/v1"  # xAI endpoint
            return client
        else: # gemini
            # Đọc trực tiếp từ file .env
            dotenv_path = find_dotenv()
            if not dotenv_path:
                dotenv_path = os.path.join(os.getcwd(), '.env')
            
            api_key = ""
            if os.path.exists(dotenv_path):
                with open(dotenv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('GOOGLE_API_KEY='):
                            api_key = line.strip().split('=', 1)[1].strip()
                            break
            
            if not api_key:
                api_key = os.getenv("GOOGLE_API_KEY", "").strip()
            
            if not api_key:
                raise ValueError("Chưa cung cấp GOOGLE_API_KEY trong file .env")
            
            # Hỗ trợ nhiều key phân tách bằng dấu phẩy (round-robin)
            self._gemini_keys = [k.strip() for k in api_key.split(',') if k.strip()]
            self._gemini_key_idx = 0
            if len(self._gemini_keys) > 1:
                self.progress.emit(f"🔑 Sử dụng {len(self._gemini_keys)} Google API Keys (round-robin)")
                for i, k in enumerate(self._gemini_keys):
                    self.progress.emit(f"  Key {i+1}: {k[:15]}...{k[-6:]}")
            else:
                self.progress.emit(f"🔑 Sử dụng Google Key: {self._gemini_keys[0][:25]}...{self._gemini_keys[0][-10:]}")
            
            genai.configure(api_key=self._gemini_keys[0])
            return genai

    def _rotate_gemini_key(self):
        """Round-robin sang Gemini API key tiếp theo."""
        if len(self._gemini_keys) > 1:
            self._gemini_key_idx = (self._gemini_key_idx + 1) % len(self._gemini_keys)
            next_key = self._gemini_keys[self._gemini_key_idx]
            genai.configure(api_key=next_key)
            return self._gemini_key_idx + 1
        return 1

    # =========================================================================
    # === BATCH TRANSLATION - Gửi nhiều block SRT trong 1 API call ===
    # =========================================================================
    def _translate_file_by_chunks(self, client: Any, content: str, system_prompt: str):
        """Dịch file SRT theo batch COMPACT: chỉ gửi [idx]|text, tiết kiệm ~40% token."""
        blocks = split_srt_blocks(content)
        total_blocks = len(blocks)
        final_translated_blocks: List[str] = [""] * total_blocks
        
        # Parse tất cả block ra: giữ idx, ts, text riêng
        parsed_blocks = []
        for b in blocks:
            idx, ts, text_lines = parse_block(b)
            parsed_blocks.append((idx, ts, text_lines))
        
        # Ngữ cảnh 2 chiều: lưu cặp (text_cn, text_vi) của batch trước
        prev_context_pairs = []  # [(cn_text, vi_text), ...]
        
        total_batches = (total_blocks + BATCH_SIZE - 1) // BATCH_SIZE
        api_calls = 0
        total_input_tokens = 0
        self._total_blocks = total_blocks  # Lưu để hiển thị khi hoàn tất
        
        self.progress.emit(f"📦 [COMPACT MODE] Dịch {total_blocks} block ({total_batches} batch × {BATCH_SIZE} block/batch)")
        self.progress.emit(f"💡 Tiết kiệm ~40% token: chỉ gửi text, không gửi timestamp")
        self.batch_info.emit(f"🔄 Bắt đầu dịch {total_blocks} block ({total_batches} batch)...")
        
        for batch_idx in range(0, total_blocks, BATCH_SIZE):
            if not self.is_running:
                self.progress.emit("Tác vụ đã bị hủy.")
                return None

            batch_start = batch_idx
            batch_end = min(batch_idx + BATCH_SIZE, total_blocks)
            batch_num = batch_idx // BATCH_SIZE + 1
            
            # Cập nhật batch info chi tiết
            progress_pct = int((batch_num - 1) * 100 / total_batches)
            elapsed = time.time() - self._start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            eta_str = f" | ⏱ {mins}p{secs:02d}s" if mins > 0 else f" | ⏱ {secs}s"
            self.batch_info.emit(f"🔄 Đang dịch batch {batch_num}/{total_batches} ({progress_pct}%){eta_str}")
            self.progress.emit(f"\n🔄 Batch {batch_num}/{total_batches} (block {batch_start+1}→{batch_end})...")
            
            # [TỐI ƯU TOKEN] Chỉ gửi text kèm index, KHÔNG gửi timestamp
            text_lines_for_api = []
            batch_cn_texts = {}  # {idx_str: cn_text} để dùng cho enforce_glossary
            for i in range(batch_start, batch_end):
                idx, ts, text_lines = parsed_blocks[i]
                if idx and text_lines:
                    text = ' '.join(l.strip() for l in text_lines)
                    text_lines_for_api.append(f"[{idx}]|{text}")
                    batch_cn_texts[idx] = text
            
            if not text_lines_for_api:
                for k in range(batch_start, batch_end):
                    final_translated_blocks[k] = blocks[k]
                continue
            
            compact_text = "\n".join(text_lines_for_api)
            
            # Tìm thuật ngữ liên quan cho batch này
            all_cn_text = ' '.join(batch_cn_texts.values())
            glossary_hint = find_relevant_terms(all_cn_text, self.glossary)
            if glossary_hint:
                term_count = len(glossary_hint.split('\n'))
                self.progress.emit(f"  📖 Thuật ngữ: {term_count} từ")
            
            # Ngữ cảnh song ngữ (CN→VI) từ batch trước
            prev_ctx = ""
            if prev_context_pairs:
                ctx_lines = []
                for cn, vi in prev_context_pairs[-CONTEXT_OVERLAP:]:
                    ctx_lines.append(f"{cn} → {vi}")
                prev_ctx = "\n".join(ctx_lines)
            
            # Tạo danh sách nhân vật đã biết từ glossary (khi bật tag_characters)
            char_names_hint = ""
            if self.tag_characters and self.glossary:
                char_entries = []
                char_sections = ['nhân vật chính', 'hóa danh vương lâm', 'sư tôn vương lâm',
                                 'đệ tử vương lâm', 'đồng bạn', 'nhân vật phụ', 'phản diện']
                for section in char_sections:
                    if section in self.glossary:
                        for cn_name, vi_name in self.glossary[section].items():
                            char_entries.append(f"{cn_name}={vi_name}")
                if char_entries:
                    char_names_hint = ', '.join(char_entries[:40])  # Giới hạn 40 NV
            
            # Xây dựng prompt compact
            user_prompt = build_batch_prompt(compact_text, prev_ctx, glossary_hint, 
                                            tag_characters=self.tag_characters,
                                            character_names_hint=char_names_hint)
            
            # Ước tính token
            token_est = len(user_prompt) // 4
            total_input_tokens += token_est
            self.progress.emit(f"  📊 ~{token_est} tokens (compact, tiết kiệm ~40%)")
            
            # Gọi API — retry bằng key khác nếu lỗi
            raw_response = ""
            max_retries = max(len(self._gemini_keys) * 4, 15) if self.api_provider == "gemini" else 5
            
            if self.api_provider == "gemini" and len(self._gemini_keys) > 1:
                key_num = self._rotate_gemini_key()
            else:
                key_num = 1
                
            for attempt in range(max_retries):
                if not self.is_running:
                    return final_translated_blocks
                try:
                    if self.api_provider in ("openai", "grok"):
                        raw_response = call_openai_api(client, self.selected_model, system_prompt, user_prompt)
                    else:
                        if len(self._gemini_keys) > 1:
                            self.progress.emit(f"  🔑 Key #{key_num}")
                        raw_response = call_gemini_api(client, self.selected_model, system_prompt, user_prompt)
                    api_calls += 1
                    break  # Thành công → thoát retry
                except Exception as e:
                    err_str = str(e)
                    is_rate_limit = '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower()
                    remaining = max_retries - attempt - 1
                    
                    if remaining > 0:
                        wait_s = 3
                        # Xử lý format gọn thông báo lỗi
                        error_summary = err_str.split('\n')[0][:100] + "..." if len(err_str) > 100 else err_str
                        if is_rate_limit:
                            error_summary = "Lỗi 429: Quota Exceeded / Rate Limit"
                            wait_s = 10
                            m = re.search(r'Please retry in ([\d\.]+)s', err_str)
                            if m:
                                api_wait = int(float(m.group(1))) + 2
                                keys_count = len(self._gemini_keys) if self.api_provider == "gemini" else 1
                                # Thử các key khác trước, nếu hết vòng mới đợi lâu
                                if attempt >= keys_count:
                                    wait_s = min(api_wait, 60)
                                else:
                                    wait_s = min(api_wait, 5) # Vẫn thử nhanh key khác
                        
                        if self.api_provider == "gemini" and len(self._gemini_keys) > 1:
                            key_num = self._rotate_gemini_key()
                            self.progress.emit(f"  ⚠️ Batch {batch_num} lỗi: {error_summary}")
                            self.progress.emit(f"  🔄 Đổi sang Key #{key_num}, retry sau {wait_s}s... (còn {remaining} lần)")
                        else:
                            self.progress.emit(f"  ⚠️ Batch {batch_num} lỗi: {error_summary}")
                            self.progress.emit(f"  🔄 Đợi {wait_s}s rồi thử lại... (còn {remaining} lần)")
                        time.sleep(wait_s)
                    else:
                        error_summary = err_str.split('\n')[0][:100] + "..." if len(err_str) > 100 else err_str
                        if is_rate_limit:
                            error_summary = "Lỗi 429: Quota Exceeded / Rate Limit"
                        self.progress.emit(f"  ❌ Batch {batch_num} thất bại! Lỗi cuối: {error_summary}")
                        raw_response = ""
            
            if not raw_response:
                self.progress.emit(f"  ⚠️ Batch {batch_num} không có kết quả (tất cả API keys đều lỗi/hết lượt)")
                for k in range(batch_start, batch_end):
                    final_translated_blocks[k] = blocks[k]
                progress_pct = int(batch_end * 100 / total_blocks)
                self.update_progress_bar.emit(progress_pct)
                continue
            
            # Parse response compact [idx]|text_vi
            translated_map = self._parse_compact_response(raw_response)
            
            # Ghép lại thành SRT blocks với timestamp gốc + hậu xử lý glossary
            batch_context_pairs = []
            matched_count = 0
            for i in range(batch_start, batch_end):
                idx, ts, orig_text = parsed_blocks[i]
                if idx and idx in translated_map:
                    vi_text = translated_map[idx]
                    cn_text = batch_cn_texts.get(idx, '')
                    
                    # Sanitize
                    vi_text = sanitize_translated_line(vi_text)
                    if not vi_text:
                        final_translated_blocks[i] = blocks[i]
                        continue
                    
                    # Enforce glossary: ép dùng đúng thuật ngữ
                    vi_text = enforce_glossary(vi_text, cn_text, self.glossary)
                    
                    # Giữ nguyên số dòng text gốc
                    orig_line_count = len(orig_text)
                    vi_lines = force_line_count(vi_text, orig_line_count)
                    
                    # Ghép lại thành SRT block hoàn chỉnh
                    final_translated_blocks[i] = "\n".join([idx, ts] + vi_lines)
                    batch_context_pairs.append((cn_text, vi_text))
                    matched_count += 1
                else:
                    final_translated_blocks[i] = blocks[i]
            
            # Cập nhật context song ngữ cho batch tiếp theo
            prev_context_pairs = batch_context_pairs[-CONTEXT_OVERLAP:] if batch_context_pairs else []
            
            self.progress.emit(f"  ✅ Batch {batch_num} hoàn tất ({matched_count}/{batch_end - batch_start} block)")
            progress_pct = int(batch_end * 100 / total_blocks)
            self.update_progress_bar.emit(progress_pct)
        
        # Đảm bảo không có block None/rỗng trước khi retry
        for k in range(total_blocks):
            if not final_translated_blocks[k]:
                final_translated_blocks[k] = blocks[k]
        
        # ====== RETRY: Dịch lại các block bị bỏ sót (vẫn còn tiếng Trung) ======
        cn_char_re = re.compile(r'[\u4e00-\u9fff]')
        missed_indices = []
        for k in range(total_blocks):
            idx, ts, text_lines = parsed_blocks[k]
            if idx and text_lines:
                block_text = ' '.join(l.strip() for l in text_lines)
                # Kiểm tra block đã dịch có còn chứa tiếng Trung không
                translated_block = final_translated_blocks[k]
                # Lấy phần text từ block đã dịch (bỏ idx và timestamp)
                translated_lines = translated_block.splitlines()
                if len(translated_lines) >= 3:
                    translated_text_part = ' '.join(translated_lines[2:])
                else:
                    translated_text_part = block_text
                
                if cn_char_re.search(translated_text_part):
                    missed_indices.append(k)
        
        if missed_indices and self.is_running:
            self.progress.emit(f"\n� Phát hiện {len(missed_indices)} block chưa được dịch, đang dịch lại...")
            
            # Tạo batch retry nhỏ
            retry_text_lines = []
            retry_cn_texts = {}
            for k in missed_indices:
                idx, ts, text_lines = parsed_blocks[k]
                if idx and text_lines:
                    text = ' '.join(l.strip() for l in text_lines)
                    retry_text_lines.append(f"[{idx}]|{text}")
                    retry_cn_texts[idx] = text
            
            if retry_text_lines:
                retry_compact = "\n".join(retry_text_lines)
                all_retry_cn = ' '.join(retry_cn_texts.values())
                retry_glossary = find_relevant_terms(all_retry_cn, self.glossary)
                
                # Thêm ngữ cảnh từ các block trước block bị sót
                retry_ctx = ""
                if missed_indices[0] > 0:
                    ctx_pairs = []
                    ctx_start = max(0, missed_indices[0] - CONTEXT_OVERLAP)
                    for ci in range(ctx_start, missed_indices[0]):
                        cidx, cts, ctext = parsed_blocks[ci]
                        if cidx:
                            cn = ' '.join(l.strip() for l in ctext)
                            # Lấy text đã dịch
                            vi_block_lines = final_translated_blocks[ci].splitlines()
                            vi = ' '.join(vi_block_lines[2:]) if len(vi_block_lines) >= 3 else cn
                            ctx_pairs.append(f"{cn} → {vi}")
                    retry_ctx = "\n".join(ctx_pairs)
                
                retry_prompt = build_batch_prompt(retry_compact, retry_ctx, retry_glossary)
                
                try:
                    # Retry với key rotation (giống batch translate chính)
                    retry_response = ""
                    retry_max = max(len(self._gemini_keys) * 4, 15) if self.api_provider == "gemini" else 5
                    
                    if self.api_provider == "gemini" and len(self._gemini_keys) > 1:
                        key_num = self._rotate_gemini_key()
                    else:
                        key_num = 1
                        
                    for r_attempt in range(retry_max):
                        if not self.is_running:
                            break
                        try:
                            if self.api_provider in ("openai", "grok"):
                                retry_response = call_openai_api(client, self.selected_model, system_prompt, retry_prompt)
                            else:
                                if len(self._gemini_keys) > 1:
                                    self.progress.emit(f"  🔑 Retry Key #{key_num}")
                                retry_response = call_gemini_api(client, self.selected_model, system_prompt, retry_prompt)
                            api_calls += 1
                            break  # Thành công
                        except Exception as re_err:
                            err_str = str(re_err)
                            is_rate_limit = '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower()
                            r_remaining = retry_max - r_attempt - 1
                            
                            if r_remaining > 0:
                                wait_s = 3
                                error_summary = err_str.split('\n')[0][:100] + "..." if len(err_str) > 100 else err_str
                                if is_rate_limit:
                                    error_summary = "Lỗi 429: Quota Exceeded / Rate Limit"
                                    wait_s = 10
                                    m = re.search(r'Please retry in ([\d\.]+)s', err_str)
                                    if m:
                                        api_wait = int(float(m.group(1))) + 2
                                        keys_count = len(self._gemini_keys) if self.api_provider == "gemini" else 1
                                        if r_attempt >= keys_count:
                                            wait_s = min(api_wait, 60)
                                        else:
                                            wait_s = min(api_wait, 5)
                                
                                if self.api_provider == "gemini" and len(self._gemini_keys) > 1:
                                    key_num = self._rotate_gemini_key()
                                    self.progress.emit(f"  ⚠️ Retry lỗi: {error_summary}")
                                    self.progress.emit(f"  🔄 Đổi Key #{key_num}, thử lại sau {wait_s}s... (còn {r_remaining} lần)")
                                else:
                                    self.progress.emit(f"  ⚠️ Retry lỗi: {error_summary}")
                                    self.progress.emit(f"  🔄 Đợi {wait_s}s... (còn {r_remaining} lần)")
                                time.sleep(wait_s)
                            else:
                                error_summary = err_str.split('\n')[0][:100] + "..." if len(err_str) > 100 else err_str
                                if is_rate_limit:
                                    error_summary = "Lỗi 429: Quota Exceeded / Rate Limit"
                                self.progress.emit(f"  ❌ Retry thất bại. Lỗi cuối: {error_summary}")
                                retry_response = ""
                except Exception as e:
                    self.progress.emit(f"  ❌ Retry lỗi API: {e}")
                    retry_response = ""
                
                if retry_response:
                    retry_map = self._parse_compact_response(retry_response)
                    retry_success = 0
                    for k in missed_indices:
                        idx, ts, orig_text = parsed_blocks[k]
                        if idx and idx in retry_map:
                            vi_text = sanitize_translated_line(retry_map[idx])
                            if vi_text:
                                cn_text = retry_cn_texts.get(idx, '')
                                vi_text = enforce_glossary(vi_text, cn_text, self.glossary)
                                orig_line_count = len(orig_text)
                                vi_lines = force_line_count(vi_text, orig_line_count)
                                final_translated_blocks[k] = "\n".join([idx, ts] + vi_lines)
                                retry_success += 1
                    
                    self.progress.emit(f"  ✅ Retry thành công: {retry_success}/{len(missed_indices)} block")
                else:
                    self.progress.emit(f"  ⚠️ Retry không có kết quả")
        
        # ====== HẬU XỬ LÝ: Gộp block '...' vào block trước ======
        final_translated_blocks, ellipsis_removed = merge_ellipsis_blocks(final_translated_blocks)
        if ellipsis_removed > 0:
            self.progress.emit(f"\n🔗 Đã gộp {ellipsis_removed} block '...' vào block trước (cộng thời gian)")
        
        # Thống kê
        sep = "━" * 40
        self.progress.emit(f"\n{sep}")
        self.progress.emit(f"🔄 Đã hoàn tất dịch {total_blocks} block trong {api_calls} lần gọi API.")
        if ellipsis_removed > 0:
            self.progress.emit(f"🔗 Gộp '...' → còn {len(final_translated_blocks)} block")
        self.progress.emit(f"💰 Tổng ~{total_input_tokens} input tokens (compact mode)")
        self.progress.emit(sep)
        
        return final_translated_blocks
    
    # =========================================================================
    # === VIDEO-ASSISTED: Upload video lên Gemini để tag NV chính xác
    # =========================================================================
    
    def _compress_video_for_upload(self, video_path: str, quality: str) -> str:
        """Nén video bằng FFmpeg trước khi upload cho Gemini. Trả về path file nén hoặc None."""
        import subprocess
        import tempfile
        
        # Tìm ffmpeg
        ffmpeg_path = 'ffmpeg'
        if getattr(sys, 'frozen', False):
            bundled = os.path.join(os.path.dirname(sys.executable), 'ffmpeg', 'ffmpeg.exe')
            if os.path.isfile(bundled):
                ffmpeg_path = bundled
        else:
            local = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'ffmpeg.exe')
            if os.path.isfile(local):
                ffmpeg_path = local
        
        # Resolution & bitrate config
        if quality == '480p':
            scale = 'scale=-2:480'
            v_bitrate = '500k'
            a_bitrate = '64k'
        else:  # 720p
            scale = 'scale=-2:720'
            v_bitrate = '1000k'
            a_bitrate = '96k'
        
        try:
            orig_size = os.path.getsize(video_path) / (1024 * 1024)
            self.progress.emit(f"  🔧 Đang nén video → {quality} (gốc: {orig_size:.1f} MB)...")
            
            # Output file
            tmp_dir = tempfile.gettempdir()
            base = os.path.splitext(os.path.basename(video_path))[0]
            out_path = os.path.join(tmp_dir, f"{base}_{quality}_gemini.mp4")
            
            cmd = [
                ffmpeg_path, '-y', '-i', video_path,
                '-vf', scale,
                '-b:v', v_bitrate,
                '-b:a', a_bitrate,
                '-c:v', 'libx264', '-preset', 'fast',
                '-c:a', 'aac',
                '-movflags', '+faststart',
                out_path
            ]
            
            # Ẩn cửa sổ console trên Windows
            kwargs = {}
            if sys.platform == 'win32':
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs['startupinfo'] = si
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, **kwargs)
            
            if result.returncode == 0 and os.path.isfile(out_path):
                new_size = os.path.getsize(out_path) / (1024 * 1024)
                ratio = orig_size / max(new_size, 0.1)
                self.progress.emit(f"  ✅ Nén xong: {new_size:.1f} MB (giảm {ratio:.1f}x)")
                return out_path
            else:
                self.progress.emit(f"  ⚠️ FFmpeg nén lỗi, upload video gốc...")
                return None
                
        except FileNotFoundError:
            self.progress.emit(f"  ⚠️ Không tìm thấy FFmpeg, upload video gốc...")
            return None
        except subprocess.TimeoutExpired:
            self.progress.emit(f"  ⚠️ Nén video quá 5 phút, upload video gốc...")
            return None
        except Exception as e:
            self.progress.emit(f"  ⚠️ Lỗi nén: {e}, upload video gốc...")
            return None
    
    def _tag_with_video(self, client, translated_blocks: list) -> list:
        """Upload video lên Gemini, cho nó xem và tag nhân vật nói."""
        
        if self.api_provider != "gemini":
            self.progress.emit("  ⚠️ Video-assisted chỉ hỗ trợ Gemini API. Bỏ qua.")
            return translated_blocks
        
        try:
            # Build SRT text có số thứ tự + timestamp + text dịch
            srt_lines = []
            for i, block in enumerate(translated_blocks):
                idx, ts, text_lines = parse_block(block)
                if idx and text_lines:
                    text = ' '.join(l.strip() for l in text_lines)
                    text = re.sub(r'\{.+?\}\s*', '', text).strip()
                    srt_lines.append(f"[{idx}] {ts} | {text}")
            
            srt_text = "\n".join(srt_lines)
            
            # Build character names hint
            char_hint = ""
            if self.glossary:
                entries = []
                for section in ['nhân vật chính', 'hóa danh vương lâm', 'sư tôn vương lâm',
                               'đệ tử vương lâm', 'đồng bạn', 'nhân vật phụ', 'phản diện']:
                    if section in self.glossary:
                        for cn, vi in self.glossary[section].items():
                            entries.append(f"{cn}={vi}")
                if entries:
                    char_hint = "Nhân vật đã biết: " + ', '.join(entries[:40]) + "\n\n"
            
            # Step 1: Nén video (nếu cần) rồi upload
            upload_path = self.video_path
            compressed_tmp = None
            if self.video_quality in ('720p', '480p'):
                compressed_tmp = self._compress_video_for_upload(self.video_path, self.video_quality)
                if compressed_tmp:
                    upload_path = compressed_tmp
            
            file_size_mb = os.path.getsize(upload_path) / (1024 * 1024)
            self.progress.emit(f"  📤 Đang upload video ({file_size_mb:.1f} MB): {os.path.basename(upload_path)}...")
            video_file = genai.upload_file(path=upload_path)
            self.progress.emit(f"  ☁️ Upload xong, đang xử lý video trên server...")
            
            # Wait for processing
            wait_count = 0
            while video_file.state.name == "PROCESSING":
                if not self.is_running:
                    return translated_blocks
                time.sleep(5)
                wait_count += 1
                video_file = genai.get_file(video_file.name)
                if wait_count % 4 == 0:
                    self.progress.emit(f"  ⏳ Đang xử lý video... ({wait_count * 5}s)")
            
            if video_file.state.name == "FAILED":
                self.progress.emit(f"  ❌ Video processing failed: {video_file.state.name}")
                return translated_blocks
            
            self.progress.emit(f"  ✅ Video đã sẵn sàng! Đang gửi cho Gemini phân tích...")
            
            # Step 2: Send video + SRT to Gemini
            prompt = (
                f"{char_hint}"
                "Xem video này và xác định NHÂN VẬT NÀO ĐANG NÓI trong mỗi câu phụ đề bên dưới.\n\n"
                "Dựa vào:\n"
                "- Hình ảnh: ai xuất hiện trên màn hình, miệng ai đang mở\n"
                "- Giọng nói: giọng nam/nữ, giọng trầm/cao\n"
                "- Ngữ cảnh hội thoại: ai đang nói với ai\n\n"
                "Nếu là mô tả/旁白 (không ai nói, chỉ miêu tả) → {旁白}\n\n"
                f"【PHỤ ĐỀ CẦN TAG】\n{srt_text}\n\n"
                "→ Trả về MỖI dòng CHÍNH XÁC theo format:\n"
                "[số]|{Tên NV tiếng Việt}\n\n"
                "VD:\n[1]|{Vương Lâm}\n[2]|{旁白}\n[3]|{Kế Đô}\n\n"
                "CHỈ trả kết quả, KHÔNG giải thích. LUÔN dùng tên tiếng Việt."
            )
            
            model = genai.GenerativeModel(
                self.selected_model,
                system_instruction="Bạn là chuyên gia phân tích video hoạt hình Trung Quốc. Xem video và xác định nhân vật nào đang nói từng câu."
            )
            
            response = model.generate_content(
                [video_file, prompt],
                generation_config=genai.types.GenerationConfig(temperature=0.2),
                request_options={'timeout': 300}
            )
            
            result_text = response.text or ""
            
            # Debug preview
            preview = result_text.strip()[:300].replace('\n', ' | ')
            self.progress.emit(f"  Response preview: {preview}")
            
            # Step 3: Parse response
            tag_results = {}
            for line in result_text.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                m = re.match(r'\[?(\d+)\]?\s*\|?\s*(\{.+?\})', line)
                if m:
                    tag_results[m.group(1)] = m.group(2)
            
            self.progress.emit(f"  Parsed {len(tag_results)} tags từ video analysis")
            
            # Step 4: Merge tags
            tagged_count = 0
            result_blocks = list(translated_blocks)
            for i, block in enumerate(result_blocks):
                idx, ts, text_lines = parse_block(block)
                if idx and idx in tag_results and text_lines:
                    tag = tag_results[idx]
                    text_lines[0] = re.sub(r'\{.+?\}\s*', '', text_lines[0]).strip()
                    text_lines[0] = f"{tag} {text_lines[0]}"
                    result_blocks[i] = "\n".join([idx, ts] + text_lines)
                    tagged_count += 1
            
            self.progress.emit(f"  🎬 Video-assisted: tag {tagged_count}/{len(translated_blocks)} block ({tagged_count*100//max(len(translated_blocks),1)}%)")
            
            # Cleanup
            try:
                genai.delete_file(video_file.name)
                self.progress.emit(f"  🗑️ Đã xóa video trên server")
            except:
                pass
            # Xóa file nén tạm
            if compressed_tmp and os.path.exists(compressed_tmp):
                try:
                    os.remove(compressed_tmp)
                except:
                    pass
            
            return result_blocks
            
        except Exception as e:
            self.progress.emit(f"  ❌ Video-assisted failed: {e}")
            self.progress.emit(f"  ↩️ Giữ nguyên tags từ pass dịch (text-only)")
            return translated_blocks
    
    def _parse_compact_response(self, response: str) -> dict:
        """Parse response compact [idx]|text thành dict {idx_str: translated_text}."""
        result = {}
        response = sanitize_output(response)
        
        # Loại bỏ markdown code block nếu có
        response = re.sub(r'^```[a-zA-Z]*\n?', '', response)
        response = re.sub(r'\n?```$', '', response)
        response = response.strip()
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Match format [idx]|text
            m = re.match(r'\[(\d+)\]\|(.+)', line)
            if m:
                idx_str = m.group(1)
                text = m.group(2).strip()
                if text:
                    result[idx_str] = text
            else:
                # Fallback: thử match format idx|text (không có dấu [])
                m2 = re.match(r'(\d+)\|(.+)', line)
                if m2:
                    idx_str = m2.group(1)
                    text = m2.group(2).strip()
                    if text:
                        result[idx_str] = text
                else:
                    # Fallback 2: thử match format SRT cũ nếu AI trả về full SRT
                    # (backward compatibility)
                    pass
        
        # Nếu compact parse thất bại (AI trả về SRT thay vì compact),
        # thử fallback sang SRT parser
        if not result:
            response_blocks = split_srt_blocks(response)
            for rb in response_blocks:
                idx_line, ts_line, text_lines = parse_block(rb)
                if idx_line and text_lines:
                    text = ' '.join(l.strip() for l in text_lines)
                    if text:
                        result[idx_line] = text
        
        return result

# ================== GIAO DIỆN ỨNG DỤNG ==================
# ===================== DARK THEME STYLESHEET =====================
DARK_STYLE = """
/* --- Global --- */
QWidget {
    background-color: #1a1b2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 10pt;
}

/* --- Group Box --- */
QGroupBox {
    background-color: #232442;
    border: 1px solid #3a3b5c;
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px 12px 10px 12px;
    font-weight: bold;
    font-size: 10pt;
    color: #b8c0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
    background-color: #2d2e50;
    border-radius: 6px;
    color: #8ec8f6;
}

/* --- Buttons --- */
QPushButton {
    background-color: #3d3e6b;
    color: #e0e0e0;
    border: 1px solid #4e4f8a;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 10pt;
}
QPushButton:hover {
    background-color: #5252a0;
    border: 1px solid #6c6dca;
}
QPushButton:pressed {
    background-color: #6c6dca;
}
QPushButton:disabled {
    background-color: #2a2b45;
    color: #555;
    border: 1px solid #333;
}
QPushButton#translateBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f67e0, stop:1 #7c4dff);
    color: white;
    font-size: 12pt;
    padding: 10px 24px;
    border: none;
    border-radius: 10px;
}
QPushButton#translateBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5f77f0, stop:1 #9c6dff);
}
QPushButton#translateBtn:disabled {
    background: #2a2b45;
    color: #555;
}
QPushButton#compareBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e07c4f, stop:1 #ff9a4d);
    color: white;
    font-size: 11pt;
    padding: 10px 20px;
    border: none;
    border-radius: 10px;
}
QPushButton#compareBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f08c5f, stop:1 #ffaa6d);
}
QPushButton#grammarBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2ecc71, stop:1 #27ae60);
    color: white;
    font-size: 11pt;
    padding: 10px 20px;
    border: none;
    border-radius: 10px;
}
QPushButton#grammarBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3ddc84, stop:1 #2ecc71);
}
QPushButton#grammarBtn:disabled {
    background: #2a2b45;
    color: #555;
}

/* --- Line Edit / Text Edit --- */
QLineEdit, QTextEdit {
    background-color: #2a2b4a;
    color: #e0e0e0;
    border: 1px solid #3a3b5c;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #5252a0;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #6c6dca;
}

/* --- ComboBox --- */
QComboBox {
    background-color: #2a2b4a;
    color: #e0e0e0;
    border: 1px solid #3a3b5c;
    border-radius: 6px;
    padding: 6px 10px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #2a2b4a;
    color: #e0e0e0;
    selection-background-color: #5252a0;
    border: 1px solid #3a3b5c;
}

/* --- Radio / Checkbox --- */
QRadioButton, QCheckBox {
    color: #c0c8e0;
    spacing: 6px;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px; height: 16px;
}

/* --- Progress Bar --- */
QProgressBar {
    background-color: #2a2b4a;
    border: 1px solid #3a3b5c;
    border-radius: 8px;
    text-align: center;
    color: #e0e0e0;
    height: 22px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f67e0, stop:0.5 #7c4dff, stop:1 #a855f7);
    border-radius: 7px;
}

/* --- Tab Widget --- */
QTabWidget::pane {
    background-color: #232442;
    border: 1px solid #3a3b5c;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background-color: #2a2b4a;
    color: #8890b0;
    border: 1px solid #3a3b5c;
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: #232442;
    color: #8ec8f6;
    border-bottom: 2px solid #7c4dff;
}
QTabBar::tab:hover:!selected {
    background-color: #3d3e6b;
    color: #c0c8e0;
}

/* --- Table --- */
QTableWidget {
    background-color: #232442;
    alternate-background-color: #2a2b4a;
    gridline-color: #3a3b5c;
    color: #e0e0e0;
    border: 1px solid #3a3b5c;
    border-radius: 6px;
    selection-background-color: #3d3e6b;
}
QTableWidget::item {
    padding: 6px;
}
QTableWidget::item:selected {
    background-color: #4f67e0;
    color: white;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3d3e6b, stop:1 #2d2e50);
    color: #8ec8f6;
    padding: 8px;
    border: 1px solid #4e4f8a;
    font-weight: bold;
    font-size: 10pt;
}

/* --- Scrollbar --- */
QScrollBar:vertical {
    background: #1a1b2e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #4e4f8a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #6c6dca;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #1a1b2e;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #4e4f8a;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background: #6c6dca;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* --- Labels --- */
QLabel {
    color: #c0c8e0;
}
QLabel#headerLabel {
    color: #8ec8f6;
    font-size: 16pt;
    font-weight: bold;
}
QLabel#subtitleLabel {
    color: #7880a0;
    font-size: 9pt;
}

/* --- Form Label --- */
QFormLayout QLabel {
    color: #a0a8c0;
    font-weight: normal;
}

/* --- Message Box --- */
QMessageBox {
    background-color: #232442;
}
QMessageBox QLabel {
    color: #e0e0e0;
}
QMessageBox QPushButton {
    min-width: 80px;
}
"""

class SettingsDialog(QWidget):
    """Cửa sổ cài đặt API Keys và System Prompt."""
    def __init__(self, dotenv_path: str, parent=None):
        super().__init__(parent)
        self.dotenv_path = dotenv_path
        self.setWindowTitle("⚙️ Cài đặt")
        self.setGeometry(200, 200, 600, 500)
        self.setMinimumSize(500, 400)
        try: self.setWindowIcon(QIcon('icon.ico'))
        except: pass

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # --- API Keys ---
        keys_group = QGroupBox("🔑 API Keys")
        keys_form = QFormLayout()
        keys_form.setSpacing(8)
        self.google_key_input = QLineEdit()
        self.google_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.google_key_input.setPlaceholderText("Nhập Google API Key...")
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_input.setPlaceholderText("Nhập OpenAI API Key...")
        self.grok_key_input = QLineEdit()
        self.grok_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.grok_key_input.setPlaceholderText("Nhập Grok (xAI) API Key...")
        keys_form.addRow("Google Gemini:", self.google_key_input)
        keys_form.addRow("OpenAI GPT:", self.openai_key_input)
        keys_form.addRow("Grok (xAI):", self.grok_key_input)
        keys_actions = QHBoxLayout()
        self.show_keys_cb = QCheckBox("👁 Hiện keys")
        self.show_keys_cb.toggled.connect(self._toggle_key_visibility)
        self.save_keys_btn = QPushButton("💾 Lưu Keys")
        self.save_keys_btn.clicked.connect(self._save_keys)
        keys_actions.addWidget(self.show_keys_cb)
        keys_actions.addStretch()
        keys_actions.addWidget(self.save_keys_btn)
        keys_v = QVBoxLayout(keys_group)
        keys_v.addLayout(keys_form)
        keys_v.addLayout(keys_actions)
        layout.addWidget(keys_group)

        # --- System Prompt ---
        prompt_group = QGroupBox("📝 System Prompt")
        prompt_lay = QVBoxLayout(prompt_group)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setFont(QFont("Consolas", 9))
        self.prompt_edit.setPlaceholderText("Nhập system prompt tùy chỉnh...")
        self.save_prompt_btn = QPushButton("💾 Lưu Prompt")
        self.save_prompt_btn.clicked.connect(self._save_prompt)
        prompt_lay.addWidget(self.prompt_edit)
        prompt_lay.addWidget(self.save_prompt_btn, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(prompt_group)

        self.setLayout(layout)
        self._load_values()

    def _read_env(self, key, default=""):
        try:
            from dotenv import dotenv_values
            return dotenv_values(self.dotenv_path).get(key, default) or default
        except Exception:
            return os.getenv(key, default) or default

    def _load_values(self):
        self.google_key_input.setText(self._read_env("GOOGLE_API_KEY"))
        self.openai_key_input.setText(self._read_env("OPENAI_API_KEY"))
        self.grok_key_input.setText(self._read_env("XAI_API_KEY"))
        saved = self._read_env("CUSTOM_SYSTEM_PROMPT")
        self.prompt_edit.setPlainText(saved if saved else DEFAULT_SYSTEM_PROMPT)

    def _toggle_key_visibility(self, checked):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.google_key_input.setEchoMode(mode)
        self.openai_key_input.setEchoMode(mode)
        self.grok_key_input.setEchoMode(mode)

    def _save_keys(self):
        try:
            set_key(self.dotenv_path, "GOOGLE_API_KEY", self.google_key_input.text().strip(), quote_mode="never")
            set_key(self.dotenv_path, "OPENAI_API_KEY", self.openai_key_input.text().strip(), quote_mode="never")
            set_key(self.dotenv_path, "XAI_API_KEY", self.grok_key_input.text().strip(), quote_mode="never")
            load_dotenv(self.dotenv_path, override=True)
            QMessageBox.information(self, "Thành công", "Đã lưu API Keys!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu: {e}")

    def _save_prompt(self):
        text = self.prompt_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Cảnh báo", "Prompt không được để trống.")
            return
        try:
            set_key(self.dotenv_path, "CUSTOM_SYSTEM_PROMPT", text, quote_mode="always")
            load_dotenv(self.dotenv_path, override=True)
            QMessageBox.information(self, "Thành công", "Đã lưu System Prompt!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu: {e}")

    def get_prompt(self):
        return self.prompt_edit.toPlainText().strip() or DEFAULT_SYSTEM_PROMPT


class TranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.input_file_path = ""
        self.last_output_path = ""
        self.thread = None
        self.worker = None
        self.settings_win = None
        self._init_dotenv()
        self._init_ui()

    def _init_dotenv(self):
        self.dotenv_path = find_dotenv()
        if not self.dotenv_path:
            self.dotenv_path = os.path.join(os.getcwd(), '.env')
            if not os.path.exists(self.dotenv_path):
                with open(self.dotenv_path, 'w', encoding='utf-8') as f:
                    f.write("# API Keys\n")
        load_dotenv(self.dotenv_path, override=True)

    def _init_ui(self):
        self.setWindowTitle('⚡ SRT Translator Pro')
        self.setGeometry(80, 50, 1300, 850)
        self.setMinimumSize(900, 600)
        try: self.setWindowIcon(QIcon('icon.ico'))
        except: pass

        root = QVBoxLayout()
        root.setSpacing(6)
        root.setContentsMargins(10, 8, 10, 8)

        # ═══════ TOOLBAR (1 dòng gọn) ═══════
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # API
        self.radio_gemini = QRadioButton("Gemini")
        self.radio_gemini.setChecked(True)
        self.radio_openai = QRadioButton("OpenAI")
        self.radio_grok = QRadioButton("Grok")
        self.radio_gemini.toggled.connect(self._update_models)
        self.radio_openai.toggled.connect(self._update_models)
        self.radio_grok.toggled.connect(self._update_models)
        toolbar.addWidget(self.radio_gemini)
        toolbar.addWidget(self.radio_openai)
        toolbar.addWidget(self.radio_grok)

        # Model
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(170)
        toolbar.addWidget(self.model_combo)

        # Separator
        sep1 = QLabel("│")
        sep1.setStyleSheet("color: #3a3b5c; font-size: 14pt;")
        toolbar.addWidget(sep1)

        # File
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Chưa chọn file SRT...")
        toolbar.addWidget(self.file_path_edit, 1)  # stretch

        self.btn_file = QPushButton("📂")
        self.btn_file.setToolTip("Chọn file SRT")
        self.btn_file.setFixedWidth(42)
        self.btn_file.clicked.connect(self._open_file)
        toolbar.addWidget(self.btn_file)

        # Separator
        sep2 = QLabel("│")
        sep2.setStyleSheet("color: #3a3b5c; font-size: 14pt;")
        toolbar.addWidget(sep2)

        # Translate button
        self.btn_translate = QPushButton("🚀 Dịch")
        self.btn_translate.setObjectName("translateBtn")
        self.btn_translate.setEnabled(False)
        self.btn_translate.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_translate.clicked.connect(self._start_translation)
        toolbar.addWidget(self.btn_translate)

        # Grammar fix button
        self.btn_grammar = QPushButton("✏️ Sửa ngữ pháp")
        self.btn_grammar.setObjectName("grammarBtn")
        self.btn_grammar.setFont(QFont("Segoe UI", 10))
        self.btn_grammar.setEnabled(False)
        self.btn_grammar.clicked.connect(self._start_grammar_fix)
        toolbar.addWidget(self.btn_grammar)

        # Compare button
        self.btn_compare = QPushButton("🔍 So sánh")
        self.btn_compare.setObjectName("compareBtn")
        self.btn_compare.setFont(QFont("Segoe UI", 10))
        self.btn_compare.clicked.connect(self._open_compare_dialog)
        toolbar.addWidget(self.btn_compare)

        # Settings button
        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setToolTip("Cài đặt API Keys & Prompt")
        self.btn_settings.setFixedWidth(42)
        self.btn_settings.clicked.connect(self._open_settings)
        toolbar.addWidget(self.btn_settings)

        root.addLayout(toolbar)

        # ═══════ GLOSSARY ROW ═══════
        glossary_row = QHBoxLayout()
        glossary_row.setSpacing(8)

        glossary_label = QLabel("📖 Glossary:")
        glossary_label.setStyleSheet("color: #8ec8f6; font-weight: bold;")
        glossary_row.addWidget(glossary_label)

        self.glossary_combo = QComboBox()
        self.glossary_combo.setMinimumWidth(200)
        self.glossary_combo.setToolTip("Chọn file glossary thuật ngữ")
        self._refresh_glossary_combo()
        glossary_row.addWidget(self.glossary_combo, 1)

        self.btn_add_glossary = QPushButton("📂+ Thêm")
        self.btn_add_glossary.setToolTip("Thêm file glossary mới")
        self.btn_add_glossary.setFixedWidth(90)
        self.btn_add_glossary.clicked.connect(self._add_glossary)
        glossary_row.addWidget(self.btn_add_glossary)

        self.btn_remove_glossary = QPushButton("🗑 Xóa")
        self.btn_remove_glossary.setToolTip("Xóa glossary đang chọn (không được xóa mặc định)")
        self.btn_remove_glossary.setFixedWidth(80)
        self.btn_remove_glossary.clicked.connect(self._remove_glossary)
        glossary_row.addWidget(self.btn_remove_glossary)

        glossary_row.addWidget(QLabel("  🌐"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("🇻🇳 Tiếng Việt", "vi")
        self.lang_combo.addItem("🇬🇧 Tiếng Anh", "en")
        self.lang_combo.addItem("🇪🇸 Tây Ban Nha", "es")
        self.lang_combo.addItem("🇧🇷 Bồ Đào Nha", "pt")
        self.lang_combo.addItem("🇫🇷 Tiếng Pháp", "fr")
        self.lang_combo.addItem("🇩🇪 Tiếng Đức", "de")
        self.lang_combo.addItem("🇷🇺 Tiếng Nga", "ru")
        self.lang_combo.addItem("🇸🇦 Ả Rập", "ar")
        self.lang_combo.addItem("🇮🇳 Tiếng Hindi", "hi")
        self.lang_combo.addItem("🇰🇷 Hàn Quốc", "ko")
        self.lang_combo.addItem("🇯🇵 Nhật Bản", "ja")
        self.lang_combo.addItem("🇹🇭 Thái Lan", "th")
        self.lang_combo.addItem("🇮🇩 Indonesia", "id")
        self.lang_combo.addItem("🇲🇾 Malaysia", "ms")
        self.lang_combo.addItem("🇵🇭 Philippines", "fil")
        self.lang_combo.addItem("🇹🇷 Thổ Nhĩ Kỳ", "tr")
        self.lang_combo.setFixedWidth(160)
        self.lang_combo.setToolTip("Ngôn ngữ đích để dịch sang")
        glossary_row.addWidget(self.lang_combo)

        root.addLayout(glossary_row)

        # ═══════ CHECKBOX NHẬN DIỆN NHÂN VẬT ═══════
        self.chk_tag_characters = QCheckBox("🎭 Nhận diện nhân vật nói (cho lồng tiếng đa giọng)")
        self.chk_tag_characters.setChecked(False)
        self.chk_tag_characters.setToolTip(
            "Khi bật: AI sẽ gắn {Tên NV} trước mỗi câu thoại.\n"
            "VD: {Vương Lâm} Ta chính là thiên mệnh chi nhân!\n"
            "Dùng cho chế độ lồng tiếng đa giọng ở Tab Chuyển Đổi."
        )
        self.chk_tag_characters.toggled.connect(self._on_tag_toggled)
        root.addWidget(self.chk_tag_characters)
        
        # Video file input (cho Video-assisted tagging - ẩn mặc định)
        self.video_row = QWidget()
        vr_lay = QHBoxLayout(self.video_row)
        vr_lay.setContentsMargins(20, 0, 0, 0)
        vr_lay.addWidget(QLabel("🎬 Video (tag NV chính xác hơn):"))
        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText("Chọn video để Gemini xem và tag NV (~95% accuracy)")
        vr_lay.addWidget(self.video_path_edit)
        btn_browse_video = QPushButton("📂")
        btn_browse_video.setFixedWidth(35)
        btn_browse_video.clicked.connect(self._browse_video)
        vr_lay.addWidget(btn_browse_video)
        # ComboBox chọn chất lượng video upload
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItem("Mặc định", "original")
        self.video_quality_combo.addItem("720p (nhanh hơn)", "720p")
        self.video_quality_combo.addItem("480p (nhanh nhất)", "480p")
        self.video_quality_combo.setCurrentIndex(1)  # Mặc định chọn 720p
        self.video_quality_combo.setFixedWidth(140)
        self.video_quality_combo.setToolTip("Nén video trước khi upload cho Gemini.\n480p/720p giảm thời gian upload 5-20x, vẫn đủ chính xác.")
        vr_lay.addWidget(self.video_quality_combo)
        self.video_row.setVisible(False)
        root.addWidget(self.video_row)

        # ═══════ PROGRESS BAR + BATCH INFO ═══════
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(20)
        root.addWidget(self.progress_bar)
        
        # Label hiển thị chi tiết batch và thời gian
        self.lbl_batch_info = QLabel("")
        self.lbl_batch_info.setStyleSheet("color: #8888cc; font-size: 11px; padding: 2px 4px;")
        root.addWidget(self.lbl_batch_info)

        # ═══════ MAIN TABS (chiếm hết phần còn lại) ═══════
        self.tabs = QTabWidget()

        # --- Tab Nhật Ký ---
        log_tab = QWidget()
        log_lay = QVBoxLayout(log_tab)
        log_lay.setContentsMargins(4, 4, 4, 4)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFont(QFont("Consolas", 9))
        self.log_edit.setPlainText(
            "🎉 Chào mừng đến SRT Translator Pro!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "▸ Bấm ⚙️ để cấu hình API Keys\n"
            "▸ Chọn file .srt rồi bấm 🚀 Dịch\n"
            "▸ Tab So Sánh sẽ hiện kết quả đối chiếu"
        )
        log_lay.addWidget(self.log_edit)
        self.tabs.addTab(log_tab, "📋 Nhật Ký")

        # --- Tab Xem Trước ---
        preview_tab = QWidget()
        preview_lay = QVBoxLayout(preview_tab)
        preview_lay.setContentsMargins(4, 4, 4, 4)

        self.preview_info = QLabel("📖 Chọn file SRT để xem trước nội dung")
        self.preview_info.setStyleSheet("color: #7880a0; padding: 4px;")
        preview_lay.addWidget(self.preview_info)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(['#', 'Thời gian', 'Nội dung gốc'])
        ph = self.preview_table.horizontalHeader()
        ph.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        ph.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        ph.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.preview_table.setColumnWidth(0, 45)
        self.preview_table.setColumnWidth(1, 215)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setWordWrap(True)
        self.preview_table.setFont(QFont('Segoe UI', 10))
        ph.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        preview_lay.addWidget(self.preview_table)

        self.preview_stats = QLabel("")
        self.preview_stats.setStyleSheet("color: #7880a0; padding: 2px;")
        preview_lay.addWidget(self.preview_stats)

        self.tabs.addTab(preview_tab, "📖 Xem Trước")

        # --- Tab So Sánh ---
        cmp_tab = QWidget()
        cmp_lay = QVBoxLayout(cmp_tab)
        cmp_lay.setContentsMargins(4, 4, 4, 4)

        self.cmp_info = QLabel("🔍 Dịch xong hoặc bấm \"So sánh\" để xem đối chiếu")
        self.cmp_info.setStyleSheet("color: #7880a0; padding: 4px;")
        cmp_lay.addWidget(self.cmp_info)

        # Nút gộp + lưu + undo + xóa + lọc trùng
        cmp_btn_row = QHBoxLayout()
        self.btn_merge_rows = QPushButton("🔗 Gộp")
        self.btn_merge_rows.setToolTip("Chọn nhiều dòng liên tiếp (Shift+Click) rồi gộp lại thành 1 dòng")
        self.btn_merge_rows.clicked.connect(self._merge_selected_rows)
        cmp_btn_row.addWidget(self.btn_merge_rows)
        self.btn_delete_rows = QPushButton("🗑️ Xóa dòng")
        self.btn_delete_rows.setToolTip("Xóa các dòng đã chọn")
        self.btn_delete_rows.clicked.connect(self._delete_selected_rows)
        cmp_btn_row.addWidget(self.btn_delete_rows)
        self.btn_detect_junk = QPushButton("🧹 Lọc trùng/rác")
        self.btn_detect_junk.setToolTip("Tìm dòng trùng lặp hoặc quá ngắn vô nghĩa → tô đỏ để bạn xóa")
        self.btn_detect_junk.clicked.connect(self._detect_junk_rows)
        cmp_btn_row.addWidget(self.btn_detect_junk)
        self.chk_auto_merge = QCheckBox("Tự động gộp")
        self.chk_auto_merge.setChecked(False)
        self.chk_auto_merge.setToolTip("Khi tích: bấm Lọc trùng sẽ tự gộp các dòng trùng lặp liền kề")
        self.chk_auto_merge.setStyleSheet("color:#e0e0e8;")
        cmp_btn_row.addWidget(self.chk_auto_merge)
        self.btn_undo_cmp = QPushButton("↩️ Undo")
        self.btn_undo_cmp.setToolTip("Hoàn tác thao tác cuối (Ctrl+Z)")
        self.btn_undo_cmp.clicked.connect(self._undo_cmp)
        cmp_btn_row.addWidget(self.btn_undo_cmp)
        self.btn_save_cmp_srt = QPushButton("💾 Lưu SRT")
        self.btn_save_cmp_srt.setToolTip("Lưu bảng hiện tại ra file SRT mới")
        self.btn_save_cmp_srt.clicked.connect(self._save_cmp_srt)
        cmp_btn_row.addWidget(self.btn_save_cmp_srt)
        cmp_btn_row.addStretch()
        cmp_lay.addLayout(cmp_btn_row)
        
        # Undo history stack
        self._cmp_undo_stack = []

        self.cmp_table = QTableWidget()
        self.cmp_table.setColumnCount(4)
        self.cmp_table.setHorizontalHeaderLabels(['#', 'Thời gian', 'Gốc (中文)', 'Dịch (Tiếng Việt)'])
        h = self.cmp_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.cmp_table.setColumnWidth(0, 45)
        self.cmp_table.setColumnWidth(1, 215)
        self.cmp_table.verticalHeader().setVisible(False)
        self.cmp_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cmp_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.cmp_table.setAlternatingRowColors(True)
        self.cmp_table.setWordWrap(True)
        self.cmp_table.setFont(QFont('Segoe UI', 10))
        h.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        cmp_lay.addWidget(self.cmp_table)

        self.cmp_stats = QLabel("")
        self.cmp_stats.setStyleSheet("color: #7880a0; padding: 2px;")
        cmp_lay.addWidget(self.cmp_stats)

        self.tabs.addTab(cmp_tab, "🔍 So Sánh")
        
        # Ctrl+Z shortcut cho undo
        from PyQt6.QtGui import QShortcut, QKeySequence
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self._undo_cmp)

        root.addWidget(self.tabs, 1)  # stretch=1 → chiếm hết phần còn lại
        self.setLayout(root)
        self._update_models()

    # ─────── Actions ───────
    def _open_settings(self):
        self.settings_win = SettingsDialog(self.dotenv_path)
        self.settings_win.setStyleSheet(DARK_STYLE)
        self.settings_win.show()

    def _update_models(self):
        self.model_combo.clear()
        if self.radio_gemini.isChecked():
            models = GEMINI_MODELS
        elif self.radio_grok.isChecked():
            models = GROK_MODELS
        else:
            models = OPENAI_MODELS
        self.model_combo.addItems(models)

    def _open_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Chọn file SRT", "", "SRT Files (*.srt)")
        if f:
            self.input_file_path = f
            self.file_path_edit.setText(f)
            self.btn_translate.setEnabled(True)
            self.btn_grammar.setEnabled(True)  # Bật nút sửa ngữ pháp ngay khi có file
            self.log_edit.append(f"\n📂 Đã chọn: {os.path.basename(f)}")
            self._load_preview(f)

    def _load_preview(self, filepath: str):
        """Đọc file SRT và hiển thị xem trước trong tab Preview."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.log_edit.append(f"❌ Không đọc được file: {e}")
            return

        blocks = split_srt_blocks(content)
        parsed = []
        for b in blocks:
            idx, ts, text_lines = parse_block(b)
            if idx and ts:
                text = ' '.join(l.strip() for l in text_lines)
                parsed.append((idx, ts, text))

        self.preview_table.setRowCount(len(parsed))
        for r, (idx, ts, text) in enumerate(parsed):
            self.preview_table.setItem(r, 0, QTableWidgetItem(str(idx)))
            self.preview_table.setItem(r, 1, QTableWidgetItem(ts))
            self.preview_table.setItem(r, 2, QTableWidgetItem(text))

        self.preview_table.resizeRowsToContents()
        self.preview_info.setText(f"📖 File: {os.path.basename(filepath)}")
        self.preview_stats.setText(f"Tổng: {len(parsed)} dòng phụ đề")
        self.tabs.setCurrentIndex(1)  # Chuyển sang tab Xem Trước
        self.log_edit.append(f"📖 Đã tải xem trước: {len(parsed)} dòng")

    def _on_tag_toggled(self, checked):
        """Hiện/ẩn video input khi toggle nhận diện nhân vật."""
        self.video_row.setVisible(checked)
    
    def _browse_video(self):
        """Chọn file video cho video-assisted tagging."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn video", "", "Video (*.mp4 *.mkv *.avi *.webm *.mov);;All (*.*)"
        )
        if path:
            self.video_path_edit.setText(path)

    def _start_translation(self):
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Thông báo", "Đang dịch, vui lòng đợi.")
            return

        self._set_controls(False)
        self.progress_bar.setValue(0)
        self.lbl_batch_info.setText("⏳ Đang khởi tạo...")
        self.log_edit.clear()
        self.tabs.setCurrentIndex(0)

        api = "gemini" if self.radio_gemini.isChecked() else ("grok" if self.radio_grok.isChecked() else "openai")
        # Đọc prompt từ settings hoặc file .env
        if self.settings_win:
            prompt = self.settings_win.get_prompt()
        else:
            try:
                from dotenv import dotenv_values
                prompt = dotenv_values(self.dotenv_path).get("CUSTOM_SYSTEM_PROMPT", "") or DEFAULT_SYSTEM_PROMPT
            except Exception:
                prompt = os.getenv("CUSTOM_SYSTEM_PROMPT", "") or DEFAULT_SYSTEM_PROMPT

        # Đa ngôn ngữ: thêm chỉ dẫn ngôn ngữ đích
        lang_names = {
            "vi": "tiếng Việt", "en": "English", "es": "Español (Spanish)",
            "pt": "Português (Portuguese)", "fr": "Français (French)", "de": "Deutsch (German)",
            "ru": "Русский (Russian)", "ar": "العربية (Arabic)", "hi": "हिन्दी (Hindi)",
            "ko": "한국어 (Korean)", "ja": "日本語 (Japanese)", "th": "ภาษาไทย (Thai)",
            "id": "Bahasa Indonesia", "ms": "Bahasa Melayu", "fil": "Filipino",
            "tr": "Türkçe (Turkish)"
        }
        target_lang = self.lang_combo.currentData() or "vi"
        target_lang_name = lang_names.get(target_lang, "tiếng Việt")
        if target_lang != "vi":
            prompt += (
                f"\n\n【NGÔN NGỮ ĐÍCH - GHI ĐÈ】\n"
                f"• DỊCH SANG {target_lang_name.upper()} thay vì tiếng Việt.\n"
                f"• Giữ tên riêng/thuật ngữ theo glossary, nhưng câu văn phải bằng {target_lang_name}.\n"
                f"• Output format: [số]|text {target_lang_name}"
            )

        self.log_edit.append(f"🚀 Dịch: {api.upper()} | {self.model_combo.currentText()}")
        self.log_edit.append(f"🌐 Ngôn ngữ: {target_lang_name}")
        glossary_path = self._get_current_glossary_path()
        glossary_name = self.glossary_combo.currentText() or DEFAULT_GLOSSARY
        self.log_edit.append(f"📄 File: {os.path.basename(self.input_file_path)}")
        self.log_edit.append(f"📖 Glossary: {glossary_name}")
        self.log_edit.append("━" * 40)

        # Lưu glossary đã chọn vào .env
        try:
            set_key(self.dotenv_path, "SELECTED_GLOSSARY", glossary_name, quote_mode="never")
        except Exception:
            pass

        self.thread = QThread()
        tag_chars = self.chk_tag_characters.isChecked()
        video_path = self.video_path_edit.text().strip() if tag_chars else None
        if tag_chars:
            self.log_edit.append("🎭 Nhận diện nhân vật nói: BẬT")
            if video_path and os.path.isfile(video_path):
                self.log_edit.append(f"🎬 Video-assisted: {os.path.basename(video_path)}")
            else:
                self.log_edit.append("  (Text-only mode, ~60-70% accuracy)")
        video_quality = self.video_quality_combo.currentData() if tag_chars else "original"
        self.worker = TranslationWorker(
            self.input_file_path, api, self.model_combo.currentText(), prompt,
            glossary_path=glossary_path, tag_characters=tag_chars,
            video_path=video_path, video_quality=video_quality
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self.log_edit.append)
        self.worker.update_progress_bar.connect(self.progress_bar.setValue)
        self.worker.batch_info.connect(self.lbl_batch_info.setText)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._on_thread_done)
        self.thread.start()

    def _on_thread_done(self):
        """Dọn dẹp thread khi hoàn tất để tránh crash."""
        if self.thread:
            self.thread.deleteLater()
        self.thread = None
        self.worker = None

    def _set_controls(self, enabled: bool):
        self.btn_translate.setEnabled(enabled)
        self.btn_file.setEnabled(enabled)
        self.btn_grammar.setEnabled(enabled and bool(self.input_file_path))
        self.radio_gemini.setEnabled(enabled)
        self.radio_openai.setEnabled(enabled)
        self.radio_grok.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.glossary_combo.setEnabled(enabled)
        self.btn_add_glossary.setEnabled(enabled)
        self.btn_remove_glossary.setEnabled(enabled)
        if enabled and not self.input_file_path:
            self.btn_translate.setEnabled(False)

    # ─────── Glossary Management ───────
    def _refresh_glossary_combo(self):
        """Cập nhật danh sách glossary trong ComboBox."""
        current = self.glossary_combo.currentText()
        self.glossary_combo.clear()
        files = get_glossary_files()
        for f in files:
            # Hiển thị tên đẹp hơn: thêm ★ cho mặc định
            display = f"★ {f}" if f == DEFAULT_GLOSSARY else f
            self.glossary_combo.addItem(display, f)  # userData = filename gốc
        
        # Khôi phục lựa chọn từ .env
        saved = self._read_env_value("SELECTED_GLOSSARY")
        if saved:
            idx = self.glossary_combo.findData(saved)
            if idx >= 0:
                self.glossary_combo.setCurrentIndex(idx)
        elif current:
            # Giữ lại lựa chọn trước đó
            idx = self.glossary_combo.findData(current)
            if idx >= 0:
                self.glossary_combo.setCurrentIndex(idx)

    def _read_env_value(self, key: str, default: str = "") -> str:
        """Doc giá trị từ .env file."""
        try:
            from dotenv import dotenv_values
            return dotenv_values(self.dotenv_path).get(key, default) or default
        except Exception:
            return os.getenv(key, default) or default

    def _get_current_glossary_path(self) -> str:
        """Lấy đường dẫn đầy đủ của glossary đang chọn."""
        filename = self.glossary_combo.currentData()
        if not filename:
            filename = DEFAULT_GLOSSARY
        return get_glossary_path(filename)

    def _add_glossary(self):
        """Thêm file glossary mới vào thư mục glossaries/."""
        f, _ = QFileDialog.getOpenFileName(
            self, "Chọn file Glossary", "", "JSON Files (*.json)"
        )
        if not f:
            return
        
        filename = os.path.basename(f)
        dest = get_glossary_path(filename)
        
        # Kiểm tra file đã tồn tại chưa
        if os.path.exists(dest):
            reply = QMessageBox.question(
                self, "File đã tồn tại",
                f"File '{filename}' đã có trong glossaries.\nGhi đè?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            # Kiểm tra file JSON hợp lệ
            with open(f, 'r', encoding='utf-8') as fh:
                json.load(fh)
            
            shutil.copy2(f, dest)
            self._refresh_glossary_combo()
            
            # Chọn file vừa thêm
            idx = self.glossary_combo.findData(filename)
            if idx >= 0:
                self.glossary_combo.setCurrentIndex(idx)
            
            self.log_edit.append(f"✅ Đã thêm glossary: {filename}")
            QMessageBox.information(self, "Thành công", f"Đã thêm glossary '{filename}'!")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Lỗi", f"File '{filename}' không phải JSON hợp lệ!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm glossary: {e}")

    def _remove_glossary(self):
        """Xóa glossary đang chọn (không cho xóa mặc định)."""
        filename = self.glossary_combo.currentData()
        if not filename:
            return
        
        if filename == DEFAULT_GLOSSARY:
            QMessageBox.warning(
                self, "Không thể xóa",
                f"'{DEFAULT_GLOSSARY}' là glossary mặc định, không thể xóa!"
            )
            return
        
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Xóa glossary '{filename}'?\nHành động này không thể hoàn tác!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            filepath = get_glossary_path(filename)
            os.remove(filepath)
            self._refresh_glossary_combo()
            self.log_edit.append(f"🗑 Đã xóa glossary: {filename}")
            QMessageBox.information(self, "Thành công", f"Đã xóa glossary '{filename}'!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa: {e}")

    def _on_finished(self, output_path: str):
        self.log_edit.append("\n✅ DỊCH HOÀN TẤT!")
        self.last_output_path = output_path
        self.btn_grammar.setEnabled(True)  # Bật nút sửa ngữ pháp
        self._set_controls(True)
        QMessageBox.information(self, "Thành công", f"Đã lưu tại:\n{output_path}")
        self._load_comparison(self.input_file_path, output_path)

    def _on_error(self, msg: str):
        self.log_edit.append(f"\n❌ LỖI: {msg}")
        self._set_controls(True)
        QMessageBox.critical(self, "Lỗi", f"Dịch thất bại:\n{msg}")

    def _start_grammar_fix(self):
        """Sửa ngữ pháp/OCR tiếng Trung trên file gốc, ghi đè và cập nhật preview."""
        target_file = self.input_file_path
        
        if not target_file or not os.path.exists(target_file):
            QMessageBox.warning(self, "Thông báo", "Chưa có file. Hãy chọn file SRT trước!")
            return

        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Thông báo", "Đang xử lý, vui lòng đợi.")
            return

        self._set_controls(False)
        self.progress_bar.setValue(0)
        self.log_edit.clear()
        self.tabs.setCurrentIndex(0)

        api = "gemini" if self.radio_gemini.isChecked() else ("grok" if self.radio_grok.isChecked() else "openai")
        self.log_edit.append(f"✏️ Sửa ngữ pháp tiếng Trung: {api.upper()} | {self.model_combo.currentText()}")
        self.log_edit.append(f"📄 File: {os.path.basename(target_file)}")
        self.log_edit.append("━" * 40)

        self.thread = QThread()
        self.grammar_worker = GrammarWorker(
            target_file, api, self.model_combo.currentText()
        )
        self.grammar_worker.moveToThread(self.thread)
        self.thread.started.connect(self.grammar_worker.run)
        self.grammar_worker.finished.connect(self._on_grammar_finished)
        self.grammar_worker.error.connect(self._on_error)
        self.grammar_worker.progress.connect(self.log_edit.append)
        self.grammar_worker.update_progress_bar.connect(self.progress_bar.setValue)
        self.grammar_worker.finished.connect(self.thread.quit)
        self.grammar_worker.finished.connect(self.grammar_worker.deleteLater)
        self.thread.finished.connect(self._on_thread_done)
        self.thread.start()

    def _on_grammar_finished(self, output_path: str):
        self.log_edit.append("\n✅ SỬA NGỮ PHÁP TIẾNG TRUNG HOÀN TẤT!")
        self.log_edit.append("📖 Đã cập nhật preview — xem lại trước khi dịch.")
        self._set_controls(True)
        self.btn_grammar.setEnabled(True)
        # Cập nhật preview để user xem lại text Trung đã sửa
        self._load_preview(output_path)
        QMessageBox.information(self, "Thành công", 
            "Đã sửa ngữ pháp tiếng Trung và cập nhật preview.\n"
            "Hãy xem lại rồi bấm Dịch khi sẵn sàng!")

    def _open_compare_dialog(self):
        f1, _ = QFileDialog.getOpenFileName(self, "Chọn file SRT gốc", "", "SRT Files (*.srt)")
        if not f1: return
        f2, _ = QFileDialog.getOpenFileName(self, "Chọn file SRT đã dịch", "", "SRT Files (*.srt)")
        if not f2: return
        self._load_comparison(f1, f2)

    def _load_comparison(self, orig_path: str, trans_path: str):
        """Đọc 2 file SRT → load vào bảng so sánh."""
        if not orig_path or not trans_path:
            return
        if not os.path.exists(orig_path) or not os.path.exists(trans_path):
            self.log_edit.append("⚠️ Không tìm thấy file.")
            return
        try:
            with open(orig_path, 'r', encoding='utf-8') as f:
                oc = f.read()
            with open(trans_path, 'r', encoding='utf-8') as f:
                tc = f.read()
        except Exception as e:
            self.log_edit.append(f"❌ Lỗi đọc file: {e}")
            return

        ob = split_srt_blocks(oc)
        tb = split_srt_blocks(tc)

        op = [(parse_block(b)[0] or '?', parse_block(b)[1] or '',
               ' '.join(l.strip() for l in parse_block(b)[2])) for b in ob]
        tp = [(parse_block(b)[0] or '?', parse_block(b)[1] or '',
               ' '.join(l.strip() for l in parse_block(b)[2])) for b in tb]

        t_map = {idx: txt for idx, _, txt in tp}
        mx = max(len(op), len(tp))
        self.cmp_table.setRowCount(mx)

        for r in range(mx):
            if r < len(op):
                idx, ts, otxt = op[r]
                ttxt = t_map.get(idx, '')
                if not ttxt and r < len(tp):
                    ttxt = tp[r][2]
            elif r < len(tp):
                idx, ts, otxt = tp[r][0], tp[r][1], ''
                ttxt = tp[r][2]
            else:
                continue
            # Cột #, Thời gian: chỉ đọc
            item_idx = QTableWidgetItem(str(idx))
            item_idx.setFlags(item_idx.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_ts = QTableWidgetItem(ts)
            item_ts.setFlags(item_ts.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.cmp_table.setItem(r, 0, item_idx)
            self.cmp_table.setItem(r, 1, item_ts)
            # Cột Gốc, Dịch: click để sửa
            self.cmp_table.setItem(r, 2, QTableWidgetItem(otxt))
            self.cmp_table.setItem(r, 3, QTableWidgetItem(ttxt))

        self.cmp_table.resizeRowsToContents()
        self.cmp_info.setText(
            f"📄 Gốc: {os.path.basename(orig_path)}  │  📄 Dịch: {os.path.basename(trans_path)}"
        )
        self.cmp_stats.setText(f"Gốc: {len(op)} dòng  │  Dịch: {len(tp)} dòng")
        self._cmp_trans_path = trans_path  # Lưu path để save
        self.tabs.setCurrentIndex(1)
        self.log_edit.append("🔍 Đã tải so sánh song ngữ.")

    def _merge_selected_rows(self):
        """Gộp các dòng đã chọn trong bảng so sánh: thời gian đầu + cuối, text gộp, renumber."""
        selected = sorted(set(idx.row() for idx in self.cmp_table.selectedIndexes()))
        if len(selected) < 2:
            QMessageBox.warning(self, "Gộp dòng", "Hãy chọn ít nhất 2 dòng liên tiếp để gộp.\n(Shift+Click để chọn nhiều dòng)")
            return
        self._save_cmp_snapshot()

        # Kiểm tra liên tiếp
        for i in range(1, len(selected)):
            if selected[i] != selected[i-1] + 1:
                QMessageBox.warning(self, "Gộp dòng", "Chỉ gộp được các dòng liên tiếp!\nHãy chọn lại.")
                return

        first_row = selected[0]
        last_row = selected[-1]

        # Lấy thời gian: start của dòng đầu + end của dòng cuối
        ts_first = (self.cmp_table.item(first_row, 1).text() or "").strip()
        ts_last = (self.cmp_table.item(last_row, 1).text() or "").strip()

        # Parse: "00:00:03,399 --> 00:00:04,399"
        start_time = ts_first.split('-->')[0].strip() if '-->' in ts_first else ts_first
        end_time = ts_last.split('-->')[1].strip() if '-->' in ts_last else ts_last
        merged_ts = f"{start_time} --> {end_time}"

        # Gộp text — nếu trùng ≥85% thì giữ dòng dài nhất, không nối
        from difflib import SequenceMatcher
        orig_parts = []
        trans_parts = []
        for r in selected:
            ot = (self.cmp_table.item(r, 2).text() or "").strip()
            tt = (self.cmp_table.item(r, 3).text() or "").strip()
            if ot: orig_parts.append(ot)
            if tt: trans_parts.append(tt)
        
        # Kiểm tra có phải dòng trùng lặp không
        all_similar_trans = len(trans_parts) >= 2
        for i in range(1, len(trans_parts)):
            if SequenceMatcher(None, trans_parts[0], trans_parts[i]).ratio() < 0.85:
                all_similar_trans = False
                break
        all_similar_orig = len(orig_parts) >= 2
        for i in range(1, len(orig_parts)):
            if SequenceMatcher(None, orig_parts[0], orig_parts[i]).ratio() < 0.85:
                all_similar_orig = False
                break
        
        if all_similar_trans:
            merged_trans = max(trans_parts, key=len)  # giữ dòng dài nhất
        else:
            merged_trans = ' '.join(trans_parts)
        if all_similar_orig:
            merged_orig = max(orig_parts, key=len)
        else:
            merged_orig = ' '.join(orig_parts)

        # Xóa các dòng thừa (từ cuối lên)
        for r in reversed(selected[1:]):
            self.cmp_table.removeRow(r)

        # Cập nhật dòng gộp
        self.cmp_table.setItem(first_row, 1, QTableWidgetItem(merged_ts))
        self.cmp_table.setItem(first_row, 2, QTableWidgetItem(merged_orig))
        self.cmp_table.setItem(first_row, 3, QTableWidgetItem(merged_trans))

        # Renumber tất cả STT
        for r in range(self.cmp_table.rowCount()):
            self.cmp_table.setItem(r, 0, QTableWidgetItem(str(r + 1)))

        self.cmp_table.resizeRowsToContents()
        merged_count = len(selected)
        total = self.cmp_table.rowCount()
        self.cmp_stats.setText(f"✅ Đã gộp {merged_count} dòng → 1 | Tổng: {total} dòng")
        self.log_edit.append(f"🔗 Gộp {merged_count} dòng (#{first_row+1}→#{last_row+1}) → dòng #{first_row+1}")

    def _save_cmp_srt(self):
        """Lưu bảng so sánh hiện tại ra file SRT (cột Dịch)."""
        rows = self.cmp_table.rowCount()
        if rows == 0:
            QMessageBox.warning(self, "Lưu SRT", "Bảng trống, không có gì để lưu.")
            return

        # Gợi ý path
        default_path = ""
        if hasattr(self, '_cmp_trans_path') and self._cmp_trans_path:
            base, ext = os.path.splitext(self._cmp_trans_path)
            default_path = f"{base}_edited{ext}"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu file SRT đã chỉnh sửa", default_path, "SRT Files (*.srt)"
        )
        if not save_path:
            return

        # Build SRT content từ bảng
        srt_lines = []
        for r in range(rows):
            idx = (self.cmp_table.item(r, 0).text() or str(r+1)).strip()
            ts = (self.cmp_table.item(r, 1).text() or "").strip()
            trans = (self.cmp_table.item(r, 3).text() or "").strip()
            if not ts or not trans:
                continue
            srt_lines.append(f"{idx}\n{ts}\n{trans}\n")

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_lines))

        self.log_edit.append(f"💾 Đã lưu SRT: {save_path}")
        QMessageBox.information(self, "Lưu SRT", f"Đã lưu {len(srt_lines)} dòng vào:\n{os.path.basename(save_path)}")

    # ====== UNDO / DELETE / DETECT JUNK ======
    def _save_cmp_snapshot(self):
        """Lưu snapshot toàn bộ bảng so sánh vào undo stack."""
        snapshot = []
        for r in range(self.cmp_table.rowCount()):
            row_data = []
            for c in range(self.cmp_table.columnCount()):
                item = self.cmp_table.item(r, c)
                text = item.text() if item else ""
                bg = item.background().color().name() if item and item.background().color().isValid() else ""
                row_data.append((text, bg))
            snapshot.append(row_data)
        self._cmp_undo_stack.append(snapshot)
        if len(self._cmp_undo_stack) > 20:
            self._cmp_undo_stack.pop(0)

    def _undo_cmp(self):
        """Hoàn tác thao tác cuối trong bảng so sánh."""
        if not self._cmp_undo_stack:
            QMessageBox.information(self, "Undo", "Không có gì để hoàn tác!")
            return
        snapshot = self._cmp_undo_stack.pop()
        self.cmp_table.setRowCount(len(snapshot))
        for r, row_data in enumerate(snapshot):
            for c, (text, bg) in enumerate(row_data):
                item = QTableWidgetItem(text)
                if c < 2:  # Cột # và Thời gian readonly
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if bg:
                    from PyQt6.QtGui import QColor
                    item.setBackground(QColor(bg))
                self.cmp_table.setItem(r, c, item)
        self.cmp_table.resizeRowsToContents()
        total = self.cmp_table.rowCount()
        self.cmp_stats.setText(f"↩️ Đã hoàn tác | Tổng: {total} dòng")
        self.log_edit.append(f"↩️ Undo thành công ({total} dòng)")

    def _delete_selected_rows(self):
        """Xóa các dòng đã chọn và renumber."""
        selected = sorted(set(idx.row() for idx in self.cmp_table.selectedIndexes()))
        if not selected:
            QMessageBox.warning(self, "Xóa dòng", "Hãy chọn ít nhất 1 dòng để xóa.")
            return
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Xóa {len(selected)} dòng đã chọn?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._save_cmp_snapshot()
        for r in reversed(selected):
            self.cmp_table.removeRow(r)
        # Renumber
        for r in range(self.cmp_table.rowCount()):
            item = QTableWidgetItem(str(r + 1))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.cmp_table.setItem(r, 0, item)
        self.cmp_table.resizeRowsToContents()
        total = self.cmp_table.rowCount()
        self.cmp_stats.setText(f"🗑️ Đã xóa {len(selected)} dòng | Tổng: {total} dòng")
        self.log_edit.append(f"🗑️ Xóa {len(selected)} dòng")

    def _detect_junk_rows(self):
        """Phát hiện dòng trùng lặp / quá ngắn → tô màu. Nếu tự động gộp → gộp luôn."""
        rows = self.cmp_table.rowCount()
        if rows == 0:
            QMessageBox.warning(self, "Lọc trùng", "Bảng trống!")
            return
        
        from PyQt6.QtGui import QColor
        from difflib import SequenceMatcher
        junk_count = 0
        dup_count = 0
        dup_rows = []  # danh sách dòng trùng để auto-merge
        
        # Reset màu nền trước
        for r in range(rows):
            for c in range(self.cmp_table.columnCount()):
                item = self.cmp_table.item(r, c)
                if item:
                    item.setBackground(QColor(0, 0, 0, 0))
        
        for r in range(rows):
            trans_item = self.cmp_table.item(r, 3)
            trans = trans_item.text().strip() if trans_item else ""
            
            is_junk = False
            
            # Dòng quá ngắn vô nghĩa (< 2 ký tự sau khi bỏ dấu)
            clean_trans = ''.join(c for c in trans if c.isalnum())
            if len(clean_trans) < 2 and trans:
                for c in range(self.cmp_table.columnCount()):
                    item = self.cmp_table.item(r, c)
                    if item:
                        item.setBackground(QColor(255, 165, 0, 80))
                junk_count += 1
                is_junk = True
            
            # Dòng trùng lặp LIÊN TIẾP (giống ≥85% với dòng trước)
            if trans and not is_junk and r > 0:
                prev_item = self.cmp_table.item(r - 1, 3)
                prev_trans = prev_item.text().strip() if prev_item else ""
                if prev_trans:
                    ratio = SequenceMatcher(None, trans, prev_trans).ratio()
                    if ratio >= 0.85:
                        for c in range(self.cmp_table.columnCount()):
                            item = self.cmp_table.item(r, c)
                            if item:
                                item.setBackground(QColor(255, 80, 80, 80))
                        dup_count += 1
                        dup_rows.append(r)
        
        total_found = junk_count + dup_count
        
        # Nếu checkbox tự động gộp được tích → gộp các dòng trùng
        auto_merged = 0
        if self.chk_auto_merge.isChecked() and dup_rows:
            self._save_cmp_snapshot()
            # Gộp từ cuối lên (để index không bị lệch)
            for dup_r in reversed(dup_rows):
                prev_r = dup_r - 1
                if prev_r < 0:
                    continue
                # Lấy thời gian: start dòng trên + end dòng dưới
                ts_prev = (self.cmp_table.item(prev_r, 1).text() or "").strip()
                ts_dup = (self.cmp_table.item(dup_r, 1).text() or "").strip()
                start_t = ts_prev.split('-->')[0].strip() if '-->' in ts_prev else ts_prev
                end_t = ts_dup.split('-->')[1].strip() if '-->' in ts_dup else ts_dup
                merged_ts = f"{start_t} --> {end_t}"
                # Giữ text dòng dài hơn
                prev_trans = (self.cmp_table.item(prev_r, 3).text() or "").strip()
                dup_trans = (self.cmp_table.item(dup_r, 3).text() or "").strip()
                keep_trans = prev_trans if len(prev_trans) >= len(dup_trans) else dup_trans
                prev_orig = (self.cmp_table.item(prev_r, 2).text() or "").strip()
                dup_orig = (self.cmp_table.item(dup_r, 2).text() or "").strip()
                keep_orig = prev_orig if len(prev_orig) >= len(dup_orig) else dup_orig
                # Cập nhật dòng trên, xóa dòng dưới
                self.cmp_table.setItem(prev_r, 1, QTableWidgetItem(merged_ts))
                self.cmp_table.setItem(prev_r, 2, QTableWidgetItem(keep_orig))
                self.cmp_table.setItem(prev_r, 3, QTableWidgetItem(keep_trans))
                self.cmp_table.removeRow(dup_r)
                auto_merged += 1
            # Renumber
            for r in range(self.cmp_table.rowCount()):
                self.cmp_table.setItem(r, 0, QTableWidgetItem(str(r + 1)))
            self.cmp_table.resizeRowsToContents()
        
        if total_found == 0:
            QMessageBox.information(self, "🧹 Lọc trùng/rác", "✅ Không phát hiện dòng trùng hay rác nào!")
        elif auto_merged > 0:
            msg = f"✅ Đã tự động gộp {auto_merged} dòng trùng lặp!\n"
            if junk_count > 0:
                msg += f"🟠 Còn {junk_count} dòng quá ngắn/rác (cam) → chọn xóa thủ công."
            msg += f"\nTổng còn: {self.cmp_table.rowCount()} dòng."
            QMessageBox.information(self, "🧹 Lọc trùng/rác", msg)
        else:
            msg = f"Phát hiện {total_found} dòng nghi vấn:\n"
            if dup_count > 0:
                msg += f"  🔴 {dup_count} dòng trùng lặp (đỏ)\n"
            if junk_count > 0:
                msg += f"  🟠 {junk_count} dòng quá ngắn/rác (cam)\n"
            msg += "\nChọn các dòng tô màu → bấm 🗑️ Xóa dòng hoặc 🔗 Gộp."
            QMessageBox.information(self, "🧹 Lọc trùng/rác", msg)
        
        self.cmp_stats.setText(f"🧹 Trùng: {dup_count} | Rác: {junk_count} | Tự gộp: {auto_merged}")

    def closeEvent(self, event):
        try:
            if self.thread is not None and self.thread.isRunning():
                reply = QMessageBox.question(self, 'Thoát?', "Đang dịch, dừng lại?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    if self.worker:
                        self.worker.is_running = False
                    self.thread.quit()
                    self.thread.wait(2000)
                    event.accept()
                else:
                    event.ignore()
                    return
        except RuntimeError:
            pass  # QThread đã bị xóa, bỏ qua
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    ex = TranslatorApp()
    ex.show()
    sys.exit(app.exec())