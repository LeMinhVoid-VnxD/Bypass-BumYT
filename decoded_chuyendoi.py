#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import time
import srt
import requests
import subprocess
import json
import shutil
import base64
import threading
import concurrent.futures
import tempfile
import uuid
import hashlib
from datetime import timedelta
from typing import List

# --- Cài đặt thư viện: pip install PyQt6 srt requests playsound==1.2.2 ---
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QTextEdit, QProgressBar, QGroupBox,
    QMessageBox, QFormLayout, QComboBox, QStackedWidget, QCheckBox, QSlider,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import QThread, QObject, pyqtSignal, Qt, QSettings, QEvent


class WheelGuard(QObject):
    """Event filter: chặn wheel event trên ComboBox/Slider/SpinBox để tránh đổi giá trị khi scroll."""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if isinstance(obj, (QComboBox, QSlider)):
                event.ignore()
                return True  # Block wheel
        return super().eventFilter(obj, event)


# ================== DANH SÁCH GIỌNG ĐỌC TIKTOK ==================
TIKTOK_VOICES = {
    # Vietnamese
    'Vietnamese Female': 'BV074_streaming',
    'Vietnamese Male': 'BV075_streaming',
    # English
    'Game On': 'en_male_jomboy', 'Jessie': 'en_us_002', 'Warm': 'es_mx_002',
    'Wacky': 'en_male_funny', 'Scream': 'en_us_ghostface', 'Empathetic': 'en_us_female_samc',
    'Serious': 'en_male_cody', 'Beauty Guru': 'en_female_makeup', 'Bestie': 'en_female_richgirl',
    'Trickster': 'en_male_grinch', 'Joey': 'en_us_006', 'Story Teller': 'en_male_narration',
    'Mr. GoodGuy': 'en_male_deadpool', 'Narrator': 'en_uk_001', 'Male English UK': 'en_au_001',
    'Metro': 'en_au_001', 'Alfred': 'en_male_jarvis', 'ashmagic': 'en_male_ashmagic',
    'olantekkers': 'en_male_olantekkers', 'Lord Cringe': 'en_male_ukneighbor',
    'Mr. Meticulous': 'en_male_ukbutler', 'Debutante': 'en_female_shenna', 'Varsity': 'en_female_pansino',
    'Marty': 'en_male_trevor', 'Pop Lullaby': 'en_female_f08_twinkle', 'Classic Electric': 'en_male_m03_classical',
    'Bae': 'en_female_betty', 'Cupid': 'en_male_cupid', 'Granny': 'en_female_grandma',
    'Cozy': 'en_male_m2_xhxs_m03_christmas', 'Author': 'en_male_santa_narration',
    'Caroler': 'en_male_sing_deep_jingle', 'Santa': 'en_male_santa_effect', 'NYE 2023': 'en_female_ht_f08_newyear',
    'Magician': 'en_male_wizard', 'Opera': 'en_female_ht_f08_halloween', 'Euphoric': 'en_female_ht_f08_glorious',
    'Hypetrain': 'en_male_sing_funny_it_goes_up', 'Melodrama': 'en_female_ht_f08_wonderful_world',
    'Quirky Time': 'en_male_m2_xhxs_m03_silly', 'Peaceful': 'en_female_emotional', 'Toon Beat': 'en_male_m03_sunshine_soon',
    'Open Mic': 'en_female_f08_warmy_breeze', 'Jingle': 'en_male_m03_lobby', 'Thanksgiving': 'en_male_sing_funny_thanksgiving',
    'Cottagecore': 'en_female_f08_salut_damour', 'Professor': 'en_us_007', 'Scientist': 'en_us_009',
    'Confidence': 'en_us_010', 'Smooth': 'en_au_002'
}

# ================== DANH SÁCH GIỌNG ĐỌC FPT AI ==================
FPT_VOICES = {
    'Ban Mai (Nữ Bắc)': 'banmai',
    'Lan Nhi (Nữ Nam)': 'lannhi',
    'Lê Minh (Nam Bắc)': 'leminh',
    'My An (Nữ Trung)': 'myan',
    'Thu Minh (Nữ Bắc)': 'thuminh',
    'Gia Huy (Nam Trung)': 'giahuy',
    'Linh San (Nữ Nam)': 'linhsan',
}

# ================== DANH SÁCH GIỌNG ĐỌC ELEVENLABS (Tiếng Việt) ==================
ELEVENLABS_VOICES_VI = {
    # ── 🔵 NAM - GIỌNG BẮC ──
    'Tuấn Anh - Trầm, Kể chuyện (Nam Bắc)': 'HG0MlJIknmaXREpTckfK',
    'Tony Nguyễn - Trung niên (Nam Bắc)': '2ZUpiKo5wCCuypvx2zaS',
    'Nhật - Kể chuyện, Tin tức (Nam Bắc)': '6adFm46eyy74snVn6YrT',
    'Huy - Trầm, Đáng tin (Nam Bắc)': 'z9AwTVuN8C7iJ75jitEW',
    'Huy Lê - Rõ ràng, Giáo dục (Nam Bắc)': 'eZ248pfac00g3092s7h8',
    'Quang Nguyễn - Ấm, Năng động (Nam Bắc)': 'KVzG2JMdZJKi6y7cwERP',
    'Thai - Trầm, Trang trọng (Nam Bắc)': 'xVv8qLTTnsYnrysc2Lx4',
    'Hoàng Đặng - Trầm, Storytelling (Nam Bắc)': 'ipTvfDXAg1zowfF1rv9w',
    'Anh - Ấm, Trầm (Nam Bắc)': 'ywBZEqUhld86Jeajq94o',
    'Ninh Đôn - Trầm, Ấm (Nam Bắc)': 'aN7cv9yXNrfIR87bDmyD',
    'Cường Phạm - Trầm, Mạnh mẽ (Nam Bắc)': 'mTMLdrFZdBqiPUW1W47D',
    'Nhật Phong - Podcast, Ấm (Nam Bắc)': 'RxhjHDfpO54FYotYtKpw',
    'Lời - Rõ ràng, Tin tức (Nam Bắc)': 'OZ41k7uYyV1AwlxmkRx0',
    'Huy Bùi - Vững vàng, Kể chuyện (Nam Bắc)': 'VkftF4RyfVI5yIYa6wFa',
    'Dũng - Thơ mộng, Quảng cáo (Nam Bắc)': 'BUPPIXeDaJWBz696iXRS',
    'Liam - Ấm, Trò chuyện (Nam Bắc)': '7XOKiK112QRZRSLbCfMc',
    'Tùng Đặng - Trầm, Ấm (Nam Bắc)': '3VnrjnYrskPMDsapTr8X',
    'Ngọc (Nam) - Trầm, Đọc sách (Nam Bắc)': 'pFEtwO9FWuRIINWTs00y',
    # ── 🟢 NAM - GIỌNG TRUNG ──
    'Minh - Ấm, Giáo dục (Nam Trung)': 'IZKDEBDVLx4BnFc8W03D',
    'Trung Caha - Tin tức, Kể chuyện (Nam Trung)': 'FfC8yOt3HaUlZaet6DPx',
    'Hoàng - Vững vàng, Tự tin (Nam Trung)': 'cvguG4SQfZYZ0wHQTNLF',
    'Gia - Quảng cáo, Chuyên nghiệp (Nam Trung)': 'h7K5CmpgjUpbfD1vi7Zz',
    'Vinh - Ấm, Quảng cáo (Nam Trung)': 'FSA98p0BgnTAzCpH8avM',
    'Quân - Ấm, Giáo dục (Nam Trung)': 'puBBfOSRT9Dbk3FUJQGd',
    'Quy - Ấm, Hội An (Nam Trung)': '5DIp7NodzHK1ZgA68hss',
    'Nathan - Nhẹ nhàng, MXH (Nam Trung)': 'u8EWWYyBDfXFxHak7WM3',
    'Hợp Lê - Rõ ràng, Diễn cảm (Nam Trung)': '9w5lSVhu8VnBEqFqdrD9',
    'Kỳ Nguyên - Trầm, Kể chuyện (Nam Trung)': 'GdbrbFjAI4wKg8XPPRWg',
    'William - Trang trọng, Trò chuyện (Nam Trung)': 'jydR2VHYWfW6Yi35URqJ',
    'Ethan - Rõ ràng, Miền Trung (Nam Trung)': 'EcENCamMHdzIoMysqdsv',
    # ── 🟡 NAM - GIỌNG NAM ──
    'Hoàng Tỏi - Tự nhiên, MXH (Nam Nam)': 'fNukeGpfmYBkfd1Fj43Y',
    'Xuân Hi - Ấm, Cảm xúc (Nam Nam)': 'TSQmL8GUTyX83rgaewuP',
    'Lâm - Ấm, Kể chuyện (Nam Nam)': 'VAzxBZgjAoy5WCeMEmFW',
    'Trúc Lâm - Vui vẻ, Kể chuyện (Nam Nam)': '9RpzPSAZdsH0F8tpXfP4',
    'Trần Thành - Trung niên, Nhẹ nhàng (Nam Nam)': 'kPNz4WRTiKDplS7jAwHu',
    'Thanh - Trầm, Giáo dục (Nam Nam)': 'oLR5l8TbWm0sNc5LspDA',
    'Max - Rõ ràng, Podcast (Nam Nam)': 'EUVwmLU6voiyIbWsrs8V',
    'Triệu Dương - Trầm, Kể chuyện (Nam Nam)': 'UsgbMVmY3U59ijwK5mdh',
    'Hùng - Rõ ràng, Trò chuyện (Nam Nam)': 'DTLhW2kDOWq9IAPipCcu',
    'Sang Lê - Ấm, Cảm xúc (Nam Nam)': 'JDbnZf9C4zfUzF0EuIch',
    'Phước - Ấm, Kể chuyện (Nam Nam)': '7clfgAuss1M0JUYGlh1t',
    'Triết Ngô - Tự tin, Kể chuyện (Nam Nam)': 'TIQkE9DDukawEm00ejgd',
    'Khánh - Năng động, Trò chuyện (Nam Nam)': 'JYT6xPLD3LGl0ui3YXNq',
    'Phi - Ấm, Sài Gòn (Nam Nam)': 'QtiWG8SzdwWbDkee1llf',
    # ── 🔵 NAM - GIỌNG CHUẨN ──
    'Tuấn - Quảng cáo, Nhẹ nhàng (Nam)': 'In8K4JDLu1r9fGysc64F',
    'Quyến Rũ - Quyến rũ, Kể chuyện (Nam)': 'f966mdF5njWREvreUG07',
    'Zenson - Rõ ràng, Tự tin (Nam)': 'hfQXFFMygx7xoaljt9aE',
    'Owen - Trầm, Kể chuyện (Nam)': 'rBPOXJ1BAFm78yP1UmBB',
    'Rin Đình - Trầm, Ấm (Nam)': 'N8ES35RJ1GXQGHhdiimy',
    'Phương (BS) - Ấm, Trò chuyện (Nam)': 'MqsnLOwcpkRUz9a4AhNi',
    'Xuân Toàn - Rõ ràng, Kể chuyện (Nam)': 'ux9eagR6pSyxgfunaGxo',
    'Huynh Dương - Mạnh mẽ, Tự tin (Nam)': '6DozafBK77YWCkMMr2Ok',
    'Quốc - Ấm, Diễn cảm (Nam)': 'Y4Dv8VW6IGIXAJ67HiEv',
    'Kyle - Ấm, Cảm xúc (Nam)': '4a9d2yNlrzn6YEoy5ZWT',
    'Tanny - Ấm, Kể chuyện (Nam)': 'mwLufM1J13N37It93eQN',
    'Luci - Tin tức, Giáo dục (Nam)': 'Wzj3w9OuQFcoiuKPnk3j',
    'Tim - Trầm, Truyền cảm hứng (Nam)': 'QU8w26MMkEgMWCbCiebE',
    'Linh (Nam) - Rõ ràng, Giáo dục (Nam)': 'jdCnxs34TN80uQ8DRnGR',
    # ── 🔴 NỮ - GIỌNG BẮC ──
    'Thắm - Nhẹ nhàng, Ấm (Nữ Bắc)': '0ggMuQ1r9f9jqBu50nJn',
    'Trang - Ấm, Truyền cảm hứng (Nữ Bắc)': 'ArosID24mP18TEiQpNhs',
    'Hiền - Ấm, MC Tin tức (Nữ Bắc)': 'jdlxsPOZOHdGEfcItXVu',
    'Freya - Nhẹ nhàng, Kể chuyện (Nữ Bắc)': 'rXOGzMiqbmjugMpzKMEx',
    'Thảo - Nhẹ nhàng, TVC (Nữ Bắc)': '558B1EcdabtcSdleer40',
    'Trinh - Sáng, Đọc truyện (Nữ Bắc)': 'KpzB5RgCRuVkUlZeY6wb',
    'Viên - Ấm, Đọc sách (Nữ Bắc)': 'iSFxP4Z6YNcx9OXl62Ic',
    # ── 🟣 NỮ - GIỌNG TRUNG ──
    'Ngọc An - Ấm, Audiobook (Nữ Trung)': 'D0dFzCacaMgMGjIksFuH',
    'Ngân - Dễ thương, MXH (Nữ Trung)': 'a3AkyqGG4v8Pg7SWQ0Y3',
    'Bảo - Nhẹ nhàng, Quảng cáo (Nữ Trung)': 'zRKf3RQpAJq11rSezsxD',
    'Linh (Nữ) - Nhẹ nhàng, Quảng cáo (Nữ Trung)': 'L5c6tGA8OiORYKxez5Zu',
    'Hương - Nhẹ nhàng, MC (Nữ Trung)': 'q6uIUrmSRksEvUMlwYPR',
    'Duyên - Sáng, Kể chuyện (Nữ Trung)': 'DVQIYWzpAqd5qcoIlirg',
    'Trần - Nhẹ nhàng, Kể chuyện (Nữ Trung)': 'MfnRBJHBrGwMSVFTatjK',
    'Phương (Nữ) - Mượt mà, Quảng cáo (Nữ Trung)': 'deC6NEXcbavaVWbzjgzb',
    'Ngọc (Nữ) - Nhẹ nhàng, Giáo dục (Nữ Trung)': 'Y3DoBhgPgHh29oMNUEDk',
    'Nguyễn - Rõ ràng, Quảng cáo (Nữ Trung)': 'eqMFh4kWVrmjm0Bcil6E',
    'Duyên (QN) - Nhẹ nhàng, MXH (Nữ Trung)': '1rqNHUqUbBGpY3OyzPMI',
    'Zara - Ấm, Đà Nẵng (Nữ Trung)': 'QocxxnxEa0x8mrL2d4VT',
    'My - Nhẹ nhàng, Kể chuyện (Nữ Trung)': 'RmcV9cAq1TByxNSgbii7',
    # ── 🟠 NỮ - GIỌNG NAM ──
    'HTN - Ấm, Giáo dục (Nữ Nam)': 's06eec3OqspIDuOznMK4',
    'Tiểu Hồng - Trầm, Đọc sách (Nữ Nam)': '0xI4eT7fHnn6AHTfF4Ro',
    'Hoa - Mượt mà, Kể chuyện (Nữ Nam)': '5g2DMFQF8xR0KmnuNr4U',
    'Thanh (Nữ) - Rõ ràng, Đọc sách (Nữ Nam)': 'N0Z0aL8qHhzwUHwRBcVo',
    'Nari - Sáng, Trẻ trung (Nữ Nam)': 'yS7aiYdIV6YnJ3ZFcQZA',
    'Nam - Nhẹ nhàng, Kể chuyện (Nữ Nam)': '0eXHGNoETNSO4IGTBKno',
    'Giang - Ấm, Tự tin (Nữ Nam)': 'X0V9HEDEuaVhVqzVPUKM',
    # ── 🔵 NỮ - GIỌNG CHUẨN ──
    'Anna Thu - Ấm, Trò chuyện (Nữ)': 'P37gHF6iLTEvs2pLYhyv',
    'Kiều Linh - Tự tin, Quảng cáo (Nữ)': 'qByVAGjXwGlkcRDJoiHg',
    'Tâm Nguyên - Đọc truyện cổ tích (Nữ)': 'IovBBFnLZ6QzJhFLLroy',
    'Kênh - Trẻ, Kể chuyện (Nữ)': '5vqV9IG7sDpzgzKOIZAv',
    'Quỳnh Anh - MC, MXH (Nữ)': 'Si3s1VCb7dLbeqH57kiC',
    'Nguyệt - Rõ ràng, Hà Nội (Nữ)': 'oAvm5cbNCsMTdnhtmIs4',
    'Như - Nhẹ nhàng, Giáo dục (Nữ)': 'A5w1fw5x0uXded1LDvZp',
    'Mai - Tự nhiên, Hà Nội (Nữ)': 'd5HVupAWCwe4e6GvMCAL',
    'Emma - Nhẹ nhàng, Trưởng thành (Nữ)': 'oN0q7mZB5kootbGrbqix',
    'Lily - Mượt mà, Nhẹ nhàng (Nữ)': 'Sd0vUjtPZLtmojfIMHMx',
    'Huyền - Tự tin, Kể chuyện (Nữ)': 'eMZSaad4tZC98eLRlyKT',
    'Ngân Nguyễn - Sáng, Truyền cảm hứng (Nữ)': 'DvG3I1kDzdBY3u4EzYh6',
    'Mai Hoàng - Hoạt bát, Trò chuyện (Nữ)': 'szlbmCOTZzG1seZ82nZs',
    'Dahlia - Rõ ràng, Kể chuyện (Nữ)': 'BLeuF5fPXWSDAwZScbTY',
    'Ly - MC, Kể chuyện (Nữ)': 'HQZkBNMmZF5aISnrU842',
}

# ================== DANH SÁCH GIỌNG ĐỌC ELEVENLABS (English - Premade) ==================
ELEVENLABS_VOICES_EN = {
    # ── 🔵 MALE ──
    'Roger - Laid-Back, Casual (Male US)': 'CwhRBWXzGAHq8TQ4Fs17',
    'Charlie - Deep, Confident (Male AU)': 'IKne3meq5aSn9XLyUdCD',
    'George - Warm, Storyteller (Male UK)': 'JBFqnCBsd6RMkjVDRZzb',
    'Callum - Husky Trickster (Male US)': 'N2lVS1w4EtoT3dr4eOWO',
    'Harry - Fierce Warrior (Male US)': 'SOYHLrjzK2X1ezoPC6cr',
    'Liam - Energetic, Social Media (Male US)': 'TX3LPaxmHKxFdv7VOQHJ',
    'Will - Relaxed Optimist (Male US)': 'bIHbv24MWmeRgasZH58o',
    'Eric - Smooth, Trustworthy (Male US)': 'cjVigY5qzO86Huf0OWal',
    'Chris - Charming, Down-to-Earth (Male US)': 'iP95p4xoKVk53GoZ742B',
    'Brian - Deep, Comforting (Male US)': 'nPczCjzI2devNBz1zQrb',
    'Daniel - Steady Broadcaster (Male UK)': 'onwK4e9ZLuTAKqWW03F9',
    'Adam - Dominant, Firm (Male US)': 'pNInz6obpgDQGcFmaJgB',
    'Bill - Wise, Mature (Male US)': 'pqHfZKP75CvOlQylNhV4',
    # ── 🔴 FEMALE ──
    'Sarah - Mature, Confident (Female US)': 'EXAVITQu4vr4xnSDxMaL',
    'Laura - Enthusiast, Quirky (Female US)': 'FGY2WhTYpPnrIDTdsKH5',
    'Alice - Clear, Educator (Female UK)': 'Xb7hH8MSUJpSbSDYk0k2',
    'Matilda - Professional (Female US)': 'XrExE9yKIg1WjnnlVkGX',
    'Jessica - Playful, Bright (Female US)': 'cgSgspJ2msm6clMCkdW9',
    'Bella - Professional, Warm (Female US)': 'hpp4J3VqNfWAUOO0d1Us',
    'Lily - Velvety Actress (Female UK)': 'pFZP5JQG7iQjIQuC4Bku',
    # ── ⚪ NEUTRAL ──
    'River - Relaxed, Informative (Neutral)': 'SAz9YHcvj6GT2YYXdXww',
}

# ================== LỚP WORKER XỬ LÝ TÁC VỤ NỀN ==================
class ConversionWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    MAX_WORKERS = 15  # Default, sẽ được override từ config

    def __init__(self, srt_path: str, output_path: str, config: dict):
        super().__init__()
        self.srt_path = srt_path
        self.output_path = output_path
        self.config = config
        self.MAX_WORKERS = config.get('max_workers', 15)
        self.is_running = True
        self.completed_count = 0
        self.lock = threading.Lock()
        self.slow_segments = []  # Theo dõi các segment audio dài hơn SRT slot
        self._session_counter = 0  # Round-robin counter cho nhiều TikTok session IDs

    def stop(self):
        self.is_running = False

    def _process_segment(self, sub: srt.Subtitle, idx: int, total_subs: int):
        if not self.is_running:
            return None

        seg_wav = os.path.join(self.temp_dir, f"seg_{idx:04d}.wav")
        
        if os.path.exists(seg_wav):
            self._update_progress(total_subs, f"-> Đã có file seg_{idx:04d}.wav, bỏ qua.")
            return None

        text = sub.content.replace('\n', ' ').strip()
        
        # === Auto-Punctuation: Ngắt giọng tự nhiên ===
        # Nếu đoạn phụ đề không kết thúc bằng dấu câu, tự chèn dấu chấm (.)
        # để ép AI đọc thả tone chậm rãi về cuối thay vì giật cục.
        if text and text[-1] not in '.。,，!！?？;；:：…、》」』)）】〉':
            text = text + '.'
        
        # === Chế độ lồng tiếng đa giọng: parse tag {Tên NV} ===
        voice_override = None
        provider_override = None
        dubbing_mode = self.config.get('dubbing_mode', False)
        if dubbing_mode:
            tag_match = re.match(r'\{(.+?)\}\s*(.+)', text)
            if tag_match:
                char_name = tag_match.group(1).strip()
                text = tag_match.group(2).strip()  # Bỏ tag, chỉ giữ text
                voice_mapping = self.config.get('voice_mapping', {})
                char_info = voice_mapping.get(char_name, {})
                if isinstance(char_info, dict) and 'voice_id' in char_info:
                    voice_override = char_info['voice_id']
                    provider_override = char_info.get('provider', None)
                elif isinstance(char_info, str):
                    voice_override = char_info  # backward compat
            # Nếu không có tag hoặc tên không trong mapping → dùng default
            if not voice_override:
                voice_override = self.config.get('dubbing_default_voice', None)
        
        if not text:
            self._update_progress(total_subs, f"-> Phụ đề {idx} rỗng, bỏ qua.")
            return None

        try:
            audio_content = None
            provider = provider_override if provider_override else self.config.get('provider')

            # Thử tối đa 2 lần ở level segment
            for seg_attempt in range(2):
                if provider == 'FPT AI':
                    fpt_voice = voice_override if (dubbing_mode and voice_override) else self.config.get('fpt_voice', 'banmai')
                    audio_content = self._call_fpt_api(text, self.config['fpt_api_key'], fpt_voice)
                elif provider == 'ElevenLabs':
                    if dubbing_mode and voice_override:
                        voice_id = voice_override
                    else:
                        voice_id = self.config.get('elevenlabs_voice_id', '')
                        custom_id = self.config.get('elevenlabs_custom_voice_id', '').strip()
                        if custom_id:
                            voice_id = custom_id
                    audio_content = self._call_elevenlabs_api(text, self.config['elevenlabs_api_key'], voice_id)
                elif provider == 'TikTok TTS':
                    # Hỗ trợ nhiều session ID (phân tách bằng dấu phẩy) — round-robin
                    raw_sessions = self.config.get('tiktok_session_id', '')
                    session_list = [s.strip() for s in raw_sessions.split(',') if s.strip()]
                    if session_list:
                        with self.lock:
                            sid = session_list[self._session_counter % len(session_list)]
                            self._session_counter += 1
                    else:
                        sid = raw_sessions.strip()
                    audio_content = self._call_tiktok_api(text, sid, voice_override if (dubbing_mode and voice_override) else self.config['tiktok_voice'])

                if audio_content:
                    break
                if seg_attempt == 0:
                    self.progress.emit(0, f"-> Retry segment {idx} sau 2s...")
                    time.sleep(2)

            if audio_content:
                # Lưu MP3 tạm từ API
                tmp_mp3 = os.path.join(self.temp_dir, f"seg_{idx:04d}_raw.mp3")
                with open(tmp_mp3, 'wb') as f_out:
                    f_out.write(audio_content)
                # Decode sang WAV ngay lập tức (sample-accurate)
                self._decode_to_wav(tmp_mp3, seg_wav, self.config['ffmpeg_path'])
                # Xóa file MP3 tạm
                try:
                    os.remove(tmp_mp3)
                except Exception:
                    pass
                # === Audio Silence Padding: Chống cắt xén ===
                # Nối thêm 100ms khoảng lặng vào đuôi mọi file âm thanh
                # để khi đưa vào CapCut/Premiere không bị cắt mất chữ cuối.
                self._pad_silence_tail(seg_wav, pad_ms=100)
                # Áp dụng tốc độ đọc (nếu khác 1.0x)
                speed_factor = self.config.get('speed_factor', 1.0)
                if abs(speed_factor - 1.0) > 0.01:
                    self._apply_speed(seg_wav, speed_factor, self.config['ffmpeg_path'])
                # Điều chỉnh duration trên WAV
                self._adjust_duration(seg_wav, sub, self.config['ffmpeg_path'], self.config['ffprobe_path'], self.temp_dir)
                self._update_progress(total_subs, f"-> Tạo thành công seg_{idx:04d}.wav")
                return None
            else:
                self._update_progress(total_subs, f"-> ⚠️ Lỗi khi tạo seg_{idx:04d}.")
                return idx
        except Exception as e:
            self._update_progress(total_subs, f"-> ⚠️ Lỗi nghiêm trọng seg_{idx:04d}: {e}")
            return idx

    def _update_progress(self, total_subs: int, message: str):
        with self.lock:
            self.completed_count += 1
            percentage = int(self.completed_count / total_subs * 100)
            self.progress.emit(percentage, message)
    
    def run(self):
        try:
            FFMPEG_BIN = self.config.get('ffmpeg_path')
            if not FFMPEG_BIN or not os.path.exists(FFMPEG_BIN):
                raise FileNotFoundError(f"Không tìm thấy FFmpeg tại: {FFMPEG_BIN}")

            FFPROBE_BIN = os.path.join(os.path.dirname(FFMPEG_BIN), 'ffprobe.exe')
            self.config['ffprobe_path'] = FFPROBE_BIN
            # Dùng thư mục temp trong thư mục chứa file script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            TEMP_DIR = os.path.join(script_dir, 'temp')
            # Xóa sạch thư mục temp cũ nếu có
            if os.path.exists(TEMP_DIR):
                try:
                    shutil.rmtree(TEMP_DIR)
                except Exception:
                    pass
            os.makedirs(TEMP_DIR, exist_ok=True)
            self.temp_dir = TEMP_DIR
            # Đảm bảo output path là absolute
            if not os.path.isabs(self.output_path):
                self.output_path = os.path.join(script_dir, self.output_path)
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            self.progress.emit(0, f"Thư mục tạm: {TEMP_DIR}")
            
            with open(self.srt_path, encoding='utf-8') as f:
                subs = list(srt.parse(f.read()))
            if not subs:
                raise ValueError("File SRT rỗng hoặc không hợp lệ.")

            total_subs = len(subs)
            failed_indices = []
            
            self.progress.emit(0, f"Bắt đầu xử lý {total_subs} phụ đề với tối đa {self.MAX_WORKERS} luồng...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                future_to_sub = {executor.submit(self._process_segment, sub, i + 1, total_subs): sub for i, sub in enumerate(subs)}

                for future in concurrent.futures.as_completed(future_to_sub):
                    if not self.is_running:
                        for f in future_to_sub: f.cancel()
                        break
                    
                    result_idx = future.result()
                    if result_idx is not None:
                        failed_indices.append(result_idx)

            if not self.is_running:
                self.progress.emit(self.completed_count * 100 // total_subs, "Tác vụ đã bị dừng bởi người dùng.")
                return

            self.progress.emit(100, "Đang ghép các tệp âm thanh...")
            self._concatenate_segments(subs, self.output_path, FFMPEG_BIN, TEMP_DIR)
            
            # === Tạo dự án CapCut nếu được bật ===
            capcut_project_dir = None
            if self.config.get('create_capcut') and self.config.get('video_path'):
                video_path = self.config['video_path']
                if os.path.exists(video_path):
                    self.progress.emit(100, "🎬 Đang tạo dự án CapCut...")
                    try:
                        capcut_project_dir = self._create_capcut_project(
                            subs, self.output_path, video_path, FFMPEG_BIN
                        )
                    except Exception as e:
                        self.progress.emit(100, f"⚠️ Lỗi khi tạo dự án CapCut: {e}")
                else:
                    self.progress.emit(100, f"⚠️ Không tìm thấy file video: {video_path}")

            if self.config.get('delete_temp', True):
                self.progress.emit(100, "Dọn dẹp các tệp tạm thời...")
                try:
                    shutil.rmtree(TEMP_DIR)
                    self.progress.emit(100, "-> Đã dọn dẹp thư mục temp.")
                except Exception as e:
                    self.progress.emit(100, f"-> ⚠️ Không thể xóa thư mục temp: {e}")
            else:
                self.progress.emit(100, f"-> Giữ lại thư mục temp theo cài đặt. Đường dẫn: {TEMP_DIR}")

            final_message = f"✅ HOÀN TẤT! Đã lưu file tại:\n{self.output_path}"
            if capcut_project_dir:
                final_message += f"\n\n🎬 Dự án CapCut: {capcut_project_dir}"
            if failed_indices:
                final_message += f"\n\nCảnh báo: Không thể tạo âm thanh cho các phụ đề số: {', '.join(map(str, sorted(failed_indices)))}"

            self.finished.emit(final_message)

        except Exception as e:
            self.error.emit(f"Đã xảy ra lỗi nghiêm trọng: {e}")

    # Danh sách TikTok TTS API endpoints (thử lần lượt nếu endpoint trước bị lỗi)
    TIKTOK_API_ENDPOINTS = [
        'https://tiktok-tts.weilnet.workers.dev/api/generation',
        'https://countik.com/api/text/speech',
        'https://gesserit.co/api/tiktok-tts',
    ]

    def _call_tiktok_api(self, text: str, session_id: str, voice: str):
        headers = {'Content-Type': 'application/json'}
        data = {'text': text, 'voice': voice}
        cookies = {'sessionid': session_id}

        for attempt in range(4):
            for url in self.TIKTOK_API_ENDPOINTS:
                try:
                    response = requests.post(url, headers=headers, data=json.dumps(data), cookies=cookies, timeout=30)
                    response.raise_for_status()
                    json_response = response.json()
                    if json_response.get("data"):
                        return base64.b64decode(json_response["data"])
                except Exception:
                    continue  # Thử endpoint tiếp theo

            self.progress.emit(0, f"-> TikTok retry {attempt+1}/4: tất cả endpoints đều lỗi")
            time.sleep(1 + attempt)  # Progressive backoff: 1s, 2s, 3s, 4s
        return None

    def _call_fpt_api(self, text: str, api_key: str, voice: str = 'banmai'):
        """Gọi API FPT AI Text-to-Speech. Trả về audio bytes (MP3)."""
        url = 'https://api.fpt.ai/hmi/tts/v5'
        headers = {
            'api-key': api_key,
            'voice': voice,
            'speed': '0',  # Tốc độ bình thường (sẽ dùng speed_factor riêng)
        }
        
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, data=text.encode('utf-8'), timeout=30)
                response.raise_for_status()
                json_response = response.json()
                
                # FPT trả về JSON chứa URL audio — cần tải về
                audio_url = json_response.get('async')
                if not audio_url:
                    self.progress.emit(0, f"-> FPT API Error: {json_response.get('message', 'Không có URL audio')}")
                    return None
                
                # Chờ và tải file audio (FPT cần vài giây xử lý)
                for wait_attempt in range(15):  # Tối đa 15 lần thử (15 giây)
                    time.sleep(1)
                    try:
                        audio_resp = requests.get(audio_url, timeout=15)
                        if audio_resp.status_code == 200 and len(audio_resp.content) > 1000:
                            return audio_resp.content
                    except Exception:
                        pass
                
                self.progress.emit(0, "-> FPT: Timeout khi tải audio")
                return None
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    wait = 3 + attempt * 2  # 429: đợi lâu hơn (3s, 5s, 7s)
                    self.progress.emit(0, f"-> FPT rate-limit, đợi {wait}s (lần {attempt+1})...")
                    time.sleep(wait)
                else:
                    self.progress.emit(0, f"-> FPT API lỗi (lần {attempt+1}): {e}")
                    time.sleep(1)
            except Exception as e:
                self.progress.emit(0, f"-> FPT API lỗi (lần {attempt+1}): {e}")
                time.sleep(1)
        return None

    def _call_elevenlabs_api(self, text: str, api_key: str, voice_id: str):
        """Gọi API ElevenLabs Text-to-Speech. Trả về audio bytes (MP3)."""
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        headers = {
            'xi-api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'audio/mpeg',
        }
        data = {
            'text': text,
            'model_id': 'eleven_multilingual_v2',
            'voice_settings': {
                'stability': 0.5,
                'similarity_boost': 0.75,
            }
        }
        
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=30)
                if response.status_code == 200:
                    return response.content  # Audio bytes trực tiếp
                else:
                    error_detail = ""
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('detail', {})
                        if isinstance(error_detail, dict):
                            error_detail = error_detail.get('message', str(error_detail))
                    except Exception:
                        error_detail = response.text[:200]
                    self.progress.emit(0, f"-> ElevenLabs API Error ({response.status_code}): {error_detail}")
                    return None
            except Exception as e:
                self.progress.emit(0, f"-> ElevenLabs lỗi (lần {attempt+1}): {e}")
                time.sleep(1)
        return None

    def _get_duration(self, path: str, ffprobe_bin: str) -> float:
        proc = subprocess.run(
            [ffprobe_bin, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return float(proc.stdout.strip())

    def _pad_silence_tail(self, wav_path: str, pad_ms: int = 100):
        """Nối thêm pad_ms mili-giây khoảng lặng vào đuôi file WAV.
        Thao tác trực tiếp trên waveform array, cực nhanh, không cần gọi ffmpeg."""
        try:
            import wave, struct
            with wave.open(wav_path, 'rb') as wf:
                params = wf.getparams()
                frames = wf.readframes(wf.getnframes())
            # Tính số sample cần thêm
            n_silence_samples = int(params.framerate * pad_ms / 1000) * params.nchannels
            silence_bytes = b'\x00\x00' * n_silence_samples  # 16-bit silence = 0
            # Ghi lại file WAV với silence đuôi
            with wave.open(wav_path, 'wb') as wf:
                wf.setparams(params)
                wf.writeframes(frames + silence_bytes)
        except Exception:
            pass  # Nếu lỗi, bỏ qua (không ảnh hưởng chức năng chính)

    def _decode_to_wav(self, mp3_path: str, wav_path: str, ffmpeg_bin: str):
        """Decode MP3 sang WAV (44100Hz, stereo, s16le) để xử lý sample-accurate."""
        subprocess.run([
            ffmpeg_bin, '-y', '-i', mp3_path,
            '-ar', '44100', '-ac', '2', '-sample_fmt', 's16',
            wav_path
        ], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def _apply_speed(self, wav_path: str, speed_factor: float, ffmpeg_bin: str):
        """
        Áp dụng atempo để thay đổi tốc độ đọc.
        speed_factor > 1.0 = đọc nhanh hơn, < 1.0 = đọc chậm hơn.
        Timeline SRT vẫn được giữ nguyên nhờ _adjust_duration chạy sau.
        """
        tmp_path = wav_path + '.speed.wav'
        atempo_val = max(0.5, min(speed_factor, 2.0))
        subprocess.run([
            ffmpeg_bin, '-y', '-i', wav_path,
            '-filter:a', f'atempo={atempo_val:.6f}',
            '-c:a', 'pcm_s16le', '-ar', '44100', '-ac', '2',
            tmp_path
        ], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        os.replace(tmp_path, wav_path)

    def _make_silence(self, duration: float, filename: str, ffmpeg_bin: str):
        """Tạo file WAV im lặng với duration chính xác."""
        subprocess.run(
            [ffmpeg_bin, '-y', '-f', 'lavfi',
             '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
             '-t', f"{duration:.6f}",
             '-sample_fmt', 's16',
             filename],
            check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )

    def _detect_silence_boundaries(self, wav_path: str, ffmpeg_bin: str, threshold_db: str = '-40dB', min_duration: float = 0.05) -> tuple:
        """
        Phát hiện khoảng lặng ở đầu và cuối file WAV.
        Trả về (leading_silence_sec, trailing_silence_sec).
        """
        try:
            proc = subprocess.run([
                ffmpeg_bin, '-i', wav_path, '-af',
                f'silencedetect=noise={threshold_db}:d={min_duration}',
                '-f', 'null', '-'
            ], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            stderr = proc.stderr
            # Parse silence_start / silence_end / silence_duration
            silence_starts = []
            silence_ends = []
            for line in stderr.split('\n'):
                if 'silence_start:' in line:
                    m = re.search(r'silence_start:\s*([\d.]+)', line)
                    if m:
                        silence_starts.append(float(m.group(1)))
                if 'silence_end:' in line:
                    m = re.search(r'silence_end:\s*([\d.]+)', line)
                    if m:
                        silence_ends.append(float(m.group(1)))
            
            # Lấy duration file
            ffprobe_bin = os.path.join(os.path.dirname(ffmpeg_bin), 'ffprobe.exe')
            file_dur = self._get_duration(wav_path, ffprobe_bin)
            
            leading = 0.0
            trailing = 0.0
            
            # Leading silence: khoảng lặng bắt đầu tại 0.0
            if silence_starts and silence_ends and silence_starts[0] < 0.01:
                leading = silence_ends[0]
            
            # Trailing silence: khoảng lặng kết thúc tại cuối file
            if silence_starts:
                last_start = silence_starts[-1]
                # Nếu silence cuối chạy đến hết file (không có silence_end tương ứng hoặc silence_end ≈ file_dur)
                if len(silence_ends) < len(silence_starts):
                    # silence cuối chưa kết thúc = chạy đến hết file
                    trailing = file_dur - last_start
                elif len(silence_ends) == len(silence_starts):
                    last_end = silence_ends[-1]
                    if abs(last_end - file_dur) < 0.05:
                        trailing = file_dur - last_start
            
            return (leading, trailing)
        except Exception:
            return (0.0, 0.0)

    def _trim_silence(self, wav_path: str, ffmpeg_bin: str, max_trim_each_side: float = 0.8) -> float:
        """
        Cắt khoảng lặng đầu/cuối file WAV (tối đa max_trim_each_side mỗi bên).
        Trả về tổng thời gian đã cắt được.
        """
        leading, trailing = self._detect_silence_boundaries(wav_path, ffmpeg_bin)
        
        trim_start = min(leading, max_trim_each_side)
        trim_end = min(trailing, max_trim_each_side)
        
        if trim_start < 0.01 and trim_end < 0.01:
            return 0.0  # Không có gì để cắt
        
        ffprobe_bin = os.path.join(os.path.dirname(ffmpeg_bin), 'ffprobe.exe')
        file_dur = self._get_duration(wav_path, ffprobe_bin)
        
        # Tính thời điểm bắt đầu và kết thúc mới
        new_start = trim_start
        new_end = file_dur - trim_end
        
        if new_end <= new_start:
            return 0.0  # Tránh trường hợp file quá ngắn
        
        tmp_path = wav_path + '.trimmed.wav'
        try:
            subprocess.run([
                ffmpeg_bin, '-y', '-i', wav_path,
                '-ss', f"{new_start:.6f}",
                '-to', f"{new_end:.6f}",
                '-c:a', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                tmp_path
            ], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            os.replace(tmp_path, wav_path)
            return trim_start + trim_end
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            return 0.0

    def _adjust_duration(self, seg_fn, sub, ffmpeg_bin, ffprobe_bin, temp_dir, trim_tol=0.01):
        """
        Điều chỉnh duration của segment WAV theo timeline SRT.
        Thứ tự ưu tiên:
          1. Trim silence (tối đa 0.8s mỗi bên)
          2. Atempo nếu vẫn quá dài
          3. Pad silence nếu quá ngắn
        """
        try:
            dur = self._get_duration(seg_fn, ffprobe_bin)
            target = (sub.end - sub.start).total_seconds()
            
            if target <= 0:
                return

            # === Bước 1: Trim silence nếu audio quá dài ===
            if dur - target > trim_tol:
                trimmed = self._trim_silence(seg_fn, ffmpeg_bin, max_trim_each_side=0.8)
                if trimmed > 0:
                    dur = self._get_duration(seg_fn, ffprobe_bin)  # Đo lại sau trim

            delta = target - dur

            # === Bước 2: Video chậm trước, audio atempo sau (nếu cần) ===
            if delta < -trim_tol:
                # Tính tốc độ video cần thiết
                natural_speed = target / dur  # VD: 2s/5s = 0.4x
                video_speed = max(0.6, natural_speed)  # Cap tối đa 0.3x (không chậm hơn)
                
                # Ghi nhận segment cần slow-down video
                with self.lock:
                    self.slow_segments.append({
                        'sub_index': sub.index,
                        'srt_start': sub.start.total_seconds(),
                        'srt_end': sub.end.total_seconds(),
                        'audio_duration': dur,
                        'target_duration': target,
                        'speed_ratio': video_speed,
                    })
                
                # Tính duration có sẵn sau khi video đã chậm lại
                adjusted_target = target / video_speed  # VD: 2s/0.3 = 6.67s
                
                # CHỈ atempo audio nếu vẫn quá dài SAU KHI video đã chậm tối đa
                if dur > adjusted_target + trim_tol:
                    atempo_speed = dur / adjusted_target
                    atempo_speed = max(0.5, min(atempo_speed, 2.0))
                    tmp_fn = seg_fn + ".tmp.wav"
                    subprocess.run([
                        ffmpeg_bin, '-y', '-i', seg_fn,
                        '-filter:a', f"atempo={atempo_speed:.6f}",
                        '-c:a', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                        tmp_fn
                    ], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    os.replace(tmp_fn, seg_fn)
                # Nếu audio ngắn hơn adjusted_target → không cần atempo!

            # === Bước 3: Pad silence nếu quá ngắn ===
            elif delta > trim_tol:
                pad_fn = os.path.join(temp_dir, f"pad_{sub.index:04d}.wav")
                self._make_silence(delta, pad_fn, ffmpeg_bin)
                concat_list_fn = os.path.join(temp_dir, f"concat_pad_{sub.index:04d}.txt")
                with open(concat_list_fn, 'w', encoding='utf-8') as f:
                    f.write(f"file '{os.path.abspath(seg_fn)}'\n")
                    f.write(f"file '{os.path.abspath(pad_fn)}'\n")
                tmp_fn = seg_fn + ".tmp.wav"
                subprocess.run([
                    ffmpeg_bin, '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_fn,
                    '-c', 'copy', tmp_fn
                ], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                os.replace(tmp_fn, seg_fn)
                # Dọn file tạm
                for f_path in [pad_fn, concat_list_fn]:
                    try:
                        os.remove(f_path)
                    except Exception:
                        pass
        except Exception as e:
            # Log lỗi nhưng không crash
            pass

    def _concatenate_segments(self, subs: List[srt.Subtitle], output_path: str, ffmpeg_bin: str, temp_dir: str, trim_tol=0.01):
        """Ghép tất cả segment WAV và encode MP3 một lần duy nhất ở cuối.
        Audio được đặt theo timeline đã điều chỉnh tốc độ (khớp với video)."""
        
        # === Chế độ Audio Edit: xuất từng segment riêng ===
        if self.config.get('audio_edit'):
            edit_dir = os.path.join(os.path.dirname(output_path), 'audio_edit')
            os.makedirs(edit_dir, exist_ok=True)
            copied = 0
            for i, sub in enumerate(subs):
                idx = i + 1
                seg_fn = os.path.join(temp_dir, f"seg_{idx:04d}.wav")
                if os.path.exists(seg_fn):
                    # Tên file: 001_start-end.wav
                    start_str = f"{sub.start.total_seconds():.1f}s"
                    dest = os.path.join(edit_dir, f"{idx:03d}_{start_str}.wav")
                    shutil.copy2(seg_fn, dest)
                    copied += 1
            self.progress.emit(100, f"🔊 Audio Edit: Đã xuất {copied} segment vào {edit_dir}")
            return  # Không ghép MP3, chỉ xuất segment riêng
        
        parts = []
        ffprobe_bin = os.path.join(os.path.dirname(ffmpeg_bin), 'ffprobe.exe')
        
        # === Tính toán adjusted timeline từ slow_segments ===
        video_path = self.config.get('video_path')
        video_duration = 0
        if video_path and os.path.exists(video_path):
            video_duration = self._get_duration(video_path, ffprobe_bin)
        else:
            # Fallback: dùng thời gian kết thúc của sub cuối
            video_duration = subs[-1].end.total_seconds() if subs else 0
        
        video_duration_us = int(video_duration * 1_000_000)
        
        # Tạo danh sách speed events từ slow_segments
        slow_segs = sorted(self.slow_segments, key=lambda x: x['srt_start'])
        speed_events = []
        for seg in slow_segs:
            speed_events.append({
                'start_us': int(seg['srt_start'] * 1_000_000),
                'end_us': int(seg['srt_end'] * 1_000_000),
                'speed': max(0.2, seg['speed_ratio']),
            })
        
        # Merge overlapping events
        merged_events = []
        for ev in speed_events:
            if merged_events and ev['start_us'] <= merged_events[-1]['end_us']:
                merged_events[-1]['end_us'] = max(merged_events[-1]['end_us'], ev['end_us'])
                merged_events[-1]['speed'] = min(merged_events[-1]['speed'], ev['speed'])
            else:
                merged_events.append(ev.copy())
        
        # Tạo regions (normal speed + slow speed)
        all_regions = []
        pos = 0
        for ev in merged_events:
            if ev['start_us'] > pos:
                all_regions.append({'start': pos, 'end': ev['start_us'], 'speed': 1.0})
            all_regions.append({'start': ev['start_us'], 'end': ev['end_us'], 'speed': ev['speed']})
            pos = ev['end_us']
        if pos < video_duration_us:
            all_regions.append({'start': pos, 'end': video_duration_us, 'speed': 1.0})
        
        # Tính timeline position cho mỗi region
        total_timeline_us = 0
        for r in all_regions:
            source_dur = r['end'] - r['start']
            timeline_dur = int(source_dur / r['speed']) if r['speed'] > 0 else source_dur
            r['timeline_start'] = total_timeline_us
            r['timeline_dur'] = timeline_dur
            total_timeline_us += timeline_dur
        
        # Helper: map SRT time → adjusted timeline
        def map_to_timeline(srt_time_us):
            for r in all_regions:
                if srt_time_us <= r['start']:
                    return r['timeline_start']
                if srt_time_us <= r['end']:
                    offset = srt_time_us - r['start']
                    return r['timeline_start'] + int(offset / r['speed'])
            return total_timeline_us
        
        has_slow = len(self.slow_segments) > 0
        if has_slow:
            self.progress.emit(100, f"📊 Timeline điều chỉnh: {total_timeline_us / 1_000_000:.2f}s (gốc: {video_duration:.2f}s)")
        
        # === Ghép audio theo timeline đã điều chỉnh ===
        current_position = 0.0  # seconds
        
        for i, sub in enumerate(subs):
            idx = i + 1
            
            # Dùng adjusted timeline nếu có slow segments
            if has_slow:
                sub_start_us = int(sub.start.total_seconds() * 1_000_000)
                expected_start = map_to_timeline(sub_start_us) / 1_000_000.0
            else:
                expected_start = sub.start.total_seconds()
            
            gap = expected_start - current_position
            if gap > trim_tol:
                gap_fn = os.path.join(temp_dir, f"sil_{idx:04d}.wav")
                self._make_silence(gap, gap_fn, ffmpeg_bin)
                parts.append(gap_fn)
                current_position += gap
            elif gap < -trim_tol:
                self.progress.emit(100, f"   ⚠️ Segment {idx}: bị trễ {-gap:.3f}s so với timeline")
            
            seg_fn = os.path.join(temp_dir, f"seg_{idx:04d}.wav")
            if os.path.exists(seg_fn):
                parts.append(seg_fn)
                seg_dur = self._get_duration(seg_fn, ffprobe_bin)
                current_position += seg_dur
            else:
                target = (sub.end - sub.start).total_seconds()
                fallback_fn = os.path.join(temp_dir, f"fallback_{idx:04d}.wav")
                self._make_silence(target, fallback_fn, ffmpeg_bin)
                parts.append(fallback_fn)
                current_position += target

        expected_end = total_timeline_us / 1_000_000.0 if has_slow else subs[-1].end.total_seconds()
        self.progress.emit(100, f"📊 Timeline cuối: {current_position:.3f}s (mong đợi: {expected_end:.3f}s, lệch: {current_position - expected_end:.3f}s)")

        # 2. Sắp xếp file
        final_parts = []
        if self.config.get('rename_temp_files', False):
            self.progress.emit(100, "-> Đang sắp xếp lại các file trong thư mục temp...")
            for i, old_path in enumerate(parts):
                if os.path.exists(old_path):
                    basename = os.path.basename(old_path)
                    new_basename = f"{i+1:04d}_{basename}"
                    new_path = os.path.join(temp_dir, new_basename)
                    
                    if old_path != new_path:
                        if os.path.exists(new_path):
                            os.remove(new_path)
                        os.rename(old_path, new_path)
                    
                    final_parts.append(new_path)
            self.progress.emit(100, "-> Đã sắp xếp xong.")
        else:
            final_parts = parts

        # 3. Ghi danh sách file WAV để ghép
        list_file = os.path.join(temp_dir, 'files_to_concat.txt')
        with open(list_file, 'w', encoding='utf-8') as lf:
            for part_path in final_parts:
                lf.write(f"file '{os.path.abspath(part_path)}'\n")

        # 4. Ghép tất cả WAV thành 1 file WAV lớn
        combined_wav = os.path.join(temp_dir, 'combined_output.wav')
        self.progress.emit(100, "-> Đang ghép tất cả WAV segments...")
        subprocess.run([
            ffmpeg_bin, '-y', '-f', 'concat', '-safe', '0', '-i', list_file,
            '-c', 'copy', combined_wav
        ], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

        # 5. Encode MP3 MỘT LẦN DUY NHẤT từ WAV đã ghép
        self.progress.emit(100, "-> Đang encode MP3 cuối cùng (một lần duy nhất)...")
        subprocess.run([
            ffmpeg_bin, '-y', '-i', combined_wav,
            '-c:a', 'libmp3lame', '-q:a', '2', output_path
        ], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        # Dọn file WAV tổng hợp
        try:
            os.remove(combined_wav)
        except Exception:
            pass
        
        self.progress.emit(100, f"-> ✅ Đã encode MP3 thành công: {output_path}")


    def _create_capcut_project(self, subs, audio_path, video_path, ffmpeg_bin):
        """Tạo dự án CapCut với video track (có slow-down) và audio track."""
        ffprobe_bin = os.path.join(os.path.dirname(ffmpeg_bin), 'ffprobe.exe')
        
        video_duration = self._get_duration(video_path, ffprobe_bin)
        video_duration_us = int(video_duration * 1_000_000)
        if os.path.exists(audio_path):
            audio_duration = self._get_duration(audio_path, ffprobe_bin)
        else:
            audio_duration = 0.0
        audio_duration_us = int(audio_duration * 1_000_000)
        
        try:
            proc = subprocess.run([
                ffprobe_bin, '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=s=x:p=0', video_path
            ], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            w, h = proc.stdout.strip().split('x')
            canvas_width, canvas_height = int(w), int(h)
        except Exception:
            canvas_width, canvas_height = 1920, 1080

        self.progress.emit(100, f"📐 Video: {canvas_width}x{canvas_height}, {video_duration:.2f}s")
        self.progress.emit(100, f"🔊 Audio: {audio_duration:.2f}s")
        self.progress.emit(100, f"🐢 Số đoạn cần slow-down: {len(self.slow_segments)}")

        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        project_id = str(uuid.uuid4()).upper()
        project_dir = os.path.join(os.path.dirname(audio_path), f"capcut_{base_name}")
        os.makedirs(project_dir, exist_ok=True)

        video_material_id = str(uuid.uuid4()).upper()
        audio_material_id = str(uuid.uuid4()).upper()
        video_path_abs = os.path.abspath(video_path).replace('\\', '/')
        audio_path_abs = os.path.abspath(audio_path).replace('\\', '/')

        def _uid():
            return str(uuid.uuid4()).upper()

        # === Tính toán video segments với speed ===
        slow_segs = sorted(self.slow_segments, key=lambda x: x['srt_start'])
        speed_events = []
        for seg in slow_segs:
            speed_events.append({
                'start_us': int(seg['srt_start'] * 1_000_000),
                'end_us': int(seg['srt_end'] * 1_000_000),
                'speed': max(0.2, seg['speed_ratio']),
            })
        
        merged_events = []
        for ev in speed_events:
            if merged_events and ev['start_us'] <= merged_events[-1]['end_us']:
                merged_events[-1]['end_us'] = max(merged_events[-1]['end_us'], ev['end_us'])
                merged_events[-1]['speed'] = min(merged_events[-1]['speed'], ev['speed'])
            else:
                merged_events.append(ev.copy())
        
        all_regions = []
        pos = 0
        for ev in merged_events:
            if ev['start_us'] > pos:
                all_regions.append({'start': pos, 'end': ev['start_us'], 'speed': 1.0})
            all_regions.append({'start': ev['start_us'], 'end': ev['end_us'], 'speed': ev['speed']})
            pos = ev['end_us']
        if pos < video_duration_us:
            all_regions.append({'start': pos, 'end': video_duration_us, 'speed': 1.0})
        
        total_timeline_us = 0
        for r in all_regions:
            source_dur = r['end'] - r['start']
            timeline_dur = int(source_dur / r['speed']) if r['speed'] > 0 else source_dur
            r['timeline_start'] = total_timeline_us
            r['timeline_dur'] = timeline_dur
            total_timeline_us += timeline_dur

        self.progress.emit(100, f"📊 Timeline: {total_timeline_us / 1_000_000:.2f}s (video gốc: {video_duration:.2f}s)")

        # === Helper: map SRT time (us) → timeline position (us) ===
        def map_to_timeline(srt_time_us):
            """Convert SRT time (us) to adjusted timeline position (us), accounting for speed changes."""
            timeline_pos = 0
            remaining = srt_time_us
            for r in all_regions:
                region_src_dur = r['end'] - r['start']
                if remaining <= 0:
                    break
                if srt_time_us <= r['start']:
                    break
                if srt_time_us <= r['end']:
                    # Inside this region
                    offset_in_region = srt_time_us - r['start']
                    timeline_pos = r['timeline_start'] + int(offset_in_region / r['speed'])
                    return timeline_pos
                timeline_pos = r['timeline_start'] + r['timeline_dur']
            return timeline_pos

        # === Build SRT subtitle text materials and segments ===
        text_materials = []
        text_segments = []
        subtitle_group_id = _uid()  # Shared group ID for batch editing
        
        for sub in subs:
            sub_start_us = int(sub.start.total_seconds() * 1_000_000)
            sub_end_us = int(sub.end.total_seconds() * 1_000_000)
            
            # Subtitle sync với adjusted timeline (khớp video + audio đã điều chỉnh)
            tl_start = map_to_timeline(sub_start_us)
            tl_end = map_to_timeline(sub_end_us)
            tl_duration = max(tl_end - tl_start, 100_000)  # min 0.1s
            
            text_content = sub.content.strip()
            # Strip tag nhân vật {Tên NV} khỏi phụ đề (chỉ dùng cho lồng tiếng)
            text_content = re.sub(r'\{.+?\}\s*', '', text_content).strip()
            if not text_content:
                continue
            
            text_mat_id = _uid()
            text_seg_id = _uid()
            
            text_material = {
                "id": text_mat_id,
                "type": "text",
                "content": text_content,
                "alignment": 1,
                "background_alpha": 0.0,
                "background_color": "",
                "background_height": 0.14,
                "background_horizontal_offset": 0.0,
                "background_round_radius": 0.0,
                "background_style": 0,
                "background_vertical_offset": 0.005,
                "background_width": 0.14,
                "base_content": "",
                "bold_width": 0.0,
                "border_alpha": 1.0,
                "border_color": "",
                "border_width": 0.08,
                "caption_template_info": {
                    "category_id": "",
                    "category_name": "",
                    "effect_id": "",
                    "is_new": False,
                    "path": "",
                    "request_id": "",
                    "resource_id": "",
                    "resource_name": "",
                    "source_platform": 0
                },
                "cap_text_type": 0,
                "check_flag": 7,
                "combo_info": {"text_templates": []},
                "fixed_height": -1.0,
                "fixed_width": -1.0,
                "font_category_id": "",
                "font_category_name": "",
                "font_id": "",
                "font_name": "",
                "font_path": "",
                "font_resource_id": "",
                "font_size": float(self.config.get('subtitle_size', 5)),
                "font_source_platform": 0,
                "font_team_id": "",
                "font_title": "Default",
                "font_url": "",
                "fonts": [],
                "force_apply_line_max_width": True,
                "global_alpha": 1.0,
                "group_id": "",
                "has_shadow": True,
                "initial_scale": 1.0,
                "inner_padding": -1.0,
                "is_rich_text": False,
                "italic_degree": 0,
                "ktv_color": "",
                "language": "",
                "layer_weight": 1,
                "letter_spacing": 0.0,
                "line_feed": 1,
                "line_max_width": 1.0,
                "line_spacing": 0.02,
                "name": "",
                "original_size": [],
                "preset_category": "",
                "preset_category_id": "",
                "preset_has_set_alignment": False,
                "preset_id": "",
                "preset_index": 0,
                "preset_name": "",
                "recognize_task_id": "",
                "recognize_type": 0,
                "relevance_segment": [],
                "shadow_alpha": 0.9,
                "shadow_angle": -45.0,
                "shadow_color": "",
                "shadow_distance": 0.0,
                "shadow_point": {"x": 0.6401844024658203, "y": 0.6401844024658203},
                "shadow_smoothing": 0.45,
                "shape_clip_x": False,
                "shape_clip_y": False,
                "source_from": "",
                "style_name": "",
                "sub_type": 0,
                "subtitle_keywords": None,
                "text_alpha": 1.0,
                "text_color": "#FFFFFF",
                "text_curve": None,
                "text_preset_resource_id": "",
                "text_size": int(self.config.get('subtitle_size', 5)),
                "text_to_audio_ids": [],
                "tts_auto_update": False,
                "typesetting": 0,
                "underline": False,
                "underline_offset": 0.22,
                "underline_width": 0.05,
                "use_effect_default_color": True,
                "words": {"end_time": [], "start_time": [], "text": []}
            }
            text_materials.append(text_material)
            
            # Text segment linking to material
            text_segment = {
                "id": text_seg_id,
                "source_timerange": {"start": 0, "duration": tl_duration},
                "target_timerange": {"start": tl_start, "duration": tl_duration},
                "render_timerange": {"start": 0, "duration": 0},
                "desc": "",
                "state": 0,
                "speed": 1.0,
                "is_loop": False,
                "is_tone_modify": False,
                "reverse": False,
                "intensifies_audio": False,
                "cartoon": False,
                "volume": 1.0,
                "last_nonzero_volume": 1.0,
                "clip": {
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0.0,
                    "transform": {"x": 0.0, "y": -0.9},
                    "flip": {"vertical": False, "horizontal": False},
                    "alpha": 1.0
                },
                "uniform_scale": {"on": True, "value": 1.0},
                "material_id": text_mat_id,
                "extra_material_refs": [],
                "render_index": 0,
                "keyframe_refs": [],
                "enable_lut": True,
                "enable_adjust": True,
                "enable_hsl": False,
                "visible": True,
                "group_id": subtitle_group_id,
                "enable_color_curves": True,
                "enable_hsl_curves": True,
                "track_render_index": 0,
                "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
                "enable_color_wheels": True,
                "track_attribute": 0,
                "is_placeholder": False,
                "template_id": "",
                "enable_smart_color_adjust": False,
                "template_scene": "default",
                "common_keyframes": [],
                "caption_info": None,
                "responsive_layout": {
                    "enable": False, "target_follow": "",
                    "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0
                },
                "enable_color_match_adjust": False,
                "enable_color_correct_adjust": False,
                "enable_adjust_mask": False,
                "raw_segment_id": "",
                "lyric_keyframes": None,
                "enable_video_mask": True,
                "digital_human_template_group_id": "",
                "color_correct_alg_result": "",
                "source": "segmentsourcenormal",
                "enable_mask_stroke": False,
                "enable_mask_shadow": False,
            }
            text_segments.append(text_segment)
        
        self.progress.emit(100, f"📝 Đã tạo {len(text_segments)} subtitle segments")

        # === Build segments theo format CapCut v7.9 ===
        video_segments = []
        for r in all_regions:
            source_dur = r['end'] - r['start']
            seg_id = _uid()
            speed_id = _uid()
            canvas_id = _uid()
            placeholder_id = _uid()
            sound_ch_id = _uid()
            mat_color_id = _uid()
            vocal_sep_id = _uid()
            
            segment = {
                "id": seg_id,
                "source_timerange": {"start": r['start'], "duration": source_dur},
                "target_timerange": {"start": r['timeline_start'], "duration": r['timeline_dur']},
                "render_timerange": {"start": 0, "duration": 0},
                "desc": "",
                "state": 0,
                "speed": r['speed'],
                "is_loop": False,
                "is_tone_modify": False,
                "reverse": False,
                "intensifies_audio": False,
                "cartoon": False,
                "volume": 1.0,
                "last_nonzero_volume": 1.0,
                "clip": {
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0.0,
                    "transform": {"x": 0.0, "y": 0.0},
                    "flip": {"vertical": False, "horizontal": False},
                    "alpha": 1.0
                },
                "uniform_scale": {"on": True, "value": 1.0},
                "material_id": video_material_id,
                "extra_material_refs": [speed_id, placeholder_id, canvas_id, sound_ch_id, mat_color_id, vocal_sep_id],
                "render_index": 0,
                "keyframe_refs": [],
                "enable_lut": True,
                "enable_adjust": True,
                "enable_hsl": False,
                "visible": True,
                "group_id": "",
                "enable_color_curves": True,
                "enable_hsl_curves": True,
                "track_render_index": 0,
                "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
                "enable_color_wheels": True,
                "track_attribute": 0,
                "is_placeholder": False,
                "template_id": "",
                "enable_smart_color_adjust": False,
                "template_scene": "default",
                "common_keyframes": [],
                "caption_info": None,
                "responsive_layout": {
                    "enable": False, "target_follow": "",
                    "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0
                },
                "enable_color_match_adjust": False,
                "enable_color_correct_adjust": False,
                "enable_adjust_mask": False,
                "raw_segment_id": "",
                "lyric_keyframes": None,
                "enable_video_mask": True,
                "digital_human_template_group_id": "",
                "color_correct_alg_result": "",
                "source": "segmentsourcenormal",
                "enable_mask_stroke": False,
                "enable_mask_shadow": False,
                "_speed_id": speed_id,
                "_canvas_id": canvas_id,
                "_placeholder_id": placeholder_id,
                "_sound_ch_id": sound_ch_id,
                "_mat_color_id": mat_color_id,
                "_vocal_sep_id": vocal_sep_id,
            }
            video_segments.append(segment)

        # Collect generated material child objects
        speeds_list = []
        canvases_list = []
        placeholder_infos_list = []
        sound_channel_list = []
        material_colors_list = []
        vocal_separations_list = []
        
        for seg in video_segments:
            speeds_list.append({
                "id": seg["_speed_id"], "type": "speed",
                "mode": 0, "speed": seg["speed"], "curve_speed": None
            })
            canvases_list.append({
                "id": seg["_canvas_id"], "type": "canvas_color",
                "color": "", "blur": 0.0, "image": "", "album_image": "",
                "image_id": "", "image_name": "", "source_platform": 0, "team_id": ""
            })
            placeholder_infos_list.append({
                "id": seg["_placeholder_id"], "type": "placeholder_info",
                "meta_type": "none", "res_path": "", "res_text": "",
                "error_path": "", "error_text": ""
            })
            sound_channel_list.append({
                "id": seg["_sound_ch_id"], "type": "none",
                "audio_channel_mapping": 0, "is_config_open": False
            })
            material_colors_list.append({
                "id": seg["_mat_color_id"], "is_color_clip": False,
                "is_gradient": False, "solid_color": "",
                "gradient_colors": [], "gradient_percents": [],
                "gradient_angle": 90.0, "width": 0.0, "height": 0.0
            })
            vocal_separations_list.append({
                "id": seg["_vocal_sep_id"], "type": "vocal_separation",
                "choice": 0, "removed_sounds": [], "time_range": None,
                "production_path": "", "final_algorithm": "", "enter_from": ""
            })
            # Remove internal keys
            for k in ["_speed_id", "_canvas_id", "_placeholder_id", "_sound_ch_id", "_mat_color_id", "_vocal_sep_id"]:
                del seg[k]

        # Audio segment(s)
        audio_segments_list = []
        audio_materials_list = []
        
        if self.config.get('audio_edit'):
            # === Audio Edit: từng segment riêng trên timeline ===
            edit_dir = os.path.join(os.path.dirname(audio_path), 'audio_edit')
            for i, sub in enumerate(subs):
                idx = i + 1
                start_str = f"{sub.start.total_seconds():.1f}s"
                seg_wav = os.path.join(edit_dir, f"{idx:03d}_{start_str}.wav")
                if not os.path.exists(seg_wav):
                    continue
                
                seg_dur_s = self._get_duration(seg_wav, ffprobe_bin)
                seg_dur_us = int(seg_dur_s * 1_000_000)
                
                # Timeline position (adjusted)
                sub_start_us = int(sub.start.total_seconds() * 1_000_000)
                tl_start = map_to_timeline(sub_start_us)
                
                a_mat_id = _uid()
                a_seg_id = _uid()
                a_speed_id = _uid()
                a_canvas_id = _uid()
                a_placeholder_id = _uid()
                a_sound_ch_id = _uid()
                a_mat_color_id = _uid()
                a_vocal_sep_id = _uid()
                
                seg_wav_abs = os.path.abspath(seg_wav).replace('\\', '/')
                
                audio_segments_list.append({
                    "id": a_seg_id,
                    "source_timerange": {"start": 0, "duration": seg_dur_us},
                    "target_timerange": {"start": tl_start, "duration": seg_dur_us},
                    "render_timerange": {"start": 0, "duration": 0},
                    "desc": "", "state": 0, "speed": 1.0,
                    "is_loop": False, "is_tone_modify": False, "reverse": False,
                    "intensifies_audio": False, "cartoon": False,
                    "volume": 1.0, "last_nonzero_volume": 1.0,
                    "clip": {
                        "scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0,
                        "transform": {"x": 0.0, "y": 0.0},
                        "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0
                    },
                    "uniform_scale": {"on": True, "value": 1.0},
                    "material_id": a_mat_id,
                    "extra_material_refs": [a_speed_id, a_placeholder_id, a_canvas_id, a_sound_ch_id, a_mat_color_id, a_vocal_sep_id],
                    "render_index": 0, "keyframe_refs": [],
                    "enable_lut": True, "enable_adjust": True, "enable_hsl": False,
                    "visible": True, "group_id": "",
                    "enable_color_curves": True, "enable_hsl_curves": True,
                    "track_render_index": 0,
                    "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
                    "enable_color_wheels": True, "track_attribute": 0,
                    "is_placeholder": False, "template_id": "",
                    "enable_smart_color_adjust": False, "template_scene": "default",
                    "common_keyframes": [], "caption_info": None,
                    "responsive_layout": {
                        "enable": False, "target_follow": "",
                        "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0
                    },
                    "enable_color_match_adjust": False, "enable_color_correct_adjust": False,
                    "enable_adjust_mask": False, "raw_segment_id": "",
                    "lyric_keyframes": None, "enable_video_mask": True,
                    "digital_human_template_group_id": "", "color_correct_alg_result": "",
                    "source": "segmentsourcenormal",
                    "enable_mask_stroke": False, "enable_mask_shadow": False,
                })
                
                audio_materials_list.append({
                    "id": a_mat_id, "type": "extract_music",
                    "duration": seg_dur_us, "path": seg_wav_abs,
                    "category_id": "", "category_name": "local",
                    "app_id": 0, "check_flag": 1, "effect_id": "", "formula_id": "",
                    "intensifies_path": "", "local_material_id": str(uuid.uuid4()),
                    "music_id": "", "name": os.path.basename(seg_wav),
                    "request_id": "", "team_id": "", "source_platform": 0,
                    "search_id": "", "source_from": "",
                })
                
                # Material child objects
                speeds_list.append({"id": a_speed_id, "type": "speed", "mode": 0, "speed": 1.0, "curve_speed": None})
                canvases_list.append({"id": a_canvas_id, "type": "canvas_color", "color": "", "blur": 0.0, "image": "", "album_image": "", "image_id": "", "image_name": "", "source_platform": 0, "team_id": ""})
                placeholder_infos_list.append({"id": a_placeholder_id, "type": "placeholder_info", "meta_type": "none", "res_path": "", "res_text": "", "error_path": "", "error_text": ""})
                sound_channel_list.append({"id": a_sound_ch_id, "type": "none", "audio_channel_mapping": 0, "is_config_open": False})
                material_colors_list.append({"id": a_mat_color_id, "is_color_clip": False, "is_gradient": False, "solid_color": "", "gradient_colors": [], "gradient_percents": [], "gradient_angle": 90.0, "width": 0.0, "height": 0.0})
                vocal_separations_list.append({"id": a_vocal_sep_id, "type": "vocal_separation", "choice": 0, "removed_sounds": [], "time_range": None, "production_path": "", "final_algorithm": "", "enter_from": ""})
            
            self.progress.emit(100, f"🔊 CapCut Audio Edit: {len(audio_segments_list)} segments riêng trên timeline")
        else:
            # === Chế độ bình thường: 1 audio segment ghép ===
            audio_seg_id = _uid()
            audio_speed_id = _uid()
            audio_canvas_id = _uid()
            audio_placeholder_id = _uid()
            audio_sound_ch_id = _uid()
            audio_mat_color_id = _uid()
            audio_vocal_sep_id = _uid()

            audio_segment = {
                "id": audio_seg_id,
                "source_timerange": {"start": 0, "duration": audio_duration_us},
                "target_timerange": {"start": 0, "duration": audio_duration_us},
                "render_timerange": {"start": 0, "duration": 0},
                "desc": "", "state": 0, "speed": 1.0,
                "is_loop": False, "is_tone_modify": False, "reverse": False,
                "intensifies_audio": False, "cartoon": False,
                "volume": 1.0, "last_nonzero_volume": 1.0,
                "clip": {
                    "scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0,
                    "transform": {"x": 0.0, "y": 0.0},
                    "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0
                },
                "uniform_scale": {"on": True, "value": 1.0},
                "material_id": audio_material_id,
                "extra_material_refs": [audio_speed_id, audio_placeholder_id, audio_canvas_id, audio_sound_ch_id, audio_mat_color_id, audio_vocal_sep_id],
                "render_index": 0, "keyframe_refs": [],
                "enable_lut": True, "enable_adjust": True, "enable_hsl": False,
                "visible": True, "group_id": "",
                "enable_color_curves": True, "enable_hsl_curves": True,
                "track_render_index": 0,
                "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
                "enable_color_wheels": True, "track_attribute": 0,
                "is_placeholder": False, "template_id": "",
                "enable_smart_color_adjust": False, "template_scene": "default",
                "common_keyframes": [], "caption_info": None,
                "responsive_layout": {
                    "enable": False, "target_follow": "",
                    "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0
                },
                "enable_color_match_adjust": False, "enable_color_correct_adjust": False,
                "enable_adjust_mask": False, "raw_segment_id": "",
                "lyric_keyframes": None, "enable_video_mask": True,
                "digital_human_template_group_id": "", "color_correct_alg_result": "",
                "source": "segmentsourcenormal",
                "enable_mask_stroke": False, "enable_mask_shadow": False,
            }
            audio_segments_list = [audio_segment]
            audio_materials_list = [{
                "id": audio_material_id, "type": "extract_music",
                "duration": audio_duration_us, "path": audio_path_abs,
                "category_id": "", "category_name": "local",
                "app_id": 0, "check_flag": 1, "effect_id": "", "formula_id": "",
                "intensifies_path": "", "local_material_id": str(uuid.uuid4()),
                "music_id": "", "name": os.path.basename(audio_path),
                "request_id": "", "team_id": "", "source_platform": 0,
                "search_id": "", "source_from": "",
            }]

            # Audio material child objects
            speeds_list.append({"id": audio_speed_id, "type": "speed", "mode": 0, "speed": 1.0, "curve_speed": None})
            canvases_list.append({"id": audio_canvas_id, "type": "canvas_color", "color": "", "blur": 0.0, "image": "", "album_image": "", "image_id": "", "image_name": "", "source_platform": 0, "team_id": ""})
            placeholder_infos_list.append({"id": audio_placeholder_id, "type": "placeholder_info", "meta_type": "none", "res_path": "", "res_text": "", "error_path": "", "error_text": ""})
            sound_channel_list.append({"id": audio_sound_ch_id, "type": "none", "audio_channel_mapping": 0, "is_config_open": False})
            material_colors_list.append({"id": audio_mat_color_id, "is_color_clip": False, "is_gradient": False, "solid_color": "", "gradient_colors": [], "gradient_percents": [], "gradient_angle": 90.0, "width": 0.0, "height": 0.0})
            vocal_separations_list.append({"id": audio_vocal_sep_id, "type": "vocal_separation", "choice": 0, "removed_sounds": [], "time_range": None, "production_path": "", "final_algorithm": "", "enter_from": ""})

        # === draft_content.json theo format CapCut v7.9 ===
        draft_content = {
            "id": project_id,
            "version": 360000,
            "new_version": "155.0.0",
            "name": "",
            "duration": total_timeline_us,
            "create_time": 0,
            "update_time": 0,
            "fps": 30.0,
            "is_drop_frame_timecode": False,
            "color_space": -1,
            "config": {
                "video_mute": False,
                "record_audio_last_index": 1,
                "extract_audio_last_index": 1,
                "original_sound_last_index": 1,
                "subtitle_recognition_id": "",
                "subtitle_taskinfo": [],
                "lyrics_recognition_id": "",
                "lyrics_taskinfo": [],
                "subtitle_sync": True,
                "lyrics_sync": True,
                "sticker_max_index": 1,
                "adjust_max_index": 1,
                "material_save_mode": 0,
                "export_range": None,
                "maintrack_adsorb": True,
                "combination_max_index": 1,
                "attachment_info": [],
                "zoom_info_params": None,
                "system_font_list": [],
                "multi_language_mode": "none",
                "multi_language_main": "none",
                "multi_language_current": "none",
                "multi_language_list": [],
                "subtitle_keywords_config": None,
                "use_float_render": False
            },
            "canvas_config": {
                "ratio": "original",
                "width": canvas_width,
                "height": canvas_height,
                "background": None
            },
            "tracks": [
                {
                    "id": _uid(),
                    "type": "video",
                    "segments": video_segments,
                    "flag": 0,
                    "attribute": 0,
                    "name": "",
                    "is_default_name": True
                },
                {
                    "id": _uid(),
                    "type": "audio",
                    "segments": audio_segments_list,
                    "flag": 0,
                    "attribute": 0,
                    "name": "",
                    "is_default_name": True
                },
                {
                    "id": _uid(),
                    "type": "text",
                    "segments": text_segments,
                    "flag": 0,
                    "attribute": 0,
                    "name": "",
                    "is_default_name": True
                }
            ],
            "group_container": None,
            "materials": {
                "flowers": [],
                "videos": [{
                    "id": video_material_id,
                    "type": "video",
                    "duration": video_duration_us,
                    "path": video_path_abs,
                    "media_path": "",
                    "local_id": "",
                    "has_audio": True,
                    "reverse_path": "",
                    "intensifies_path": "",
                    "reverse_intensifies_path": "",
                    "intensifies_audio_path": "",
                    "cartoon_path": "",
                    "width": canvas_width,
                    "height": canvas_height,
                    "category_id": "",
                    "category_name": "local",
                    "material_id": "",
                    "material_name": os.path.basename(video_path),
                    "material_url": "",
                    "crop": {
                        "upper_left_x": 0.0, "upper_left_y": 0.0,
                        "upper_right_x": 1.0, "upper_right_y": 0.0,
                        "lower_left_x": 0.0, "lower_left_y": 1.0,
                        "lower_right_x": 1.0, "lower_right_y": 1.0
                    },
                    "crop_ratio": "free",
                    "audio_fade": None,
                    "crop_scale": 1.0,
                    "extra_type_option": 0,
                    "stable": {"stable_level": 0, "matrix_path": "", "time_range": {"start": 0, "duration": 0}},
                    "matting": {"flag": 0, "path": "", "interactiveTime": [], "has_use_quick_brush": False, "strokes": [], "has_use_quick_eraser": False},
                    "source": 0,
                    "source_platform": 0,
                    "formula_id": "",
                    "check_flag": 62978047,
                    "video_algorithm": {"algorithms": [], "time_range": None, "path": ""},
                    "is_unified_beauty_mode": False,
                    "object_locked": None,
                    "smart_motion": None,
                    "freeze": None,
                    "picture_from": "none",
                    "picture_set_category_id": "",
                    "picture_set_category_name": "",
                    "team_id": "",
                    "local_material_id": str(uuid.uuid4()),
                    "origin_material_id": "",
                    "request_id": "",
                    "is_ai_generate_content": False,
                    "is_copyright": False,
                }],
                "tail_leaders": [],
                "audios": audio_materials_list,
                "images": [],
                "texts": text_materials,
                "effects": [],
                "stickers": [],
                "canvases": canvases_list,
                "transitions": [],
                "audio_effects": [],
                "audio_fades": [],
                "beats": [],
                "material_animations": [],
                "placeholders": [],
                "placeholder_infos": placeholder_infos_list,
                "speeds": speeds_list,
                "common_mask": [],
                "chromas": [],
                "text_templates": [],
                "realtime_denoises": [],
                "audio_pannings": [],
                "audio_pitch_shifts": [],
                "video_trackings": [],
                "hsl": [],
                "drafts": [],
                "color_curves": [],
                "hsl_curves": [],
                "primary_color_wheels": [],
                "log_color_wheels": [],
                "video_effects": [],
                "audio_balances": [],
                "handwrites": [],
                "manual_deformations": [],
                "manual_beautys": [],
                "plugin_effects": [],
                "sound_channel_mappings": sound_channel_list,
                "green_screens": [],
                "shapes": [],
                "material_colors": material_colors_list,
                "digital_humans": [],
                "smart_crops": [],
                "ai_translates": [],
                "audio_track_indexes": [],
                "loudnesses": [],
                "vocal_beautifys": [],
                "vocal_separations": vocal_separations_list,
                "smart_relights": [],
                "time_marks": [],
                "multi_language_refs": [],
                "video_shadows": [],
                "video_strokes": [],
                "video_radius": [],
                "flowers": [],
            },
            "keyframes": {
                "videos": [], "audios": [], "texts": [],
                "stickers": [], "filters": [], "adjusts": [],
                "handwrites": [], "effects": []
            },
            "keyframe_graph_list": [],
            "platform": {
                "os": "windows",
                "os_version": "",
                "app_id": 359289,
                "app_version": "7.9.0",
                "app_source": "cc",
                "device_id": "",
                "hard_disk_id": "",
                "mac_address": ""
            },
            "last_modified_platform": {
                "os": "windows",
                "os_version": "",
                "app_id": 359289,
                "app_version": "7.9.0",
                "app_source": "cc",
                "device_id": "",
                "hard_disk_id": "",
                "mac_address": ""
            },
            "mutable_config": None,
            "cover": None,
            "retouch_cover": None,
            "extra_info": None,
            "relationships": [],
            "render_index_track_mode_on": True,
            "free_render_index_mode_on": False,
            "static_cover_image_path": "",
            "source": "default",
            "time_marks": None,
            "path": "",
            "lyrics_effects": [],
            "draft_type": "video",
        }

        draft_content_path = os.path.join(project_dir, 'draft_content.json')
        with open(draft_content_path, 'w', encoding='utf-8') as f:
            json.dump(draft_content, f, ensure_ascii=False)

        # === draft_info.json ===
        now_ts_sec = int(time.time())
        now_ts_us = int(time.time() * 1_000_000)
        
        draft_info = {
            "all_time_video_crop_mode_used": [],
            "caption_info": None,
            "ce_creative_template_id": "",
            "cloud_package_completed": True,
            "cloud_package_dirty": "",
            "cloud_tutorial_info": "",
            "cover": "",
            "create_time": now_ts_sec,
            "draft_cloud_last_action_download": False,
            "draft_cloud_materials": [],
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": "",
            "draft_deeplink_url": "",
            "draft_enterprise_info": {
                "draft_enterprise_extra": "",
                "draft_enterprise_id": "",
                "draft_enterprise_name": "",
                "enterprise_material": []
            },
            "draft_fold_path": project_dir.replace('\\', '/'),
            "draft_id": project_id,
            "draft_is_ai_shorts": False,
            "draft_is_article_video_draft": False,
            "draft_is_from_deeplink": "",
            "draft_is_invisible": False,
            "draft_materials_copied": False,
            "draft_name": base_name,
            "draft_need_rename": False,
            "draft_new_version": "",
            "draft_removable_storage_device": "",
            "draft_root_path": os.path.dirname(project_dir).replace('\\', '/'),
            "draft_segment_extra_info": None,
            "draft_timeline_materials_size": 0,
            "draft_type": "",
            "is_commerce_music_collection_draft": False,
            "is_tutorial_draft": False,
            "last_modified_platform": {
                "app_id": 359289,
                "app_source": "cc",
                "app_version": "7.9.0",
                "device_id": "",
                "hard_disk_id": "",
                "mac_address": "",
                "os": "windows",
                "os_version": ""
            },
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_modified": "",
            "tm_draft_create": now_ts_sec,
            "tm_draft_modified": now_ts_sec,
            "tm_draft_removed": 0,
            "tm_duration": total_timeline_us
        }

        draft_info_path = os.path.join(project_dir, 'draft_info.json')
        with open(draft_info_path, 'w', encoding='utf-8') as f:
            json.dump(draft_info, f, ensure_ascii=False, indent=2)

        # === draft_meta_info.json ===
        draft_meta_info = {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "cloud_package_completed_time": "",
            "draft_cloud_capcut_purchase_info": "",
            "draft_cloud_last_action_download": False,
            "draft_cloud_package_type": "",
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": "",
            "draft_deeplink_url": "",
            "draft_enterprise_info": {
                "draft_enterprise_extra": "", "draft_enterprise_id": "",
                "draft_enterprise_name": "", "enterprise_material": []
            },
            "draft_fold_path": project_dir.replace('\\', '/'),
            "draft_id": project_id,
            "draft_is_ae_produce": False,
            "draft_is_ai_packaging_used": False,
            "draft_is_ai_shorts": False,
            "draft_is_ai_translate": False,
            "draft_is_article_video_draft": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_from_deeplink": "false",
            "draft_is_invisible": False,
            "draft_is_web_article_video": False,
            "draft_materials": [
                {"type": 0, "value": [
                    {
                        "ai_group_type": "", "create_time": now_ts_sec,
                        "duration": int(video_duration * 1000),
                        "extra_info": os.path.basename(video_path),
                        "file_Path": video_path_abs,
                        "height": canvas_height,
                        "id": str(uuid.uuid4()),
                        "import_time": now_ts_sec, "import_time_ms": now_ts_us,
                        "item_source": 1, "md5": "", "metetype": "video",
                        "roughcut_time_range": {"duration": int(video_duration * 1000), "start": 0},
                        "sub_time_range": {"duration": -1, "start": -1},
                        "type": 0, "width": canvas_width
                    }
                ]},
                {"type": 1, "value": []}, {"type": 2, "value": []},
                {"type": 3, "value": []}, {"type": 6, "value": []},
                {"type": 7, "value": []}, {"type": 8, "value": []}
            ],
            "draft_materials_copied_info": [],
            "draft_name": base_name,
            "draft_need_rename_folder": False,
            "draft_new_version": "",
            "draft_removable_storage_device": "",
            "draft_root_path": os.path.dirname(project_dir).replace('\\', '/'),
            "draft_segment_extra_info": [],
            "draft_timeline_materials_size_": 0,
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_entry_id": -1,
            "tm_draft_cloud_modified": 0,
            "tm_draft_cloud_parent_entry_id": -1,
            "tm_draft_cloud_space_id": -1,
            "tm_draft_cloud_user_id": -1,
            "tm_draft_create": now_ts_us,
            "tm_draft_modified": now_ts_us,
            "tm_draft_removed": 0,
            "tm_duration": total_timeline_us
        }
        
        with open(os.path.join(project_dir, 'draft_meta_info.json'), 'w', encoding='utf-8') as f:
            json.dump(draft_meta_info, f, ensure_ascii=False)

        # === File phụ trợ ===
        with open(os.path.join(project_dir, 'draft_agency_config.json'), 'w', encoding='utf-8') as f:
            json.dump({"is_auto_agency_enabled": False, "is_auto_agency_popup": False, "is_single_agency_mode": False, "marterials": None, "use_converter": False, "video_resolution": 720}, f, ensure_ascii=False)

        with open(os.path.join(project_dir, 'draft_settings'), 'w', encoding='utf-8') as f:
            f.write(f"[General]\ndraft_create_time={now_ts_sec}\ndraft_last_edit_time={now_ts_sec}\nreal_edit_seconds=0\nreal_edit_keys=0\ncloud_last_modify_platform=windows\n")

        self.progress.emit(100, f"📁 Dự án CapCut đã được tạo tại: {project_dir}")

        # === Đăng ký vào CapCut ===
        try:
            capcut_meta_dir = os.path.join(
                os.environ.get('LOCALAPPDATA', ''),
                'CapCut', 'User Data', 'Projects', 'com.lveditor.draft'
            )
            root_meta_path = os.path.join(capcut_meta_dir, 'root_meta_info.json')
            
            if os.path.exists(root_meta_path):
                with open(root_meta_path, 'r', encoding='utf-8') as f:
                    root_meta = json.load(f)
                
                # Tìm thư mục CapCut Drafts thực tế
                capcut_drafts_dir = None
                for existing_draft in root_meta.get('all_draft_store', []):
                    existing_root = existing_draft.get('draft_root_path', '')
                    if existing_root and os.path.exists(existing_root):
                        capcut_drafts_dir = existing_root.replace('\\', '/')
                        break
                
                if not capcut_drafts_dir:
                    capcut_drafts_dir = os.path.join(os.path.expanduser('~'), 'CapCut Drafts').replace('\\', '/')
                    os.makedirs(capcut_drafts_dir, exist_ok=True)
                
                # Xóa entry cũ nếu có
                root_meta['all_draft_store'] = [
                    d for d in root_meta['all_draft_store']
                    if f"capcut_{base_name}" not in d.get('draft_fold_path', '')
                ]
                
                # Copy project vào CapCut Drafts
                target_project_dir = os.path.join(capcut_drafts_dir, f"capcut_{base_name}")
                if os.path.abspath(project_dir) != os.path.abspath(target_project_dir):
                    if os.path.exists(target_project_dir):
                        shutil.rmtree(target_project_dir)
                    shutil.copytree(project_dir, target_project_dir)
                
                # Cập nhật paths trong file đã copy
                target_path_fwd = target_project_dir.replace('\\', '/')
                for jf in ['draft_meta_info.json', 'draft_info.json']:
                    jp = os.path.join(target_project_dir, jf)
                    if os.path.exists(jp):
                        with open(jp, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if 'draft_fold_path' in data:
                            data['draft_fold_path'] = target_path_fwd
                        if 'draft_root_path' in data:
                            data['draft_root_path'] = capcut_drafts_dir
                        # Detect removable storage device
                        if len(target_path_fwd) >= 2 and target_path_fwd[1] == ':':
                            data['draft_removable_storage_device'] = target_path_fwd[:2]
                        with open(jp, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2 if jf == 'draft_info.json' else None)
                
                new_entry = {
                    "cloud_draft_cover": False,
                    "cloud_draft_sync": False,
                    "draft_cloud_last_action_download": False,
                    "draft_cloud_purchase_info": "",
                    "draft_cloud_template_id": "",
                    "draft_cloud_tutorial_info": "",
                    "draft_cloud_videocut_purchase_info": "",
                    "draft_cover": "",
                    "draft_fold_path": target_path_fwd,
                    "draft_id": project_id,
                    "draft_is_ai_shorts": False,
                    "draft_is_cloud_temp_draft": False,
                    "draft_is_invisible": False,
                    "draft_is_web_article_video": False,
                    "draft_json_file": f"{target_path_fwd}/draft_content.json",
                    "draft_name": base_name,
                    "draft_new_version": "",
                    "draft_root_path": capcut_drafts_dir,
                    "draft_timeline_materials_size": 0,
                    "draft_type": "",
                    "draft_web_article_video_enter_from": "",
                    "streaming_edit_draft_ready": True,
                    "tm_draft_cloud_completed": "",
                    "tm_draft_cloud_entry_id": -1,
                    "tm_draft_cloud_modified": 0,
                    "tm_draft_cloud_parent_entry_id": -1,
                    "tm_draft_cloud_space_id": -1,
                    "tm_draft_cloud_user_id": -1,
                    "tm_draft_create": now_ts_us,
                    "tm_draft_modified": now_ts_us,
                    "tm_draft_removed": 0,
                    "tm_duration": total_timeline_us
                }
                
                root_meta['all_draft_store'].insert(0, new_entry)
                root_meta['draft_ids'] = root_meta.get('draft_ids', 0) + 1
                
                with open(root_meta_path, 'w', encoding='utf-8') as f:
                    json.dump(root_meta, f, ensure_ascii=False)
                
                self.progress.emit(100, f"   ✅ Đã đăng ký vào CapCut: {target_path_fwd}")
            else:
                self.progress.emit(100, f"   ⚠️ Không tìm thấy CapCut.")
        except Exception as e:
            self.progress.emit(100, f"   ⚠️ Lỗi đăng ký CapCut: {e}")
        

        return project_dir


# ================== GIAO DIỆN ỨNG DỤNG ==================
class SrtToMp3App(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MyCompany", "SrtToMp3App_v3.3")
        self.thread = None
        self.worker = None
        self.initUI()
        self.load_settings()
        self.update_ui_for_provider() 
        
        # Chặn wheel event trên tất cả ComboBox/Slider để tránh đổi giá trị khi scroll
        self._wheel_guard = WheelGuard(self)
        for widget in self.findChildren(QComboBox):
            widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            widget.installEventFilter(self._wheel_guard)
        for widget in self.findChildren(QSlider):
            widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            widget.installEventFilter(self._wheel_guard)

    def initUI(self):
        self.setWindowTitle('Chuyển Đổi SRT sang MP3 v3.4 (CapCut)')
        self.setGeometry(300, 300, 600, 850)
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(4)
        
        # ScrollArea cho phần config + conversion (tránh overlap khi phóng to)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_content = QWidget()
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(4, 4, 4, 4)

        config_group = QGroupBox("⚙️ Cấu hình")
        config_layout = QFormLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["TikTok TTS", "FPT AI", "ElevenLabs"])
        self.provider_combo.currentIndexChanged.connect(self.update_ui_for_provider)
        config_layout.addRow("Nhà cung cấp TTS:", self.provider_combo)

        self.stacked_widget = QStackedWidget()

        tiktok_widget = QWidget()
        tiktok_layout = QVBoxLayout()
        tiktok_form_layout = QFormLayout()
        
        self.tiktok_session_id_input = QLineEdit()
        self.tiktok_session_id_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.tiktok_session_id_input.setPlaceholderText("Dán sessionid TikTok của bạn vào đây")
        tiktok_form_layout.addRow("TikTok Session ID:", self.tiktok_session_id_input)
        
        self.tiktok_voice_combo = QComboBox()
        for name in sorted(TIKTOK_VOICES.keys()):
            self.tiktok_voice_combo.addItem(name, TIKTOK_VOICES[name])
        tiktok_form_layout.addRow("Giọng đọc TikTok:", self.tiktok_voice_combo)
        
        tiktok_layout.addLayout(tiktok_form_layout)

        test_group = QGroupBox("Test Giọng Đọc")
        test_layout = QHBoxLayout()
        self.test_text_input = QLineEdit("Xin chào, đây là giọng đọc thử nghiệm.")
        self.test_voice_button = QPushButton("Test")
        self.test_voice_button.clicked.connect(self.handle_test_voice_click)
        test_layout.addWidget(self.test_text_input)
        test_layout.addWidget(self.test_voice_button)
        test_group.setLayout(test_layout)
        tiktok_layout.addWidget(test_group)
        
        tiktok_widget.setLayout(tiktok_layout)
        tiktok_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.stacked_widget.addWidget(tiktok_widget)

        fpt_widget = QWidget()
        fpt_main_layout = QVBoxLayout()
        fpt_form_layout = QFormLayout()
        self.fpt_api_key_input = QLineEdit()
        self.fpt_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.fpt_api_key_input.setPlaceholderText("Dán API key từ fpt.ai/console")
        fpt_form_layout.addRow("FPT API Key:", self.fpt_api_key_input)
        self.fpt_voice_combo = QComboBox()
        for name in sorted(FPT_VOICES.keys()):
            self.fpt_voice_combo.addItem(name, FPT_VOICES[name])
        fpt_form_layout.addRow("Giọng đọc FPT:", self.fpt_voice_combo)
        fpt_main_layout.addLayout(fpt_form_layout)

        fpt_test_group = QGroupBox("Test Giọng Đọc")
        fpt_test_layout = QHBoxLayout()
        self.fpt_test_text_input = QLineEdit("Xin chào, đây là giọng đọc thử nghiệm.")
        self.fpt_test_voice_button = QPushButton("Test")
        self.fpt_test_voice_button.clicked.connect(self.handle_test_fpt_voice_click)
        fpt_test_layout.addWidget(self.fpt_test_text_input)
        fpt_test_layout.addWidget(self.fpt_test_voice_button)
        fpt_test_group.setLayout(fpt_test_layout)
        fpt_main_layout.addWidget(fpt_test_group)

        fpt_widget.setLayout(fpt_main_layout)
        fpt_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.stacked_widget.addWidget(fpt_widget)

        elevenlabs_widget = QWidget()
        elevenlabs_main_layout = QVBoxLayout()
        elevenlabs_form_layout = QFormLayout()
        self.elevenlabs_api_key_input = QLineEdit()
        self.elevenlabs_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.elevenlabs_api_key_input.setPlaceholderText("Dán API key từ elevenlabs.io")
        elevenlabs_form_layout.addRow("ElevenLabs API Key:", self.elevenlabs_api_key_input)
        self.elevenlabs_lang_combo = QComboBox()
        self.elevenlabs_lang_combo.addItems(["🇻🇳 Tiếng Việt", "🇺🇸 English"])
        self.elevenlabs_lang_combo.currentIndexChanged.connect(self._update_elevenlabs_voices)
        elevenlabs_form_layout.addRow("Ngôn ngữ:", self.elevenlabs_lang_combo)
        self.elevenlabs_voice_combo = QComboBox()
        self._update_elevenlabs_voices()
        elevenlabs_form_layout.addRow("Giọng đọc:", self.elevenlabs_voice_combo)
        self.elevenlabs_custom_voice_input = QLineEdit()
        self.elevenlabs_custom_voice_input.setPlaceholderText("Để trống = dùng giọng ở trên. Hoặc dán Voice ID tùy chỉnh")
        elevenlabs_form_layout.addRow("Custom Voice ID:", self.elevenlabs_custom_voice_input)
        elevenlabs_main_layout.addLayout(elevenlabs_form_layout)

        el_test_group = QGroupBox("Test Giọng Đọc")
        el_test_layout = QHBoxLayout()
        self.el_test_text_input = QLineEdit("Xin chào, đây là giọng đọc thử nghiệm.")
        self.el_test_voice_button = QPushButton("Test")
        self.el_test_voice_button.clicked.connect(self.handle_test_elevenlabs_voice_click)
        el_test_layout.addWidget(self.el_test_text_input)
        el_test_layout.addWidget(self.el_test_voice_button)
        el_test_group.setLayout(el_test_layout)
        elevenlabs_main_layout.addWidget(el_test_group)

        elevenlabs_widget.setLayout(elevenlabs_main_layout)
        elevenlabs_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.stacked_widget.addWidget(elevenlabs_widget)
        
        config_layout.addRow(self.stacked_widget)
        self.stacked_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_path_input = QLineEdit()
        ffmpeg_browse_btn = QPushButton("Chọn...")
        ffmpeg_browse_btn.clicked.connect(self.browse_ffmpeg)
        ffmpeg_layout.addWidget(self.ffmpeg_path_input)
        ffmpeg_layout.addWidget(ffmpeg_browse_btn)
        config_layout.addRow("Đường dẫn FFmpeg:", ffmpeg_layout)
        
        config_group.setLayout(config_layout)
        config_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(config_group)

        conversion_group = QGroupBox("🎙️ Chuyển đổi & Tùy chọn")
        conversion_layout = QFormLayout()
        srt_layout = QHBoxLayout()
        self.srt_path_input = QLineEdit(); self.srt_path_input.setReadOnly(True)
        srt_browse_btn = QPushButton("Chọn File SRT..."); srt_browse_btn.clicked.connect(self.browse_srt)
        srt_layout.addWidget(self.srt_path_input); srt_layout.addWidget(srt_browse_btn)
        conversion_layout.addRow("File SRT nguồn:", srt_layout)
        self.output_path_input = QLineEdit()
        conversion_layout.addRow("Tên file MP3 đầu ra:", self.output_path_input)
        
        # --- Tốc độ đọc ---
        speed_layout = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(50)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setSingleStep(5)
        self.speed_slider.setPageStep(10)
        self.speed_slider.setValue(120)
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed_slider.setTickInterval(25)
        self.speed_label = QLabel("1.2x")
        self.speed_label.setFixedWidth(40)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        conversion_layout.addRow("Tốc độ đọc:", speed_layout)

        # --- Số luồng xử lý ---
        from PyQt6.QtWidgets import QSpinBox
        workers_layout = QHBoxLayout()
        self.workers_spin = QSpinBox()
        self.workers_spin.setMinimum(1)
        self.workers_spin.setMaximum(50)
        self.workers_spin.setValue(15)
        self.workers_spin.setToolTip("Số luồng xử lý song song. Nhiều luồng = nhanh hơn nhưng dễ bị rate-limit.")
        workers_layout.addWidget(self.workers_spin)
        workers_lbl = QLabel("(1-50, mặc định 15)")
        workers_lbl.setStyleSheet("color:#888;font-size:10px;")
        workers_layout.addWidget(workers_lbl)
        workers_layout.addStretch()
        conversion_layout.addRow("Số luồng:", workers_layout)

        # --- Kích thước phụ đề ---
        subtitle_size_layout = QHBoxLayout()
        self.subtitle_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.subtitle_size_slider.setMinimum(1)
        self.subtitle_size_slider.setMaximum(20)
        self.subtitle_size_slider.setSingleStep(1)
        self.subtitle_size_slider.setValue(5)
        self.subtitle_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.subtitle_size_slider.setTickInterval(2)
        self.subtitle_size_label = QLabel("5")
        self.subtitle_size_label.setFixedWidth(30)
        self.subtitle_size_slider.valueChanged.connect(lambda v: self.subtitle_size_label.setText(str(v)))
        subtitle_size_layout.addWidget(self.subtitle_size_slider)
        subtitle_size_layout.addWidget(self.subtitle_size_label)
        conversion_layout.addRow("Cỡ phụ đề:", subtitle_size_layout)

        # --- [NÂNG CẤP] Nhóm các checkbox tùy chọn ---
        options_layout = QVBoxLayout()
        self.rename_temp_files_checkbox = QCheckBox("Sắp xếp file trong thư mục temp để dễ dàng chỉnh sửa")
        self.rename_temp_files_checkbox.setChecked(False)
        options_layout.addWidget(self.rename_temp_files_checkbox)

        self.delete_temp_checkbox = QCheckBox("Tự động xóa thư mục temp sau khi hoàn thành")
        self.delete_temp_checkbox.setChecked(True)
        options_layout.addWidget(self.delete_temp_checkbox)

        self.audio_edit_checkbox = QCheckBox("🔊 Audio Edit (xuất từng segment riêng, không ghép)")
        self.audio_edit_checkbox.setChecked(False)
        options_layout.addWidget(self.audio_edit_checkbox)

        # --- Chế độ Lồng Tiếng Đa Giọng ---
        self.dubbing_checkbox = QCheckBox("🎭 Lồng tiếng đa giọng (mỗi nhân vật 1 giọng riêng)")
        self.dubbing_checkbox.setChecked(False)
        self.dubbing_checkbox.setToolTip(
            "Khi bật: đọc tag {Tên NV} trong SRT để dùng giọng khác nhau.\n"
            "Cần dịch với '🎭 Nhận diện nhân vật nói' ở tab Dịch trước."
        )
        self.dubbing_checkbox.stateChanged.connect(self._on_dubbing_toggled)
        options_layout.addWidget(self.dubbing_checkbox)

        # Panel lồng tiếng — chỉ hiện nút + label trạng thái
        self.dubbing_panel = QWidget()
        dubbing_row = QHBoxLayout(self.dubbing_panel)
        dubbing_row.setContentsMargins(0, 4, 0, 4)
        
        self.btn_scan_chars = QPushButton("🔍 Quét nhân vật từ SRT")
        self.btn_scan_chars.setFixedHeight(32)
        self.btn_scan_chars.setStyleSheet("font-weight: bold; padding: 4px 12px;")
        self.btn_scan_chars.clicked.connect(self._scan_characters)
        dubbing_row.addWidget(self.btn_scan_chars)
        
        self.lbl_dubbing_status = QLabel("Chưa quét")
        self.lbl_dubbing_status.setStyleSheet("color: #888; font-style: italic;")
        dubbing_row.addWidget(self.lbl_dubbing_status)
        
        dubbing_row.addStretch()
        lbl_default = QLabel("Giọng mặc định:")
        dubbing_row.addWidget(lbl_default)
        self.dubbing_default_combo = QComboBox()
        self.dubbing_default_combo.setMinimumWidth(200)
        dubbing_row.addWidget(self.dubbing_default_combo)
        
        self.dubbing_panel.setVisible(False)
        # Lưu voice mapping data (sẽ được populate bởi dialog)
        self._dubbing_voice_mapping = {}
        conversion_layout.addRow(self.dubbing_panel)

        # --- CapCut Project ---
        self.capcut_checkbox = QCheckBox("🎬 Tạo dự án CapCut (cần chọn file video)")
        self.capcut_checkbox.setChecked(False)
        self.capcut_checkbox.stateChanged.connect(self._on_capcut_toggled)
        options_layout.addWidget(self.capcut_checkbox)

        video_layout = QHBoxLayout()
        self.video_path_input = QLineEdit()
        self.video_path_input.setReadOnly(True)
        self.video_path_input.setPlaceholderText("Chọn file video gốc...")
        self.video_browse_btn = QPushButton("Chọn Video...")
        self.video_browse_btn.clicked.connect(self.browse_video)
        video_layout.addWidget(self.video_path_input)
        video_layout.addWidget(self.video_browse_btn)
        self.video_path_input.setEnabled(False)
        self.video_browse_btn.setEnabled(False)
        conversion_layout.addRow("File Video:", video_layout)
        
        conversion_layout.addRow(options_layout)

        conversion_group.setLayout(conversion_layout)
        conversion_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(conversion_group)

        self.start_button = QPushButton("🚀 Bắt Đầu Chuyển Đổi")
        self.start_button.clicked.connect(self.start_conversion)
        self.start_button.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        main_layout.addWidget(self.start_button)
        
        # Đẩy content lên trên
        main_layout.addStretch()
        
        # Kết thúc scroll area
        scroll.setWidget(scroll_content)
        outer_layout.addWidget(scroll, 3)  # scroll chiếm 3 phần
        
        # Progress bar + Log nằm NGOÀI scroll
        self.progress_bar = QProgressBar()
        outer_layout.addWidget(self.progress_bar)

        log_group = QGroupBox("Nhật ký tác vụ")
        log_layout = QVBoxLayout(); self.log_edit = QTextEdit(); self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(80)
        log_layout.addWidget(self.log_edit); log_group.setLayout(log_layout)
        outer_layout.addWidget(log_group, 1)

        self.setLayout(outer_layout)

    def _on_speed_changed(self, value):
        self.speed_label.setText(f"{value / 100:.1f}x")

    def _on_dubbing_toggled(self, state):
        """Bật/tắt panel lồng tiếng đa giọng."""
        visible = state == 2  # Qt.CheckState.Checked
        self.dubbing_panel.setVisible(visible)
        if visible:
            self._update_dubbing_voices()

    def _update_dubbing_voices(self):
        """Cập nhật dropdown giọng cho default combo."""
        provider = self.provider_combo.currentText()
        voice_dict = {}
        if provider == 'FPT AI':
            voice_dict = FPT_VOICES
        elif provider == 'ElevenLabs':
            lang = self.elevenlabs_lang_combo.currentText() if hasattr(self, 'elevenlabs_lang_combo') else 'Tiếng Việt'
            voice_dict = ELEVENLABS_VOICES_VI if 'Việt' in lang else ELEVENLABS_VOICES_EN
        elif provider == 'TikTok TTS':
            voice_dict = TIKTOK_VOICES
        self.dubbing_default_combo.clear()
        for name, vid in voice_dict.items():
            self.dubbing_default_combo.addItem(name, vid)
        for i in range(self.dubbing_default_combo.count()):
            txt = self.dubbing_default_combo.itemText(i)
            if 'Male' in txt or 'Nam' in txt:
                if 'Female' not in txt and 'Nữ' not in txt:
                    self.dubbing_default_combo.setCurrentIndex(i)
                    break

    def _scan_characters(self):
        """Quét SRT rồi mở popup dialog to cho user chỉnh giọng từng nhân vật."""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        from collections import Counter
        
        srt_path = self.srt_path_input.text()
        if not srt_path or not os.path.exists(srt_path):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file SRT trước!")
            return
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không đọc được file: {e}")
            return
        
        tags = re.findall(r'\{(.+?)\}', content)
        unique_chars = list(dict.fromkeys(tags))
        if not unique_chars:
            QMessageBox.information(self, "Không tìm thấy",
                "Không tìm thấy tag {Tên NV} trong file SRT.\n"
                "Hãy dịch với '🎭 Nhận diện nhân vật nói' bật trước!")
            return
        
        tag_counts = Counter(tags)
        
        # Voice dict theo provider hiện tại
        provider = self.provider_combo.currentText()
        voice_dict = {}
        if provider == 'FPT AI':
            voice_dict = FPT_VOICES
        elif provider == 'ElevenLabs':
            lang = self.elevenlabs_lang_combo.currentText() if hasattr(self, 'elevenlabs_lang_combo') else 'Tiếng Việt'
            voice_dict = ELEVENLABS_VOICES_VI if 'Việt' in lang else ELEVENLABS_VOICES_EN
        elif provider == 'TikTok TTS':
            voice_dict = TIKTOK_VOICES
        
        voice_names = list(voice_dict.keys())
        default_male_idx, default_female_idx = 0, 0
        for i, vn in enumerate(voice_names):
            vl = vn.lower()
            if default_male_idx == 0 and ('male' in vl or 'nam' in vl) and 'female' not in vl and 'nữ' not in vl:
                default_male_idx = i
            if default_female_idx == 0 and ('female' in vl or 'nữ' in vl):
                default_female_idx = i
        
        female_kw = ['娘', '女', '妹', '夫人', 'uyển', 'nhi', 'băng', 'loan', 'lan', 'trang', 'hương', 'liên', 'yến']
        narrator_kw = ['旁白', 'narrator', '旁', 'người kể']
        
        # ===== POPUP DIALOG =====
        dlg = QDialog(self)
        dlg.setWindowTitle("🎭 Chỉnh giọng cho từng nhân vật")
        dlg.setMinimumSize(850, 400)
        dlg.resize(900, min(550, 180 + len(unique_chars) * 45))
        lay = QVBoxLayout(dlg)
        
        lay.addWidget(QLabel(f"Tìm thấy <b>{len(unique_chars)}</b> nhân vật. Chọn <b>provider + giọng</b> cho từng người:"))
        
        # Hàm lấy voice dict theo provider
        def get_voices_for(prov):
            if prov == 'FPT AI':
                return FPT_VOICES
            elif prov == 'ElevenLabs':
                lang = self.elevenlabs_lang_combo.currentText() if hasattr(self, 'elevenlabs_lang_combo') else 'Tiếng Việt'
                return ELEVENLABS_VOICES_VI if 'Việt' in lang else ELEVENLABS_VOICES_EN
            elif prov == 'TikTok TTS':
                return TIKTOK_VOICES
            return {}
        
        providers = ['TikTok TTS', 'FPT AI', 'ElevenLabs']
        current_provider = self.provider_combo.currentText()
        
        tbl = QTableWidget(len(unique_chars), 5)
        tbl.setHorizontalHeaderLabels(["Nhân vật", "Câu thoại", "Giới tính", "Provider", "Giọng đọc"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        
        def on_provider_changed(row_idx, provider_combo, voice_combo):
            """Khi đổi provider → cập nhật danh sách giọng."""
            prov = provider_combo.currentText()
            vd = get_voices_for(prov)
            voice_combo.clear()
            for vn, vid in vd.items():
                voice_combo.addItem(vn, vid)
            # Auto chọn giọng nam/nữ theo giới tính nhân vật
            gender_item = tbl.item(row_idx, 2)
            if gender_item:
                gt = gender_item.text()
                vnames = list(vd.keys())
                for i, vn in enumerate(vnames):
                    vl = vn.lower()
                    if '♀' in gt or 'Nữ' in gt:
                        if 'female' in vl or 'nữ' in vl:
                            voice_combo.setCurrentIndex(i)
                            return
                    else:
                        if ('male' in vl or 'nam' in vl) and 'female' not in vl and 'nữ' not in vl:
                            voice_combo.setCurrentIndex(i)
                            return
        
        for row, cname in enumerate(unique_chars):
            it_name = QTableWidgetItem(cname)
            it_name.setFlags(it_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(row, 0, it_name)
            
            it_count = QTableWidgetItem(str(tag_counts.get(cname, 0)))
            it_count.setFlags(it_count.flags() & ~Qt.ItemFlag.ItemIsEditable)
            it_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tbl.setItem(row, 1, it_count)
            
            cl = cname.lower()
            is_f = any(k in cl for k in female_kw)
            is_n = any(k in cl for k in narrator_kw)
            gender = "📢 Narrator" if is_n else ("♀️ Nữ" if is_f else "♂️ Nam")
            vidx = default_male_idx if (is_n or not is_f) else default_female_idx
            
            it_g = QTableWidgetItem(gender)
            it_g.setFlags(it_g.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(row, 2, it_g)
            
            # Provider dropdown
            prov_cb = QComboBox()
            for p in providers:
                prov_cb.addItem(p)
            
            # Voice dropdown
            vcb = QComboBox()
            
            # Khôi phục từ mapping trước đó nếu có
            saved = self._dubbing_voice_mapping.get(cname, {})
            if isinstance(saved, dict) and 'provider' in saved:
                saved_prov = saved['provider']
                prov_idx = prov_cb.findText(saved_prov)
                prov_cb.setCurrentIndex(prov_idx if prov_idx >= 0 else providers.index(current_provider))
                vd = get_voices_for(saved_prov)
                for vn, vid in vd.items():
                    vcb.addItem(vn, vid)
                si = vcb.findData(saved.get('voice_id'))
                vcb.setCurrentIndex(si if si >= 0 else 0)
            else:
                prov_cb.setCurrentIndex(providers.index(current_provider) if current_provider in providers else 0)
                for vn, vid in voice_dict.items():
                    vcb.addItem(vn, vid)
                vcb.setCurrentIndex(vidx)
            
            # Kết nối signal: đổi provider → đổi voice list
            r = row  # capture
            prov_cb.currentIndexChanged.connect(lambda _, r=r: on_provider_changed(
                r, tbl.cellWidget(r, 3), tbl.cellWidget(r, 4)))
            
            tbl.setCellWidget(row, 3, prov_cb)
            tbl.setCellWidget(row, 4, vcb)
        
        lay.addWidget(tbl)
        
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("✅ Xác nhận")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("❌ Hủy")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._dubbing_voice_mapping = {}
            for row in range(tbl.rowCount()):
                ni = tbl.item(row, 0)
                prov_cb = tbl.cellWidget(row, 3)
                vcb = tbl.cellWidget(row, 4)
                if ni and isinstance(prov_cb, QComboBox) and isinstance(vcb, QComboBox):
                    self._dubbing_voice_mapping[ni.text()] = {
                        'provider': prov_cb.currentText(),
                        'voice_id': vcb.currentData(),
                        'voice_name': vcb.currentText()
                    }
            names_str = ', '.join(unique_chars[:3])
            if len(unique_chars) > 3:
                names_str += f' (+{len(unique_chars)-3})'
            self.lbl_dubbing_status.setText(f"✅ {len(unique_chars)} NV: {names_str}")
            self.lbl_dubbing_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.log_edit.append(f"\n🎭 Đã cấu hình giọng cho {len(unique_chars)} nhân vật:")
            for cn in unique_chars:
                info = self._dubbing_voice_mapping.get(cn, {})
                prov = info.get('provider', '?')
                vname = info.get('voice_name', '?')
                self.log_edit.append(f"  • {cn}: {prov} → {vname} ({tag_counts.get(cn, 0)} câu)")
            self.log_edit.append("→ Sẵn sàng chuyển đổi!")

    def _update_elevenlabs_voices(self):
        """Cập nhật danh sách giọng đọc ElevenLabs theo ngôn ngữ đã chọn."""
        self.elevenlabs_voice_combo.clear()
        lang = self.elevenlabs_lang_combo.currentText()
        if 'English' in lang:
            voices = ELEVENLABS_VOICES_EN
        else:
            voices = ELEVENLABS_VOICES_VI
        for name in sorted(voices.keys()):
            self.elevenlabs_voice_combo.addItem(name, voices[name])

    def update_ui_for_provider(self):
        provider = self.provider_combo.currentText()
        if provider == "TikTok TTS":
            self.stacked_widget.setCurrentIndex(0)
        elif provider == "FPT AI":
            self.stacked_widget.setCurrentIndex(1)
        elif provider == "ElevenLabs":
            self.stacked_widget.setCurrentIndex(2)
            
    def handle_test_voice_click(self):
        # Lấy tất cả giá trị từ GUI trong main thread
        text = self.test_text_input.text().strip()
        session_id = self.tiktok_session_id_input.text().strip()
        voice_code = self.tiktok_voice_combo.currentData()
        ffmpeg_path = self.ffmpeg_path_input.text().strip()
        threading.Thread(target=self._test_voice_worker, args=(text, session_id, voice_code, ffmpeg_path), daemon=True).start()

    def _test_voice_worker(self, text, session_id, voice_code, ffmpeg_path):
        if not text or not session_id:
            self.show_message_signal.emit("Thiếu thông tin", "Vui lòng nhập Session ID và văn bản để test.", "warning")
            return

        self.test_voice_button.setEnabled(False)
        self.test_voice_button.setText("...")
        
        import tempfile
        test_file = None
        try:
            audio_data = self._call_tiktok_api_for_test(text, session_id, voice_code)
            if audio_data:
                # Dùng thư mục temp hệ thống để tránh lỗi permission
                fd, test_file = tempfile.mkstemp(suffix='.mp3', prefix='tts_test_')
                with os.fdopen(fd, 'wb') as f:
                    f.write(audio_data)
                
                # Dùng ffplay (có sẵn cùng FFmpeg) để phát âm thanh
                ffplay_bin = os.path.join(os.path.dirname(ffmpeg_path), 'ffplay.exe')
                if os.path.exists(ffplay_bin):
                    subprocess.run(
                        [ffplay_bin, '-nodisp', '-autoexit', '-loglevel', 'quiet', test_file],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    # Fallback: mở bằng trình phát mặc định của Windows
                    os.startfile(test_file)
                    time.sleep(3)
            else:
                 self.show_message_signal.emit("Lỗi", "Không nhận được dữ liệu âm thanh từ API. Vui lòng kiểm tra lại Session ID và kết nối mạng.", "critical")

        except Exception as e:
            self.show_message_signal.emit("Lỗi", f"Không thể phát âm thanh: {e}", "critical")
        finally:
            if test_file and os.path.exists(test_file):
                try:
                    os.remove(test_file)
                except Exception:
                    pass
            self.test_voice_button.setEnabled(True)
            self.test_voice_button.setText("Test")
            
    def _call_tiktok_api_for_test(self, text: str, session_id: str, voice: str):
        endpoints = [
            'https://tiktok-tts.weilnet.workers.dev/api/generation',
            'https://countik.com/api/text/speech',
            'https://gesserit.co/api/tiktok-tts',
        ]
        headers = {'Content-Type': 'application/json'}
        data = {'text': text, 'voice': voice}
        cookies = {'sessionid': session_id}
        for url in endpoints:
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data), cookies=cookies, timeout=20)
                response.raise_for_status()
                json_response = response.json()
                if json_response.get("data"):
                    return base64.b64decode(json_response["data"])
            except Exception:
                continue
        return None

    # ── FPT AI Test Voice ──
    def handle_test_fpt_voice_click(self):
        text = self.fpt_test_text_input.text().strip()
        api_key = self.fpt_api_key_input.text().strip()
        voice_code = self.fpt_voice_combo.currentData()
        ffmpeg_path = self.ffmpeg_path_input.text().strip()
        threading.Thread(target=self._test_fpt_voice_worker, args=(text, api_key, voice_code, ffmpeg_path), daemon=True).start()

    def _test_fpt_voice_worker(self, text, api_key, voice_code, ffmpeg_path):
        if not text or not api_key:
            self.show_message_signal.emit("Thiếu thông tin", "Vui lòng nhập FPT API Key và văn bản để test.", "warning")
            return

        self.fpt_test_voice_button.setEnabled(False)
        self.fpt_test_voice_button.setText("...")

        import tempfile
        test_file = None
        try:
            audio_data = self._call_fpt_api_for_test(text, api_key, voice_code)
            if audio_data:
                fd, test_file = tempfile.mkstemp(suffix='.mp3', prefix='tts_test_fpt_')
                with os.fdopen(fd, 'wb') as f:
                    f.write(audio_data)

                ffplay_bin = os.path.join(os.path.dirname(ffmpeg_path), 'ffplay.exe')
                if os.path.exists(ffplay_bin):
                    subprocess.run(
                        [ffplay_bin, '-nodisp', '-autoexit', '-loglevel', 'quiet', test_file],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    os.startfile(test_file)
                    time.sleep(3)
            else:
                self.show_message_signal.emit("Lỗi", "Không nhận được dữ liệu âm thanh từ FPT AI. Vui lòng kiểm tra lại API Key.", "critical")

        except Exception as e:
            self.show_message_signal.emit("Lỗi", f"Không thể phát âm thanh FPT: {e}", "critical")
        finally:
            if test_file and os.path.exists(test_file):
                try:
                    os.remove(test_file)
                except Exception:
                    pass
            self.fpt_test_voice_button.setEnabled(True)
            self.fpt_test_voice_button.setText("Test")

    def _call_fpt_api_for_test(self, text: str, api_key: str, voice: str = 'banmai'):
        url = 'https://api.fpt.ai/hmi/tts/v5'
        headers = {'api-key': api_key, 'voice': voice, 'speed': '0'}
        try:
            response = requests.post(url, headers=headers, data=text.encode('utf-8'), timeout=30)
            response.raise_for_status()
            json_response = response.json()
            audio_url = json_response.get('async')
            if not audio_url:
                return None
            for _ in range(15):
                time.sleep(1)
                try:
                    audio_resp = requests.get(audio_url, timeout=15)
                    if audio_resp.status_code == 200 and len(audio_resp.content) > 1000:
                        return audio_resp.content
                except Exception:
                    pass
        except Exception:
            return None
        return None

    # ── ElevenLabs Test Voice ──
    def handle_test_elevenlabs_voice_click(self):
        text = self.el_test_text_input.text().strip()
        api_key = self.elevenlabs_api_key_input.text().strip()
        voice_id = self.elevenlabs_voice_combo.currentData()
        custom_id = self.elevenlabs_custom_voice_input.text().strip()
        if custom_id:
            voice_id = custom_id
        ffmpeg_path = self.ffmpeg_path_input.text().strip()
        threading.Thread(target=self._test_elevenlabs_voice_worker, args=(text, api_key, voice_id, ffmpeg_path), daemon=True).start()

    def _test_elevenlabs_voice_worker(self, text, api_key, voice_id, ffmpeg_path):
        if not text or not api_key:
            self.show_message_signal.emit("Thiếu thông tin", "Vui lòng nhập ElevenLabs API Key và văn bản để test.", "warning")
            return
        if not voice_id:
            self.show_message_signal.emit("Thiếu thông tin", "Vui lòng chọn giọng đọc hoặc nhập Custom Voice ID.", "warning")
            return

        self.el_test_voice_button.setEnabled(False)
        self.el_test_voice_button.setText("...")

        import tempfile
        test_file = None
        try:
            audio_data = self._call_elevenlabs_api_for_test(text, api_key, voice_id)
            if audio_data:
                fd, test_file = tempfile.mkstemp(suffix='.mp3', prefix='tts_test_el_')
                with os.fdopen(fd, 'wb') as f:
                    f.write(audio_data)

                ffplay_bin = os.path.join(os.path.dirname(ffmpeg_path), 'ffplay.exe')
                if os.path.exists(ffplay_bin):
                    subprocess.run(
                        [ffplay_bin, '-nodisp', '-autoexit', '-loglevel', 'quiet', test_file],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    os.startfile(test_file)
                    time.sleep(3)
            else:
                self.show_message_signal.emit("Lỗi", "Không nhận được dữ liệu âm thanh từ ElevenLabs. Kiểm tra API Key và quyền truy cập.", "critical")

        except Exception as e:
            self.show_message_signal.emit("Lỗi", f"Không thể phát âm thanh ElevenLabs: {e}", "critical")
        finally:
            if test_file and os.path.exists(test_file):
                try:
                    os.remove(test_file)
                except Exception:
                    pass
            self.el_test_voice_button.setEnabled(True)
            self.el_test_voice_button.setText("Test")

    def _call_elevenlabs_api_for_test(self, text: str, api_key: str, voice_id: str):
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        headers = {
            'xi-api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'audio/mpeg',
        }
        data = {
            'text': text,
            'model_id': 'eleven_multilingual_v2',
            'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75}
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                error_detail = ""
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', {})
                    if isinstance(error_detail, dict):
                        error_detail = error_detail.get('message', str(error_detail))
                except Exception:
                    error_detail = response.text[:200]
                self.show_message_signal.emit("ElevenLabs Lỗi", f"API Error ({response.status_code}): {error_detail}", "critical")
                return None
        except Exception:
            return None
        return None
    
    show_message_signal = pyqtSignal(str, str, str)

    def setup_signals(self):
        self.show_message_signal.connect(self.show_message_box)

    def show_message_box(self, title, message, level):
        if level == "warning":
            QMessageBox.warning(self, title, message)
        elif level == "critical":
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def start_conversion(self):
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.log_edit.append("\n---> Đang yêu cầu dừng tác vụ...")
            self.start_button.setEnabled(False)
            return

        srt_path = self.srt_path_input.text()
        output_path = self.output_path_input.text()
        
        config = {
            'provider': self.provider_combo.currentText(),
            'ffmpeg_path': self.ffmpeg_path_input.text(),
            'fpt_api_key': self.fpt_api_key_input.text(),
            'fpt_voice': self.fpt_voice_combo.currentData(),
            'tiktok_session_id': self.tiktok_session_id_input.text(),
            'tiktok_voice': self.tiktok_voice_combo.currentData(),
            'elevenlabs_api_key': self.elevenlabs_api_key_input.text(),
            'elevenlabs_voice_id': self.elevenlabs_voice_combo.currentData(),
            'elevenlabs_custom_voice_id': self.elevenlabs_custom_voice_input.text(),
            'delete_temp': self.delete_temp_checkbox.isChecked(),
            'rename_temp_files': self.rename_temp_files_checkbox.isChecked(),
            'speed_factor': self.speed_slider.value() / 100.0,
            'create_capcut': self.capcut_checkbox.isChecked(),
            'video_path': self.video_path_input.text(),
            'audio_edit': self.audio_edit_checkbox.isChecked(),
            'subtitle_size': self.subtitle_size_slider.value(),
            'max_workers': self.workers_spin.value(),
            'dubbing_mode': self.dubbing_checkbox.isChecked(),
        }
        
        # Thêm voice mapping nếu bật dubbing
        if config['dubbing_mode']:
            config['voice_mapping'] = dict(self._dubbing_voice_mapping)
            config['dubbing_default_voice'] = self.dubbing_default_combo.currentData()

        if not all([srt_path, output_path, config['ffmpeg_path']]):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn FFmpeg, file SRT và tên file Output.")
            return
        if config['provider'] == 'TikTok TTS' and not config['tiktok_session_id']:
              QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập TikTok Session ID.")
              return
        if config['provider'] == 'FPT AI' and not config['fpt_api_key']:
              QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập FPT API Key.")
              return
        if config['provider'] == 'ElevenLabs' and not config['elevenlabs_api_key']:
              QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập ElevenLabs API Key.")
              return
        if config['create_capcut'] and not config['video_path']:
              QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn file Video khi bật tạo dự án CapCut.")
              return

        self.save_settings()
        self.set_controls_enabled(False)
        self.progress_bar.setValue(0)
        self.log_edit.clear()

        self.thread = QThread()
        self.worker = ConversionWorker(srt_path, output_path, config)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        
    def save_settings(self):
        self.settings.setValue("provider", self.provider_combo.currentText())
        self.settings.setValue("ffmpeg_path", self.ffmpeg_path_input.text())
        self.settings.setValue("fpt_api_key", self.fpt_api_key_input.text())
        self.settings.setValue("fpt_voice_name", self.fpt_voice_combo.currentText())
        self.settings.setValue("tiktok_session_id", self.tiktok_session_id_input.text())
        self.settings.setValue("tiktok_voice_name", self.tiktok_voice_combo.currentText())
        self.settings.setValue("elevenlabs_api_key", self.elevenlabs_api_key_input.text())
        self.settings.setValue("elevenlabs_lang", self.elevenlabs_lang_combo.currentText())
        self.settings.setValue("elevenlabs_voice_name", self.elevenlabs_voice_combo.currentText())
        self.settings.setValue("elevenlabs_custom_voice_id", self.elevenlabs_custom_voice_input.text())
        self.settings.setValue("delete_temp", self.delete_temp_checkbox.isChecked())
        self.settings.setValue("rename_temp_files", self.rename_temp_files_checkbox.isChecked())
        self.settings.setValue("speed_factor", self.speed_slider.value())
        self.settings.setValue("create_capcut", self.capcut_checkbox.isChecked())
        self.settings.setValue("video_path", self.video_path_input.text())
        self.settings.setValue("audio_edit", self.audio_edit_checkbox.isChecked())
        self.settings.setValue("subtitle_size", self.subtitle_size_slider.value())
        self.settings.setValue("max_workers", self.workers_spin.value())
        
    def load_settings(self):
        self.provider_combo.setCurrentText(self.settings.value("provider", "TikTok TTS"))
        # Auto-detect bundled ffmpeg
        default_ffmpeg = "C:/ffmpeg/ffmpeg.exe"
        if getattr(sys, 'frozen', False):
            bundled = os.path.join(os.path.dirname(sys.executable), 'ffmpeg', 'ffmpeg.exe')
            if os.path.isfile(bundled):
                default_ffmpeg = bundled
        self.ffmpeg_path_input.setText(self.settings.value("ffmpeg_path", default_ffmpeg))
        self.fpt_api_key_input.setText(self.settings.value("fpt_api_key", ""))
        saved_fpt_voice = self.settings.value("fpt_voice_name", "Ban Mai (Nữ Bắc)")
        fpt_idx = self.fpt_voice_combo.findText(saved_fpt_voice)
        if fpt_idx != -1:
            self.fpt_voice_combo.setCurrentIndex(fpt_idx)
        self.tiktok_session_id_input.setText(self.settings.value("tiktok_session_id", ""))
        saved_tiktok_voice = self.settings.value("tiktok_voice_name", "Vietnamese Female")
        index = self.tiktok_voice_combo.findText(saved_tiktok_voice)
        if index != -1:
            self.tiktok_voice_combo.setCurrentIndex(index)
        self.elevenlabs_api_key_input.setText(self.settings.value("elevenlabs_api_key", ""))
        saved_el_lang = self.settings.value("elevenlabs_lang", "🇻🇳 Tiếng Việt")
        el_lang_idx = self.elevenlabs_lang_combo.findText(saved_el_lang)
        if el_lang_idx != -1:
            self.elevenlabs_lang_combo.setCurrentIndex(el_lang_idx)
        self._update_elevenlabs_voices()
        saved_el_voice = self.settings.value("elevenlabs_voice_name", "")
        el_idx = self.elevenlabs_voice_combo.findText(saved_el_voice)
        if el_idx != -1:
            self.elevenlabs_voice_combo.setCurrentIndex(el_idx)
        self.elevenlabs_custom_voice_input.setText(self.settings.value("elevenlabs_custom_voice_id", ""))
        
        self.delete_temp_checkbox.setChecked(self.settings.value("delete_temp", True, type=bool))
        self.rename_temp_files_checkbox.setChecked(self.settings.value("rename_temp_files", False, type=bool))
        self.speed_slider.setValue(self.settings.value("speed_factor", 120, type=int))
        self.capcut_checkbox.setChecked(self.settings.value("create_capcut", False, type=bool))
        self.video_path_input.setText(self.settings.value("video_path", ""))
        self.audio_edit_checkbox.setChecked(self.settings.value("audio_edit", False, type=bool))
        self.subtitle_size_slider.setValue(self.settings.value("subtitle_size", 5, type=int))
        self.workers_spin.setValue(self.settings.value("max_workers", 15, type=int))
            
    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file ffmpeg.exe", "", "Executable Files (ffmpeg.exe)")
        if path: self.ffmpeg_path_input.setText(path)

    def browse_srt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file phụ đề", "", "SRT Files (*.srt)")
        if path:
            self.srt_path_input.setText(path)
            base_name, _ = os.path.splitext(os.path.basename(path))
            output_dir = 'output'
            os.makedirs(output_dir, exist_ok=True)
            self.output_path_input.setText(os.path.join(output_dir, f"{base_name}.mp3"))

    def browse_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file video", "", "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm);;All Files (*.*)")
        if path:
            self.video_path_input.setText(path)

    def _on_capcut_toggled(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.video_path_input.setEnabled(enabled)
        self.video_browse_btn.setEnabled(enabled)

    def on_progress(self, percentage, message):
        self.progress_bar.setValue(percentage)
        self.log_edit.append(message)

    def on_finished(self, message):
        self.log_edit.append(f"\n{message}")
        self.progress_bar.setValue(100)
        self.set_controls_enabled(True)
        QMessageBox.information(self, "Hoàn thành", message)
        self.worker = None
        self.thread = None

    def on_error(self, message):
        self.log_edit.append(f"\nLỖI: {message}")
        self.set_controls_enabled(True)
        QMessageBox.critical(self, "Lỗi", message)
        self.worker = None
        self.thread = None

    def set_controls_enabled(self, enabled):
        self.provider_combo.setEnabled(enabled)
        self.stacked_widget.setEnabled(enabled)
        self.ffmpeg_path_input.parent().findChild(QPushButton).setEnabled(enabled)
        self.srt_path_input.parent().findChild(QPushButton).setEnabled(enabled)
        self.delete_temp_checkbox.setEnabled(enabled)
        self.rename_temp_files_checkbox.setEnabled(enabled)
        self.capcut_checkbox.setEnabled(enabled)
        if enabled:
            self._on_capcut_toggled(self.capcut_checkbox.checkState().value)

        if enabled:
            self.start_button.setText("🚀 Bắt Đầu Chuyển Đổi")
            self.start_button.setEnabled(True)
            self.start_button.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        else:
            self.start_button.setText("⏳ Dừng Lại")
            self.start_button.setEnabled(True)
            self.start_button.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px; background-color: #FF7F7F;")

    def closeEvent(self, event):
        self.save_settings()
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SrtToMp3App()
    ex.setup_signals()
    ex.show()
    sys.exit(app.exec())