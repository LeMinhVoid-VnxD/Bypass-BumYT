# -*- coding: utf-8 -*-
"""
Auto Pipeline — Xử lý hàng loạt: OCR → Dịch → TTS → CapCut
Tab thứ 4 trong BumYT. Click 1 lần, đi ngủ, dậy có dự án.
"""
import sys, os, re, time, threading, queue, shutil
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QProgressBar, QSlider, QCheckBox,
    QFileDialog, QMessageBox, QFrame, QGroupBox, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QSpinBox, QDoubleSpinBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, QEvent
from PyQt6.QtGui import QFont, QColor, QPixmap, QImage, QPainter, QPen, QIcon


class _WheelGuard(QObject):
    """Chặn wheel event trên ComboBox/Slider để tránh đổi giá trị khi scroll."""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            # Chỉ cho phép scroll trong dropdown (khi popup hiện)
            if isinstance(obj, (QComboBox, QSpinBox, QDoubleSpinBox)) and hasattr(obj, 'view') and getattr(obj, 'view')().isVisible():
                return False
            return True  # Block wheel
        return super().eventFilter(obj, event)

# ===================== DATA CLASSES =====================
@dataclass
class VideoJob:
    """Thông tin 1 video trong pipeline."""
    video_path: str
    roi: Optional[tuple] = None  # (x, y, w, h) in original coords or None for Whisper
    status: str = "⏳ Chờ"
    srt_path: str = ""           # Output SRT gốc (sau OCR)
    srt_translated: str = ""     # Output SRT đã dịch
    mp3_path: str = ""           # Output MP3
    error: str = ""

    @property
    def name(self):
        return os.path.basename(self.video_path)


# ===================== ROI PREVIEW CANVAS (Full-featured like OCR tab) =====================
class ROIPreviewCanvas(QLabel):
    """Canvas preview video với ROI kéo thả, co giãn handles — giống tab Lấy Phụ Đề."""
    HANDLE_SIZE = 8
    HANDLE_HIT = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #0a0a14; border: 1px solid #2a2a4a; border-radius: 6px;")
        self.setMinimumSize(640, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._pixmap = None
        self._frame_data = None
        self._scale = 1.0
        self._offset = (0, 0)
        self._sx = self._sy = self._ex = self._ey = None
        self._mode = None   # None / 'draw' / 'move' / 'nw'/'n'/'ne'/'w'/'e'/'sw'/'s'/'se'
        self._drag_start = None

    @property
    def _roi(self):
        if None in (self._sx, self._sy, self._ex, self._ey): return None
        return (self._sx, self._sy, self._ex, self._ey)

    def set_frame(self, bgr_frame):
        if bgr_frame is None: return
        self._frame_data = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB).copy()
        h, w, ch = self._frame_data.shape
        qimg = QImage(self._frame_data.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self._pixmap = QPixmap.fromImage(qimg.copy())
        self._update_display()

    def set_roi_from_original(self, roi_tuple):
        """Set ROI from (x, y, w, h) in original pixel coords."""
        if roi_tuple is None:
            self._sx = self._sy = self._ex = self._ey = None
        else:
            x, y, w, h = roi_tuple
            ox, oy = self._offset
            self._sx = int(x * self._scale + ox)
            self._sy = int(y * self._scale + oy)
            self._ex = int((x + w) * self._scale + ox)
            self._ey = int((y + h) * self._scale + oy)
        self._update_display()

    def get_roi_original(self):
        if None in (self._sx, self._sy, self._ex, self._ey) or not self._pixmap:
            return None
        ox, oy = self._offset
        x1 = int((min(self._sx, self._ex) - ox) / self._scale)
        y1 = int((min(self._sy, self._ey) - oy) / self._scale)
        x2 = int((max(self._sx, self._ex) - ox) / self._scale)
        y2 = int((max(self._sy, self._ey) - oy) / self._scale)
        x1, y1 = max(0, x1), max(0, y1)
        w, h = max(0, x2 - x1), max(0, y2 - y1)
        if w < 4 or h < 4: return None
        return x1, y1, w, h

    def set_default_bottom_half(self):
        """Set ROI = nửa dưới frame (vị trí sub thường gặp)."""
        if not self._pixmap: return
        pw, ph = self._pixmap.width(), self._pixmap.height()
        margin_x = int(pw * 0.05)
        self.set_roi_from_original((margin_x, ph // 2, pw - 2 * margin_x, ph // 2 - 10))

    def clear_roi(self):
        self._sx = self._sy = self._ex = self._ey = None
        self._mode = None; self._drag_start = None
        self._update_display()

    def _get_handles(self, x1, y1, x2, y2):
        mx, my = (x1+x2)//2, (y1+y2)//2
        return [
            (x1, y1, 'nw'), (mx, y1, 'n'), (x2, y1, 'ne'),
            (x1, my, 'w'),                   (x2, my, 'e'),
            (x1, y2, 'sw'), (mx, y2, 's'), (x2, y2, 'se'),
        ]

    def _hit_handle(self, mx, my):
        if not self._roi: return None
        x1, y1 = min(self._sx, self._ex), min(self._sy, self._ey)
        x2, y2 = max(self._sx, self._ex), max(self._sy, self._ey)
        for hx, hy, mode in self._get_handles(x1, y1, x2, y2):
            if abs(mx - hx) <= self.HANDLE_HIT and abs(my - hy) <= self.HANDLE_HIT:
                return mode
        return None

    def _point_in_roi(self, mx, my):
        if not self._roi: return False
        x1, y1 = min(self._sx, self._ex), min(self._sy, self._ey)
        x2, y2 = max(self._sx, self._ex), max(self._sy, self._ey)
        return x1 <= mx <= x2 and y1 <= my <= y2

    def _update_display(self):
        if self._pixmap is None: return
        cw, ch = self.width(), self.height()
        if cw < 10 or ch < 10: return
        pw, ph = self._pixmap.width(), self._pixmap.height()
        self._scale = min(cw / pw, ch / ph)
        nw, nh = int(pw * self._scale), int(ph * self._scale)
        self._offset = ((cw - nw) // 2, (ch - nh) // 2)

        # HiDPI rendering — giống tab Lấy Phụ Đề
        dpr = self.devicePixelRatioF()
        canvas = QPixmap(int(cw * dpr), int(ch * dpr))
        canvas.setDevicePixelRatio(dpr)
        canvas.fill(QColor(10, 10, 20))

        # Scale pixmap ở physical resolution → siêu nét
        phys_nw, phys_nh = int(nw * dpr), int(nh * dpr)
        scaled = self._pixmap.scaled(phys_nw, phys_nh, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        ox, oy = self._offset
        painter.drawPixmap(ox, oy, scaled)

        if self._roi:
            x1, y1 = min(self._sx, self._ex), min(self._sy, self._ey)
            x2, y2 = max(self._sx, self._ex), max(self._sy, self._ey)
            # Semi-transparent fill
            painter.fillRect(x1, y1, x2 - x1, y2 - y1, QColor(0, 255, 136, 25))
            # Rectangle border
            pen = QPen(QColor(0, 255, 136), 2)
            painter.setPen(pen)
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            # Resize handles
            painter.setBrush(QColor(0, 255, 136))
            hs = self.HANDLE_SIZE
            for hx, hy, _ in self._get_handles(x1, y1, x2, y2):
                painter.drawRect(hx - hs//2, hy - hs//2, hs, hs)

        painter.end()
        super().setPixmap(canvas)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._pixmap: return
        mx, my = event.pos().x(), event.pos().y()
        # Check handle resize
        if self._roi:
            handle = self._hit_handle(mx, my)
            if handle:
                self._mode = handle
                self._drag_start = (mx, my, self._sx, self._sy, self._ex, self._ey)
                return
            if self._point_in_roi(mx, my):
                self._mode = 'move'
                self._drag_start = (mx, my, self._sx, self._sy, self._ex, self._ey)
                return
        # New ROI
        self._mode = 'draw'
        self._sx, self._sy = mx, my
        self._ex, self._ey = mx, my
        self._drag_start = None

    def mouseMoveEvent(self, event):
        mx, my = event.pos().x(), event.pos().y()
        if self._mode is None:
            # Hover cursor
            if self._roi:
                h = self._hit_handle(mx, my)
                if h:
                    cursors = {'nw': Qt.CursorShape.SizeFDiagCursor, 'se': Qt.CursorShape.SizeFDiagCursor,
                               'ne': Qt.CursorShape.SizeBDiagCursor, 'sw': Qt.CursorShape.SizeBDiagCursor,
                               'n': Qt.CursorShape.SizeVerCursor, 's': Qt.CursorShape.SizeVerCursor,
                               'w': Qt.CursorShape.SizeHorCursor, 'e': Qt.CursorShape.SizeHorCursor}
                    self.setCursor(cursors.get(h, Qt.CursorShape.CrossCursor))
                elif self._point_in_roi(mx, my):
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            return

        if self._mode == 'draw':
            self._ex, self._ey = mx, my
        elif self._mode == 'move' and self._drag_start:
            omx, omy, osx, osy, oex, oey = self._drag_start
            dx, dy = mx - omx, my - omy
            self._sx, self._sy = osx + dx, osy + dy
            self._ex, self._ey = oex + dx, oey + dy
        elif self._drag_start:
            omx, omy, osx, osy, oex, oey = self._drag_start
            dx, dy = mx - omx, my - omy
            x1, y1 = min(osx, oex), min(osy, oey)
            x2, y2 = max(osx, oex), max(osy, oey)
            m = self._mode
            if 'n' in m: y1 = min(osy, oey) + dy
            if 's' in m: y2 = max(osy, oey) + dy
            if 'w' in m: x1 = min(osx, oex) + dx
            if 'e' in m: x2 = max(osx, oex) + dx
            if x2 - x1 < 20: x2 = x1 + 20
            if y2 - y1 < 20: y2 = y1 + 20
            self._sx, self._sy = x1, y1
            self._ex, self._ey = x2, y2
        self._update_display()

    def mouseReleaseEvent(self, event):
        if self._mode:
            self._mode = None
            self._drag_start = None
            if self._roi:
                self._sx, self._sy, self._ex, self._ey = (
                    min(self._sx, self._ex), min(self._sy, self._ey),
                    max(self._sx, self._ex), max(self._sy, self._ey))
            self._update_display()


def _fmt_time(seconds: float) -> str:
    """Format seconds → HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ===================== ROI SETUP DIALOG =====================
class ROISetupDialog(QDialog):
    """Wizard cho phép setup ROI từng video — có timeline kéo xem video."""
    def __init__(self, jobs: List[VideoJob], parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Setup ROI cho từng Video")
        self.setMinimumSize(1100, 750)
        self.resize(1200, 800)
        self.jobs = jobs
        self.current_idx = 0
        self._cap = None
        self._fps = 25.0
        self._frame_count = 0
        self._duration = 0.0
        self._build_ui()
        self._show_video(0)

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog { background: #0f0f23; }
            QLabel { color: #e0e0f0; }
            QPushButton { background: #3a3a5c; color: #e0e0f0; border: none; border-radius: 8px;
                padding: 10px 20px; font-size: 12px; font-weight: 600; }
            QPushButton:hover { background: #4a4a7c; }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Header
        self.lbl_title = QLabel("")
        self.lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #7c6ff0;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_title)

        self.lbl_filename = QLabel("")
        self.lbl_filename.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_filename.setStyleSheet("color: #a0a0c0; font-size: 11px;")
        layout.addWidget(self.lbl_filename)

        # Canvas (video preview + ROI)
        self.canvas = ROIPreviewCanvas()
        layout.addWidget(self.canvas, 1)

        # Timeline + Time labels
        timeline_frame = QFrame()
        timeline_frame.setStyleSheet("background-color: #1e1e3a; border-radius: 6px; padding: 6px;")
        tl = QHBoxLayout(timeline_frame)
        tl.setContentsMargins(8, 4, 8, 4)

        self.lbl_time = QLabel("00:00:00 / 00:00:00")
        self.lbl_time.setStyleSheet("color: #e0e0e8; font-family: Consolas; font-size: 11px;")
        self.lbl_time.setFixedWidth(160)
        tl.addWidget(self.lbl_time)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self._on_seek)
        self.slider.setStyleSheet(
            "QSlider::groove:horizontal{background:#2a2a4a;height:6px;border-radius:3px;}"
            "QSlider::handle:horizontal{background:#7c6ff0;width:14px;margin:-4px 0;border-radius:7px;}"
            "QSlider::sub-page:horizontal{background:#7c6ff0;border-radius:3px;}"
        )
        tl.addWidget(self.slider, 1)
        layout.addWidget(timeline_frame)

        # Hint + ROI control buttons
        hint_row = QHBoxLayout()
        hint = QLabel("🖱️ Kéo chuột trên ảnh để chọn vùng phụ đề — kéo handle xanh để co giãn")
        hint.setStyleSheet("color: #00d4aa; font-size: 11px;")
        hint_row.addWidget(hint, 1)

        btn_clear_roi = QPushButton("🗑️ Xóa ROI")
        btn_clear_roi.clicked.connect(lambda: self.canvas.clear_roi())
        btn_clear_roi.setStyleSheet("QPushButton{background:#e74c3c;color:#fff;padding:6px 12px;border-radius:6px;font-size:11px;} QPushButton:hover{background:#c0392b;}")
        hint_row.addWidget(btn_clear_roi)
        layout.addLayout(hint_row)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_default = QPushButton("📐 Nửa dưới / Giống Video Trước")
        self.btn_default.clicked.connect(self._set_default_roi)
        self.btn_default.setStyleSheet("QPushButton{background:#00d4aa;color:#111;font-weight:bold;} QPushButton:hover{background:#33eebb;}")
        btn_row.addWidget(self.btn_default)

        self.btn_reuse = QPushButton("📋 Dùng lại ROI trước")
        self.btn_reuse.clicked.connect(self._reuse_prev_roi)
        btn_row.addWidget(self.btn_reuse)

        btn_row.addStretch(1)

        self.btn_prev = QPushButton("⬅ Quay lại")
        self.btn_prev.clicked.connect(self._go_prev)
        btn_row.addWidget(self.btn_prev)

        self.btn_next = QPushButton("✅ Tiếp →")
        self.btn_next.clicked.connect(self._go_next)
        self.btn_next.setStyleSheet("QPushButton{background:#7c6ff0;color:#fff;font-weight:bold;} QPushButton:hover{background:#9588ff;}")
        btn_row.addWidget(self.btn_next)

        self.btn_done = QPushButton("🏁 Xong hết")
        self.btn_done.clicked.connect(self._finish_all)
        self.btn_done.setStyleSheet("QPushButton{background:#2ecc71;color:#fff;font-weight:bold;} QPushButton:hover{background:#27ae60;}")
        btn_row.addWidget(self.btn_done)

        layout.addLayout(btn_row)

    def _release_cap(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._cap = None

    def _show_video(self, idx):
        if idx < 0 or idx >= len(self.jobs): return
        self.current_idx = idx
        job = self.jobs[idx]
        self.lbl_title.setText(f"⚙️ Setup ROI — Video {idx + 1}/{len(self.jobs)}")
        self.lbl_filename.setText(f"📹 {job.name}")

        # Release previous capture
        self._release_cap()

        # Open video
        self._cap = cv2.VideoCapture(job.video_path)
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.0
        self._frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self._duration = self._frame_count / self._fps if self._fps > 0 else 0

        # Setup slider
        self.slider.blockSignals(True)
        self.slider.setMaximum(max(0, self._frame_count - 1))
        self.slider.setValue(0)
        self.slider.blockSignals(False)

        # Read first frame
        ret, frame = self._cap.read()
        if ret:
            self.canvas.set_frame(frame)
            self.lbl_time.setText(f"00:00:00 / {_fmt_time(self._duration)}")
            if job.roi:
                self.canvas.set_roi_from_original(job.roi)
            else:
                self.canvas.set_default_bottom_half()

        self.btn_prev.setEnabled(idx > 0)
        self.btn_reuse.setEnabled(idx > 0)

    def _on_seek(self, frame_idx):
        """Khi kéo slider, nhảy tới frame tương ứng.
        KHÔNG lưu/khôi phục ROI vì các frame cùng video có cùng kích thước.
        ROI canvas coords giữ nguyên, chỉ thay pixmap bên dưới."""
        if not self._cap or not self._cap.isOpened(): return
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self._cap.read()
        if ret:
            # Chỉ cập nhật pixmap, KHÔNG đụng ROI
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.canvas._pixmap = QPixmap.fromImage(qimg.copy())
            self.canvas._frame_data = rgb
            self.canvas._update_display()  # Vẽ lại với ROI giữ nguyên
            t = frame_idx / self._fps if self._fps > 0 else 0
            self.lbl_time.setText(f"{_fmt_time(t)} / {_fmt_time(self._duration)}")

    def _save_current_roi(self):
        roi = self.canvas.get_roi_original()
        if roi:
            self.jobs[self.current_idx].roi = roi

    def _set_default_roi(self):
        if self.current_idx > 0:
            prev_roi = self.jobs[self.current_idx - 1].roi
            if prev_roi:
                self.canvas.set_roi_from_original(prev_roi)
                return
        self.canvas.set_default_bottom_half()

    def _reuse_prev_roi(self):
        if self.current_idx > 0:
            prev_roi = self.jobs[self.current_idx - 1].roi
            if prev_roi:
                self.canvas.set_roi_from_original(prev_roi)

    def _go_prev(self):
        self._save_current_roi()
        self._show_video(self.current_idx - 1)

    def _go_next(self):
        self._save_current_roi()
        if self.current_idx < len(self.jobs) - 1:
            self._show_video(self.current_idx + 1)
        else:
            self._finish_all()

    def _finish_all(self):
        self._save_current_roi()
        self._release_cap()
        # Validate
        missing = [j.name for j in self.jobs if j.roi is None]
        if missing:
            QMessageBox.warning(self, "Thiếu ROI",
                f"Các video sau chưa có ROI:\n" + "\n".join(missing[:5]) +
                "\n\nBấm '📐 Nửa dưới' để đặt mặc định.")
            return
        self.accept()

    def closeEvent(self, event):
        self._release_cap()
        super().closeEvent(event)


# ===================== BATCH PIPELINE WORKER =====================
class BatchPipelineWorker(QObject):
    """Worker chạy trên QThread, xử lý tuần tự từng video qua pipeline."""
    log = pyqtSignal(str)
    progress_total = pyqtSignal(int)  # % tổng
    progress_step = pyqtSignal(int)   # % bước hiện tại
    video_status = pyqtSignal(int, str)  # (video_idx, status_text)
    step_info = pyqtSignal(str)  # "Video 3/10 — Đang dịch..."
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, jobs: List[VideoJob], config: dict):
        super().__init__()
        self.jobs = jobs
        self.config = config
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            total = len(self.jobs)
            do_ocr = self.config.get('do_ocr', True)
            do_translate = self.config.get('do_translate', True)
            do_tts = self.config.get('do_tts', True)

            for i, job in enumerate(self.jobs):
                if not self.is_running:
                    self.log.emit("⏹️ Pipeline đã bị dừng bởi người dùng.")
                    break

                self.log.emit(f"\n{'═' * 50}")
                self.log.emit(f"🎬 Video {i+1}/{total}: {job.name}")
                self.log.emit(f"{'═' * 50}")
                self.video_status.emit(i, "🔄 Đang xử lý...")
                video_start_time = time.time()

                try:
                    # ===== BƯỚC 1: OCR =====
                    if do_ocr:
                        step_t = time.time()
                        self.step_info.emit(f"Video {i+1}/{total} — 🔍 Lấy phụ đề...")
                        self.video_status.emit(i, "🔍 OCR...")
                        srt_path = self._run_ocr(job)
                        if not srt_path:
                            raise Exception("OCR thất bại, không tạo được SRT.")
                        job.srt_path = srt_path
                        elapsed = time.time() - step_t
                        self.log.emit(f"✅ OCR xong: {os.path.basename(srt_path)} ({self._fmt_elapsed(elapsed)})")
                    elif job.srt_path:
                        self.log.emit(f"⏭️ Bỏ qua OCR, dùng SRT có sẵn: {os.path.basename(job.srt_path)}")
                    else:
                        # Tìm SRT cùng tên video
                        base = os.path.splitext(job.video_path)[0]
                        for ext in ['.srt', '_output.srt']:
                            candidate = base + ext
                            if os.path.exists(candidate):
                                job.srt_path = candidate
                                self.log.emit(f"📄 Tìm thấy SRT: {os.path.basename(candidate)}")
                                break
                        if not job.srt_path:
                            raise Exception("Không có file SRT và OCR đã tắt.")

                    if not self.is_running: break

                    # ===== BƯỚC 2: DỊCH =====
                    if do_translate and job.srt_path:
                        step_t = time.time()
                        self.step_info.emit(f"Video {i+1}/{total} — 🌐 Dịch phụ đề...")
                        self.video_status.emit(i, "🌐 Dịch...")
                        translated = self._run_translate(job)
                        if translated:
                            job.srt_translated = translated
                            elapsed = time.time() - step_t
                            self.log.emit(f"✅ Dịch xong: {os.path.basename(translated)} ({self._fmt_elapsed(elapsed)})")
                            # Auto lọc + gộp
                            if self.config.get('auto_filter_merge', True):
                                self._auto_filter_merge(translated)
                                self.log.emit(f"🧹 Đã lọc trùng + gộp tự động.")
                        else:
                            self.log.emit(f"⚠️ Dịch thất bại, bỏ qua.")
                    elif job.srt_translated:
                        self.log.emit(f"⏭️ Bỏ qua dịch, dùng SRT đã dịch có sẵn.")

                    if not self.is_running: break

                    # ===== BƯỚC 3: TTS + CAPCUT =====
                    if do_tts:
                        srt_for_tts = job.srt_translated or job.srt_path
                        if srt_for_tts:
                            step_t = time.time()
                            self.step_info.emit(f"Video {i+1}/{total} — 🔊 Chuyển giọng + CapCut...")
                            self.video_status.emit(i, "🔊 TTS...")
                            mp3_path = self._run_tts(job, srt_for_tts)
                            if mp3_path:
                                job.mp3_path = mp3_path
                                elapsed = time.time() - step_t
                                self.log.emit(f"✅ TTS xong: {os.path.basename(mp3_path)} ({self._fmt_elapsed(elapsed)})")
                            else:
                                self.log.emit(f"⚠️ TTS thất bại.")

                    video_elapsed = time.time() - video_start_time
                    self.video_status.emit(i, "✅ Xong")
                    self.log.emit(f"🏁 Hoàn tất video {i+1}/{total} ({self._fmt_elapsed(video_elapsed)})")

                except Exception as e:
                    job.error = str(e)
                    job.status = f"❌ Lỗi"
                    self.video_status.emit(i, f"❌ {str(e)[:30]}")
                    self.log.emit(f"❌ Lỗi: {e}")
                    if self.config.get('stop_on_error', False):
                        self.log.emit("⏹️ Dừng pipeline do cấu hình stop_on_error.")
                        break
                    else:
                        self.log.emit("→ Bỏ qua, tiếp tục video tiếp theo...")

                # Update total progress
                pct = int((i + 1) / total * 100)
                self.progress_total.emit(pct)

            self.log.emit(f"\n{'═' * 50}")
            done_count = sum(1 for j in self.jobs if j.status == "✅ Xong" or "Xong" in (self.jobs[self.jobs.index(j)].status if j in self.jobs else ""))
            self.log.emit(f"🏆 Pipeline hoàn tất! {len([j for j in self.jobs if not j.error])}/{total} video thành công.")
            self.finished.emit()

        except Exception as e:
            import traceback
            self.error.emit(f"Pipeline crash: {e}\n{traceback.format_exc()}")

    @staticmethod
    def _fmt_elapsed(seconds):
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}p{s:02d}s" if m > 0 else f"{s}s"

    # ─────── OCR Step ───────
    def _run_ocr(self, job: VideoJob) -> Optional[str]:
        """Chạy OCR trên 1 video, trả về đường dẫn SRT."""
        engine = self.config.get('ocr_engine', 'PaddleOCR')
        
        if engine == 'Whisper':
            return self._run_whisper(job)
        
        # Import modules
        from modules.ocr_widget import OCRWidget, write_srt, Segment
        
        # Tạo instance OCR tạm
        widget = self._get_ocr_widget()
        if not widget:
            raise Exception("Không thể khởi tạo OCR engine.")
        
        # Sử dụng logic OCR trực tiếp
        roi = job.roi
        if not roi:
            raise Exception("Chưa setup ROI cho video này.")
        
        target_fps = widget.spin_fps.value()
        simi = widget.spin_simi.value()
        gap = widget.spin_gap.value()
        minseg = widget.spin_minseg.value()
        
        # Override bằng cấu hình từ Auto Pipeline nếu widget spin_* không khởi tạo
        if target_fps <= 0: target_fps = self.config.get('ocr_fps', 10.0)
        
        # Output path: đặt tên SRT = tên video (không đuôi)
        video_base = os.path.splitext(os.path.basename(job.video_path))[0]
        video_dir = os.path.dirname(job.video_path)
        out_srt = os.path.join(video_dir, f"{video_base}.srt")
        
        # Chạy OCR worker đồng bộ (blocking)
        # Chạy OCR worker đồng bộ (blocking) nhưng proxy msg_q để bắt log
        msg_q = queue.Queue()
        
        class MsgQueueProxy:
            def __init__(self, original, auto_q):
                self.original = original
                self.auto_q = auto_q
            def put(self, item):
                self.original.put(item)
                self.auto_q.put(item)
            def get_nowait(self):
                return self.original.get_nowait()
                
        old_msg_q = widget.msg_q
        widget.msg_q = MsgQueueProxy(old_msg_q, msg_q)
        widget._is_auto_pipeline = True

        widget.stop_flag = False
        widget.video_path = job.video_path
        # Đặt out_name = tên video để OCR ghi đúng file
        if hasattr(widget, 'out_name'):
            widget.out_name.setText(video_base)
        
        # Chạy trên thread riêng và đợi
        worker_done = threading.Event()
        worker_error = [None]
        
        def _worker():
            try:
                widget._ocr_worker(job.video_path, roi, target_fps, simi, gap, minseg, engine)
            except Exception as e:
                worker_error[0] = str(e)
            finally:
                worker_done.set()
                # TRÁNH RACE CONDITION: Không reset widget._is_auto_pipeline ở đây vì GUI thread 
                # (QTimer) chưa kịp đọc message "done". Ta sẽ reset sau khi t.join().
                widget.msg_q = old_msg_q
        
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        
        # Poll messages from OCR worker
        while not worker_done.is_set():
            try:
                msg_type, *msg_data = msg_q.get(timeout=0.5)
                if msg_type == "log":
                    self.log.emit(f"  [OCR] {msg_data[0]}")
                elif msg_type == "status":
                    status_text, pct = msg_data[0]
                    self.progress_step.emit(pct)
                elif msg_type == "error":
                    worker_error[0] = msg_data[0]
                elif msg_type == "done":
                    pass
            except queue.Empty:
                pass
            if not self.is_running:
                widget.stop_flag = True
                break
        
        t.join(timeout=30)
        QTimer.singleShot(1500, lambda: setattr(widget, '_is_auto_pipeline', False))
        
        if worker_error[0]:
            raise Exception(f"OCR lỗi: {worker_error[0]}")
        
        # Tìm SRT output — thử nhiều pattern
        for candidate in [out_srt, os.path.join(video_dir, "output.srt")]:
            if os.path.exists(candidate):
                # Nếu SRT tên khác, rename cho đúng
                if candidate != out_srt:
                    shutil.move(candidate, out_srt)
                return out_srt
        return None

    def _run_whisper(self, job: VideoJob) -> Optional[str]:
        """Chạy Whisper STT trên video."""
        # TODO: Implement whisper batch - reuse logic từ ocr_widget._run_whisper_stt
        self.log.emit("  [Whisper] Chưa hỗ trợ batch Whisper, bỏ qua.")
        return None

    def _get_ocr_widget(self):
        """Lấy OCR widget tab số 1 thông qua config."""
        main_tab = self.config.get('main_ocr_tab')
        if not main_tab:
            raise Exception("OCR Tab chưa được khởi tạo. Không thể thực hiện OCR.")
            
        # Khởi tạo engine theo giá trị UI
        if main_tab._active_engine is None:
            # Gọi reinitialize_ocr_engine an toàn vì đây là widget có sẵn, 
            # nhưng tốt nhất không gọi gì vì Main Thread đã gọi nó rồi.
            pass
            
        return main_tab

    # ─────── Translation Step ───────
    def _run_translate(self, job: VideoJob) -> Optional[str]:
        """Dịch file SRT, trả về đường dẫn file dịch.
        Lấy prompt + API key từ .env (giống tab Dịch Phụ Đề)."""
        try:
            import dich
            from dotenv import load_dotenv, find_dotenv, dotenv_values
        except ImportError:
            self.log.emit("⚠️ Không import được module dich.py")
            return None
        
        # Load .env
        load_dotenv(override=True)
        dotenv_path = find_dotenv() or os.path.join(os.getcwd(), '.env')
        
        api = self.config.get('translate_api', 'gemini')
        model = self.config.get('translate_model', 'gemini-2.5-flash')
        glossary_path = self.config.get('glossary_path', '')
        
        # Đọc prompt từ .env CUSTOM_SYSTEM_PROMPT — giống hệt tab Dịch
        prompt = ""
        try:
            env_vals = dotenv_values(dotenv_path)
            prompt = env_vals.get("CUSTOM_SYSTEM_PROMPT", "") or ""
        except Exception:
            prompt = os.getenv("CUSTOM_SYSTEM_PROMPT", "") or ""
        if not prompt:
            prompt = dich.DEFAULT_SYSTEM_PROMPT
        
        self.log.emit(f"  [Dịch] 🔧 Model: {model} | Prompt: {len(prompt)} ký tự")
        
        target_lang = self.config.get('target_lang', 'vi')
        lang_names = {
            "vi": "tiếng Việt", "en": "English", "es": "Español",
            "pt": "Português", "fr": "Français", "de": "Deutsch",
            "ru": "Русский", "ar": "العربية", "hi": "हिन्दी",
            "ko": "한국어", "ja": "日本語", "th": "ภาษาไทย",
            "id": "Bahasa Indonesia", "ms": "Bahasa Melayu", "fil": "Filipino",
            "tr": "Türkçe"
        }
        target_lang_name = lang_names.get(target_lang, "tiếng Việt")
        if target_lang != "vi":
            prompt += (
                f"\n\n【NGÔN NGỮ ĐÍCH - GHI ĐÈ】\n"
                f"• DỊCH SANG {target_lang_name.upper()} thay vì tiếng Việt.\n"
                f"• Output format: [số]|text {target_lang_name}"
            )
        
        # Chạy TranslationWorker đồng bộ
        done_event = threading.Event()
        result = [None]
        error_msg = [None]
        
        worker = dich.TranslationWorker(
            job.srt_path, api, model, prompt,
            glossary_path=glossary_path
        )
        
        def on_progress(msg):
            self.log.emit(f"  [Dịch] {msg}")
        
        def on_finished(output_path):
            result[0] = output_path
            done_event.set()
        
        def on_error(msg):
            error_msg[0] = msg
            done_event.set()
        
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.batch_info.connect(lambda msg: self.log.emit(f"  [Dịch] {msg}"))
        
        # Chạy worker.run() TRỰC TIẾP (synchronous) — không tạo QThread mới
        # vì BatchPipelineWorker đã chạy trên QThread rồi
        worker.run()
        
        if error_msg[0]:
            self.log.emit(f"  [Dịch] ❌ Lỗi: {error_msg[0]}")
            return None
        
        return result[0]

    # ─────── Auto Filter + Merge ───────
    def _auto_filter_merge(self, srt_path: str):
        """Lọc trùng + gộp dòng giống nhau trên file SRT đã dịch.
        Logic giống tab Lấy Phụ Đề:
        - ratio >= 0.85 (màu đỏ): Gộp, giữ câu dài nhất có ý nghĩa
        - Câu ngắn 1-2 ký tự (màu cam): Không gộp, lọc bỏ dòng rác
        """
        try:
            import srt as srt_lib
            from difflib import SequenceMatcher
            
            with open(srt_path, 'r', encoding='utf-8') as f:
                subs = list(srt_lib.parse(f.read()))
            
            if not subs: return
            
            # Lọc dòng trùng liên tiếp (≥85% giống) — giống OCR tab
            filtered = [subs[0]]
            merged_count = 0
            for i in range(1, len(subs)):
                prev_text = filtered[-1].content.strip()
                cur_text = subs[i].content.strip()
                
                # Lấy phần chữ thực (bỏ khoảng trắng, dấu câu)
                prev_alpha = ''.join(c for c in prev_text if c.isalnum())
                cur_alpha = ''.join(c for c in cur_text if c.isalnum())
                
                # Câu quá ngắn (1-2 ký tự thực = màu cam) → KHÔNG gộp
                if len(cur_alpha) <= 2 or len(prev_alpha) <= 2:
                    filtered.append(subs[i])
                    continue
                
                ratio = SequenceMatcher(None, cur_text, prev_text).ratio()
                if ratio >= 0.85:
                    # Gộp: giữ câu DÀI NHẤT có ý nghĩa, mở rộng thời gian
                    keep_text = prev_text if len(prev_text) >= len(cur_text) else cur_text
                    filtered[-1] = srt_lib.Subtitle(
                        index=filtered[-1].index,
                        start=filtered[-1].start,
                        end=subs[i].end,
                        content=keep_text
                    )
                    merged_count += 1
                else:
                    filtered.append(subs[i])
            
            # Lọc dòng rác (< 2 ký tự thực = màu cam)
            junk_removed = 0
            clean = []
            for sub in filtered:
                clean_text = ''.join(c for c in sub.content if c.isalnum())
                if len(clean_text) >= 2:
                    clean.append(sub)
                else:
                    junk_removed += 1
            
            # Renumber
            for i, sub in enumerate(clean, 1):
                sub.index = i
            
            # Ghi đè
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_lib.compose(clean))
            
            if merged_count > 0 or junk_removed > 0:
                self.log.emit(f"  [Lọc] Gộp {merged_count} dòng trùng (≥85%), xóa {junk_removed} dòng rác → {len(clean)} dòng.")
        except Exception as e:
            self.log.emit(f"  [Lọc] ⚠️ Lỗi lọc: {e}")

    # ─────── TTS Step ───────
    def _run_tts(self, job: VideoJob, srt_path: str) -> Optional[str]:
        """Chạy TTS trên file SRT, trả về đường dẫn MP3."""
        try:
            import chuyendoi_chinh
        except ImportError:
            self.log.emit("⚠️ Không import được module chuyendoi_chinh.py")
            return None
        
        base = os.path.splitext(job.video_path)[0]
        output_mp3 = f"{base}_voice.mp3"
        
        # Lấy credentials từ QSettings của tab Chuyển Đổi
        from PyQt6.QtCore import QSettings
        s = QSettings('BumYT', 'SrtToMp3')
        
        provider = self.config.get('tts_provider', 'TikTok TTS')
        voice_code = self.config.get('tts_voice_code', 'BV074_streaming')
        
        default_ffmpeg = "C:/ffmpeg/ffmpeg.exe"
        if getattr(sys, 'frozen', False):
            bundled = os.path.join(os.path.dirname(sys.executable), 'ffmpeg', 'ffmpeg.exe')
            if os.path.isfile(bundled):
                default_ffmpeg = bundled
                
        ffmpeg_path = s.value('ffmpeg_path', '')
        if not ffmpeg_path or ffmpeg_path == 'ffmpeg':
            ffmpeg_path = default_ffmpeg
                    
        tts_config = {
            'provider': provider,
            'ffmpeg_path': ffmpeg_path,
            'fpt_api_key': s.value('fpt_api_key', ''),
            'fpt_voice': voice_code if 'FPT' in provider else s.value('fpt_voice', 'banmai'),
            'tiktok_session_id': s.value('tiktok_session_id', ''),
            'tiktok_voice': voice_code if 'TikTok' in provider else 'BV074_streaming',
            'elevenlabs_api_key': s.value('elevenlabs_api_key', ''),
            'elevenlabs_voice_id': s.value('elevenlabs_voice_id', '') if 'ElevenLabs' in provider else '',
            'elevenlabs_custom_voice_id': s.value('elevenlabs_custom_voice_id', ''),
            'delete_temp': self.config.get('delete_temp_live', s.value('delete_temp', True, type=bool)),
            'rename_temp_files': self.config.get('rename_temp_live', s.value('rename_temp_files', False, type=bool)),
            'speed_factor': self.config.get('speed_factor_live', s.value('speed_factor', 120, type=int)) / 100.0,
            'create_capcut': self.config.get('create_capcut', True),
            'video_path': job.video_path,
            'audio_edit': self.config.get('audio_edit_live', s.value('audio_edit', False, type=bool)),
            'subtitle_size': self.config.get('subtitle_size_live', s.value('subtitle_size', 5, type=int)),
            'max_workers': self.config.get('max_workers_live', s.value('max_workers', 15, type=int)),
            'dubbing_mode': self.config.get('dubbing_mode_live', s.value('dubbing_mode', False, type=bool)),
        }
        
        done_event = threading.Event()
        result = [None]
        error_msg = [None]
        
        worker = chuyendoi_chinh.ConversionWorker(srt_path, output_mp3, tts_config)
        
        def on_progress(pct, msg):
            self.progress_step.emit(pct)
            self.log.emit(f"  [TTS] {msg}")
        
        def on_finished(msg):
            result[0] = output_mp3
            done_event.set()
        
        def on_error(msg):
            error_msg[0] = msg
            done_event.set()
        
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        
        # Chạy worker.run() TRỰC TIẾP (synchronous) — không nested QThread
        worker.run()
        
        if error_msg[0]:
            self.log.emit(f"  [TTS] ❌ Lỗi: {error_msg[0]}")
            return None
        
        return result[0]


# ===================== MAIN WIDGET =====================
class AutoPipelineWidget(QWidget):
    """Widget chính cho tab ⚡ Tự Động."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.jobs: List[VideoJob] = []
        self.thread = None
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ===== LEFT: Video list + Progress =====
        left = QVBoxLayout()

        # Title
        title = QLabel("⚡ XỬ LÝ HÀNG LOẠT")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #7c6ff0; padding: 4px;")
        left.addWidget(title)

        # Video Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["#", "Video", "Trạng thái"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumWidth(500)
        left.addWidget(self.table, 1)

        # Buttons: Add/Remove videos
        btn_row = QHBoxLayout()
        btn_add = QPushButton("📁 Thêm Video")
        btn_add.clicked.connect(self._add_videos)
        btn_add.setStyleSheet("QPushButton{background:#7c6ff0;color:#fff;padding:8px 16px;border-radius:8px;font-weight:bold;} QPushButton:hover{background:#9588ff;}")
        btn_row.addWidget(btn_add)

        btn_add_folder = QPushButton("📂 Thêm Thư Mục")
        btn_add_folder.clicked.connect(self._add_folder)
        btn_add_folder.setStyleSheet("QPushButton{background:#3a3a5c;color:#e0e0f0;padding:8px 16px;border-radius:8px;} QPushButton:hover{background:#4a4a7c;}")
        btn_row.addWidget(btn_add_folder)

        btn_clear = QPushButton("🗑️ Xóa tất cả")
        btn_clear.clicked.connect(self._clear_all)
        btn_clear.setStyleSheet("QPushButton{background:#e74c3c;color:#fff;padding:8px 16px;border-radius:8px;} QPushButton:hover{background:#c0392b;}")
        btn_row.addWidget(btn_clear)

        left.addLayout(btn_row)

        # Progress bars
        prog_group = QGroupBox("📊 Tiến trình")
        prog_group.setStyleSheet("QGroupBox{background:#1e1e3a;border:1px solid #2a2a4a;border-radius:8px;margin-top:8px;padding:12px 8px;font-weight:bold;color:#00d4aa;}")
        prog_lay = QVBoxLayout()

        self.lbl_step = QLabel("Chưa bắt đầu")
        self.lbl_step.setStyleSheet("color: #e0e0f0; font-size: 12px;")
        prog_lay.addWidget(self.lbl_step)

        lbl_total = QLabel("Tổng thể:")
        lbl_total.setStyleSheet("color: #a0a0c0; font-size: 10px;")
        prog_lay.addWidget(lbl_total)
        self.progress_total = QProgressBar()
        self.progress_total.setValue(0)
        prog_lay.addWidget(self.progress_total)

        lbl_step_bar = QLabel("Bước hiện tại:")
        lbl_step_bar.setStyleSheet("color: #a0a0c0; font-size: 10px;")
        prog_lay.addWidget(lbl_step_bar)
        self.progress_step = QProgressBar()
        self.progress_step.setValue(0)
        prog_lay.addWidget(self.progress_step)

        prog_group.setLayout(prog_lay)
        left.addWidget(prog_group)

        # Start/Stop
        action_row = QHBoxLayout()
        self.btn_start = QPushButton("🚀 BẮT ĐẦU PIPELINE")
        self.btn_start.clicked.connect(self._start_pipeline)
        self.btn_start.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_start.setStyleSheet("QPushButton{background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c6ff0,stop:1 #00d4aa);color:#fff;padding:14px;border-radius:10px;} QPushButton:hover{background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #9588ff,stop:1 #33eebb);}")
        action_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹️ DỪNG")
        self.btn_stop.clicked.connect(self._stop_pipeline)
        self.btn_stop.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_stop.setStyleSheet("QPushButton{background:#e74c3c;color:#fff;padding:14px;border-radius:10px;} QPushButton:hover{background:#c0392b;}")
        self.btn_stop.setEnabled(False)
        action_row.addWidget(self.btn_stop)
        left.addLayout(action_row)

        main_layout.addLayout(left, 1)

        # ===== RIGHT: Settings + Log =====
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFixedWidth(400)
        right_scroll.setStyleSheet("QScrollArea{border:none;background:#0f0f1a;}")

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(6)

        def _section(title):
            grp = QGroupBox(title)
            grp.setStyleSheet("QGroupBox{background:#1e1e3a;border:1px solid #2a2a4a;border-radius:8px;margin-top:8px;padding:12px 8px 8px 8px;font-weight:bold;color:#00d4aa;font-size:11px;}QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 6px;}")
            lay = QVBoxLayout()
            grp.setLayout(lay)
            right_layout.addWidget(grp)
            return lay

        # Pipeline Steps Selection
        steps = _section("🔧 Chọn bước xử lý")
        self.chk_ocr = QCheckBox("☑ Bước 1: Lấy Phụ Đề (OCR)")
        self.chk_ocr.setChecked(True)
        self.chk_ocr.setStyleSheet("color:#e0e0f0;")
        steps.addWidget(self.chk_ocr)
        self.chk_translate = QCheckBox("☑ Bước 2: Dịch Phụ Đề")
        self.chk_translate.setChecked(True)
        self.chk_translate.setStyleSheet("color:#e0e0f0;")
        steps.addWidget(self.chk_translate)
        self.chk_tts = QCheckBox("☑ Bước 3: Lồng Tiếng + CapCut")
        self.chk_tts.setChecked(True)
        self.chk_tts.setStyleSheet("color:#e0e0f0;")
        steps.addWidget(self.chk_tts)

        # OCR Settings
        ocr_sec = _section("🔍 Cài đặt OCR")
        form = QFormLayout()
        self.ocr_engine_combo = QComboBox()
        self.ocr_engine_combo.addItems(["PaddleOCR", "EasyOCR", "Whisper (Giọng nói)"])
        self.ocr_engine_combo.setStyleSheet("QComboBox{background:#282840;color:#e0e0e8;padding:6px;border-radius:4px;}")
        form.addRow("Engine:", self.ocr_engine_combo)
        ocr_sec.addLayout(form)

        # Translation Settings
        trans_sec = _section("🌐 Cài đặt Dịch")
        form2 = QFormLayout()
        
        # API Provider combo
        self.translate_api_combo = QComboBox()
        self.translate_api_combo.addItems(["Gemini", "ChatGPT (OpenAI)", "Grok (xAI)"])
        self.translate_api_combo.setStyleSheet("QComboBox{background:#282840;color:#e0e0e8;padding:6px;border-radius:4px;}")
        self.translate_api_combo.currentTextChanged.connect(self._on_translate_api_changed)
        form2.addRow("API:", self.translate_api_combo)
        
        # Model combo
        self.translate_model_combo = QComboBox()
        self.translate_model_combo.setStyleSheet("QComboBox{background:#282840;color:#e0e0e8;padding:6px;border-radius:4px;}")
        form2.addRow("Model:", self.translate_model_combo)
        
        self.translate_lang_combo = QComboBox()
        self.translate_lang_combo.addItems([
            "Trung → Việt", "Trung → English", "Anh → Việt",
            "Nhật → Việt", "Hàn → Việt"
        ])
        self.translate_lang_combo.setStyleSheet("QComboBox{background:#282840;color:#e0e0e8;padding:6px;border-radius:4px;}")
        form2.addRow("Ngôn ngữ:", self.translate_lang_combo)

        self.glossary_combo = QComboBox()
        self.glossary_combo.setStyleSheet("QComboBox{background:#282840;color:#e0e0e8;padding:6px;border-radius:4px;}")
        
        try:
            import dich
            files = dich.get_glossary_files()
            for f in files:
                if f == dich.DEFAULT_GLOSSARY:
                    self.glossary_combo.addItem(f"★ {f}", f)
                else:
                    self.glossary_combo.addItem(f, f)
            
            # Select the one stored in .env if available
            dotenv_path = dich.find_dotenv() or os.path.join(os.getcwd(), '.env')
            try:
                from dotenv import dotenv_values
                env_vals = dotenv_values(dotenv_path)
                selected = env_vals.get("SELECTED_GLOSSARY", "")
                if selected:
                    idx = self.glossary_combo.findText(selected)
                    if idx >= 0:
                        self.glossary_combo.setCurrentIndex(idx)
            except Exception:
                pass
        except Exception:
            self.glossary_combo.addItems(["glossary.json"])
            
        form2.addRow("Thể loại:", self.glossary_combo)

        self.chk_auto_filter = QCheckBox("Tự động lọc trùng + gộp")
        self.chk_auto_filter.setChecked(True)
        self.chk_auto_filter.setStyleSheet("color:#e0e0f0;")
        form2.addRow("", self.chk_auto_filter)
        trans_sec.addLayout(form2)
        
        # Populate models for default API
        self._on_translate_api_changed(self.translate_api_combo.currentText())

        # TTS Settings — lấy API Key/FFmpeg từ tab Chuyển Đổi, chỉ hiện chọn giọng
        tts_sec = _section("🔊 Cài đặt Lồng Tiếng")
        form3 = QFormLayout()

        note = QLabel("ℹ️ API Key & FFmpeg lấy từ tab Chuyển Đổi")
        note.setStyleSheet("color: #a0a0c0; font-size: 10px; font-style: italic;")
        form3.addRow(note)

        self.tts_provider_combo = QComboBox()
        self.tts_provider_combo.addItems(["TikTok TTS", "FPT AI", "ElevenLabs"])
        self.tts_provider_combo.setStyleSheet("QComboBox{background:#282840;color:#e0e0e8;padding:6px;border-radius:4px;}")
        self.tts_provider_combo.currentTextChanged.connect(self._on_provider_changed)
        form3.addRow("Nhà cung cấp:", self.tts_provider_combo)

        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.setStyleSheet("QComboBox{background:#282840;color:#e0e0e8;padding:6px;border-radius:4px;}")
        form3.addRow("Giọng đọc:", self.tts_voice_combo)

        self.chk_capcut = QCheckBox("Tạo dự án CapCut")
        self.chk_capcut.setChecked(True)
        self.chk_capcut.setStyleSheet("color:#e0e0f0;")
        form3.addRow("", self.chk_capcut)
        tts_sec.addLayout(form3)

        # Populate voices
        self._on_provider_changed(self.tts_provider_combo.currentText())

        # Error & Extra Cấu hình
        err_sec = _section("⚠️ Lỗi & Tính Năng Thêm")
        self.chk_stop_on_error = QCheckBox("Dừng pipeline nếu 1 video lỗi")
        self.chk_stop_on_error.setStyleSheet("color:#e0e0f0;")
        err_sec.addWidget(self.chk_stop_on_error)
        
        self.chk_auto_shutdown = QCheckBox("Tự động Tắt máy (Shutdown) khi hoàn thành")
        self.chk_auto_shutdown.setStyleSheet("color:#ff6b6b; font-weight:bold;")
        self.chk_auto_shutdown.setToolTip("Khi xử lý xong tất cả số video, đếm ngược 30s và tự động tắt máy tính.")
        err_sec.addWidget(self.chk_auto_shutdown)

        right_layout.addStretch(1)
        right_scroll.setWidget(right_widget)
        main_layout.addWidget(right_scroll)

        # Log (bottom of left side — let's put it below progress)
        # Actually let's add a collapsible log area
        log_group = QGroupBox("📋 Nhật ký")
        log_group.setStyleSheet("QGroupBox{background:#1e1e3a;border:1px solid #2a2a4a;border-radius:8px;margin-top:8px;padding:12px 8px;font-weight:bold;color:#00d4aa;}")
        log_lay = QVBoxLayout()
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(200)
        self.log_edit.setStyleSheet("QTextEdit{background:#12122a;color:#d0d0e0;border:1px solid #2a2a4a;border-radius:6px;font-family:Consolas;font-size:10px;}")
        log_lay.addWidget(self.log_edit)
        log_group.setLayout(log_lay)
        # Insert log before the action row — actually we need to restructure
        # For now, put in the right panel bottom
        right_layout.addWidget(log_group)

        # Load saved provider from QSettings
        self._load_tts_settings()

        # Cài WheelGuard cho tất cả ComboBox/SpinBox để cấm scroll nhầm
        self._wheel_guard = _WheelGuard(self)
        for widget in self.findChildren((QComboBox, QSpinBox, QDoubleSpinBox)):
            widget.installEventFilter(self._wheel_guard)

    def _on_translate_api_changed(self, api_text):
        """Cập nhật danh sách model khi đổi API Provider."""
        self.translate_model_combo.clear()
        try:
            from dich import GEMINI_MODELS, OPENAI_MODELS, GROK_MODELS
        except ImportError:
            GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
            OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
            GROK_MODELS = ["grok-3", "grok-3-mini", "grok-2"]
        
        if 'Grok' in api_text:
            self.translate_model_combo.addItems(GROK_MODELS)
        elif 'OpenAI' in api_text or 'ChatGPT' in api_text:
            self.translate_model_combo.addItems(OPENAI_MODELS)
        else:
            self.translate_model_combo.addItems(GEMINI_MODELS)

    def _on_provider_changed(self, provider_text):
        """Cập nhật danh sách giọng khi đổi nhà cung cấp."""
        self.tts_voice_combo.clear()
        try:
            from chuyendoi_chinh import TIKTOK_VOICES, FPT_VOICES
        except ImportError:
            TIKTOK_VOICES = {'Vietnamese Female': 'BV074_streaming', 'Vietnamese Male': 'BV075_streaming'}
            FPT_VOICES = {'Ban Mai (Nữ Bắc)': 'banmai'}

        if 'TikTok' in provider_text:
            for name in sorted(TIKTOK_VOICES.keys()):
                self.tts_voice_combo.addItem(name, TIKTOK_VOICES[name])
            # Default: Vietnamese Female
            idx = self.tts_voice_combo.findText('Vietnamese Female')
            if idx >= 0: self.tts_voice_combo.setCurrentIndex(idx)
        elif 'FPT' in provider_text:
            for name, code in FPT_VOICES.items():
                self.tts_voice_combo.addItem(name, code)
        elif 'ElevenLabs' in provider_text:
            self.tts_voice_combo.addItem("(Dùng giọng đã cấu hình ở tab Chuyển Đổi)", "")

    def _load_tts_settings(self):
        """Đọc cài đặt TTS từ QSettings của tab Chuyển Đổi."""
        from PyQt6.QtCore import QSettings
        s = QSettings('BumYT', 'SrtToMp3')
        saved_provider = s.value('provider', 'TikTok TTS')
        idx = self.tts_provider_combo.findText(saved_provider)
        if idx >= 0:
            self.tts_provider_combo.setCurrentIndex(idx)
        # Restore saved voice
        saved_voice = s.value('tiktok_voice_name', 'Vietnamese Female')
        voice_idx = self.tts_voice_combo.findText(saved_voice)
        if voice_idx >= 0:
            self.tts_voice_combo.setCurrentIndex(voice_idx)

    def _refresh_table(self):
        self.table.setRowCount(len(self.jobs))
        for i, job in enumerate(self.jobs):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(job.name))
            status_item = QTableWidgetItem(job.status)
            if "✅" in job.status:
                status_item.setForeground(QColor(46, 204, 113))
            elif "❌" in job.status:
                status_item.setForeground(QColor(231, 76, 60))
            elif "🔄" in job.status or "🔍" in job.status or "🌐" in job.status or "🔊" in job.status:
                status_item.setForeground(QColor(124, 111, 240))
            self.table.setItem(i, 2, status_item)

    def _add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn Video", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.wmv);;All Files (*)")
        if files:
            for f in sorted(files):  # Sắp xếp theo tên
                self.jobs.append(VideoJob(video_path=f))
            self._refresh_table()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa video")
        if folder:
            exts = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv'}
            for f in sorted(os.listdir(folder)):
                if os.path.splitext(f)[1].lower() in exts:
                    self.jobs.append(VideoJob(video_path=os.path.join(folder, f)))
            self._refresh_table()

    def _clear_all(self):
        self.jobs.clear()
        self._refresh_table()

    def _start_pipeline(self):
        if not self.jobs:
            QMessageBox.warning(self, "Chú ý", "Hãy thêm video vào danh sách trước!")
            return

        do_ocr = self.chk_ocr.isChecked()
        do_translate = self.chk_translate.isChecked()
        do_tts = self.chk_tts.isChecked()

        if not any([do_ocr, do_translate, do_tts]):
            QMessageBox.warning(self, "Chú ý", "Hãy chọn ít nhất 1 bước xử lý!")
            return

        # Setup ROI nếu cần OCR (trừ Whisper)
        engine = self.ocr_engine_combo.currentText()
        if do_ocr and "Whisper" not in engine:
            dialog = ROISetupDialog(self.jobs, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return  # User cancelled

        # Reset trạng thái
        for job in self.jobs:
            job.status = "⏳ Chờ"
            job.error = ""
        self._refresh_table()
        self.log_edit.clear()
        self.progress_total.setValue(0)
        self.progress_step.setValue(0)

        # Build config
        lang_map = {
            "Trung → Việt": "vi", "Trung → English": "en",
            "Anh → Việt": "vi", "Nhật → Việt": "vi", "Hàn → Việt": "vi"
        }

        import dich
        
        # Get glossary path using dich's get_glossary_path
        glossary_name = self.glossary_combo.currentData()
        if not glossary_name:
            glossary_name = dich.DEFAULT_GLOSSARY
        glossary_path = dich.get_glossary_path(glossary_name)

        # Map API combo text -> internal name
        api_text = self.translate_api_combo.currentText()
        if 'Grok' in api_text:
            translate_api = 'grok'
        elif 'OpenAI' in api_text or 'ChatGPT' in api_text:
            translate_api = 'openai'
        else:
            translate_api = 'gemini'
        
        translate_model = self.translate_model_combo.currentText() or 'gemini-2.5-flash'

        config = {
            'do_ocr': do_ocr,
            'do_translate': do_translate,
            'do_tts': do_tts,
            'ocr_engine': engine.replace(" (Giọng nói)", ""),
            'ocr_fps': 10.0,
            'ocr_simi': 0.88,
            'ocr_gap': 3.5,
            'ocr_minseg': 0.10,
            'translate_api': translate_api,
            'translate_model': translate_model,
            'target_lang': lang_map.get(self.translate_lang_combo.currentText(), 'vi'),
            'glossary_path': glossary_path,
            'auto_filter_merge': self.chk_auto_filter.isChecked(),
            'tts_provider': self.tts_provider_combo.currentText(),
            'tts_voice_code': self.tts_voice_combo.currentData() or 'BV074_streaming',
            'tts_voice_name': self.tts_voice_combo.currentText(),
            'create_capcut': self.chk_capcut.isChecked(),
            'tts_speed': 1.0,
            'max_workers': 15,
            'subtitle_size': 8,
            'stop_on_error': self.chk_stop_on_error.isChecked(),
        }

        # Đọc cấu hình trực tiếp từ các tab đã khởi tạo trên MAIN thread (tránh QSettings chưa lưu)
        if hasattr(self, '_main_ocr_tab'):
            config['main_ocr_tab'] = self._main_ocr_tab
        if hasattr(self, '_main_tts_tab'):
            tts = self._main_tts_tab
            config['audio_edit_live'] = tts.audio_edit_checkbox.isChecked()
            config['delete_temp_live'] = tts.delete_temp_checkbox.isChecked()
            config['rename_temp_live'] = tts.rename_temp_files_checkbox.isChecked()
            config['speed_factor_live'] = tts.speed_slider.value()
            config['subtitle_size_live'] = tts.subtitle_size_slider.value()
            config['max_workers_live'] = tts.workers_spin.value()
            config['dubbing_mode_live'] = tts.dubbing_checkbox.isChecked()

        config['auto_shutdown'] = self.chk_auto_shutdown.isChecked()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.thread = QThread()
        self.worker = BatchPipelineWorker(self.jobs, config)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self._on_log)
        self.worker.progress_total.connect(self.progress_total.setValue)
        self.worker.progress_step.connect(self.progress_step.setValue)
        self.worker.video_status.connect(self._on_video_status)
        self.worker.step_info.connect(self.lbl_step.setText)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.start()

    def _stop_pipeline(self):
        if self.worker:
            self.worker.stop()
            self.log_edit.append("⏹️ Đang yêu cầu dừng pipeline...")

    def _on_log(self, msg):
        self.log_edit.append(msg)
        # Auto-scroll to bottom
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())

    def _on_video_status(self, idx, status):
        if 0 <= idx < len(self.jobs):
            self.jobs[idx].status = status
            status_item = QTableWidgetItem(status)
            if "✅" in status:
                status_item.setForeground(QColor(46, 204, 113))
            elif "❌" in status:
                status_item.setForeground(QColor(231, 76, 60))
            elif "🔄" in status or "🔍" in status or "🌐" in status or "🔊" in status:
                status_item.setForeground(QColor(124, 111, 240))
            self.table.setItem(idx, 2, status_item)

    def _on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_step.setText("🏆 Pipeline hoàn tất!")
        self.progress_total.setValue(100)
        
        do_shutdown = False
        if hasattr(self, 'worker') and getattr(self.worker, 'config', {}).get('auto_shutdown', False):
            do_shutdown = True
            
        if do_shutdown:
            self._start_shutdown_countdown()
        else:
            QMessageBox.information(self, "Hoàn tất", "🎉 Pipeline đã xử lý xong tất cả video!")

    def _start_shutdown_countdown(self):
        from PyQt6.QtCore import QTimer
        self.shutdown_dlg = QDialog(self)
        self.shutdown_dlg.setWindowTitle("Chuẩn bị tắt máy!")
        self.shutdown_dlg.setFixedSize(350, 150)
        lay = QVBoxLayout(self.shutdown_dlg)
        
        lbl_warn = QLabel("🎉 Pipeline đã xử lý xong tất cả video!")
        lbl_warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_warn.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 14px;")
        lay.addWidget(lbl_warn)
        
        self.lbl_countdown = QLabel("Đang chuẩn bị tắt máy tính sau 30 giây...")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_countdown.setStyleSheet("color: #e74c3c; font-size: 13px;")
        lay.addWidget(self.lbl_countdown)
        
        btn_cancel = QPushButton("Hủy Tắt Máy")
        btn_cancel.setStyleSheet("background: #555;")
        btn_cancel.clicked.connect(self._cancel_shutdown)
        lay.addWidget(btn_cancel)
        
        self.shutdown_time_left = 30
        self.shutdown_timer = QTimer(self.shutdown_dlg)
        self.shutdown_timer.timeout.connect(self._tick_shutdown)
        self.shutdown_timer.start(1000)
        
        self.shutdown_dlg.exec()

    def _tick_shutdown(self):
        self.shutdown_time_left -= 1
        if self.shutdown_time_left > 0:
            self.lbl_countdown.setText(f"Đang tự động tắt máy tính sau {self.shutdown_time_left} giây...")
        else:
            self.shutdown_timer.stop()
            self.shutdown_dlg.accept()
            import os
            self.log_edit.append("🔴 Bắt đầu tắt máy tính theo yêu cầu (Shutdown)...")
            os.system("shutdown /s /t 0")

    def _cancel_shutdown(self):
        self.shutdown_timer.stop()
        self.shutdown_dlg.reject()
        self.log_edit.append("✅ Đã hủy lệnh tự động tắt máy.")

    def _on_error(self, msg):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_step.setText("❌ Lỗi!")
        QMessageBox.critical(self, "Lỗi Pipeline", msg)
