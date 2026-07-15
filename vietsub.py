#!/usr/bin/env python3
"""
Vietsub Tool - Dùng whisper + Google Translate + FFmpeg
Không cần BumYT, chỉ cần pip install faster-whisper

Usage:
    pip install faster-whisper
    python vietsub.py video.mp4
"""
import os, sys, subprocess, tempfile, json, argparse, time

# Có thể chỉnh đường dẫn FFmpeg nếu có sẵn
FFMPEG = "ffmpeg"  # hoặc "D:\\BumYT\\BumYT\\ffmpeg\\ffmpeg.exe"

def extract_audio(video_in):
    print("  Tach audio...")
    audio = tempfile.mktemp(suffix=".wav")
    subprocess.run([FFMPEG, "-i", video_in, "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1", "-y", audio],
                   capture_output=True, check=True)
    return audio

def transcribe(audio, model_size="base"):
    print(f"  Nhan dang giong noi (Whisper {model_size})...")
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, language="zh", beam_size=3)
    subs = []
    for seg in segments:
        subs.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
    return subs

def translate(subs):
    print("  Dich Trung -> Viet...")
    import requests
    for i, s in enumerate(subs):
        if not s["text"].strip():
            s["vi"] = ""
            continue
        try:
            r = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "zh-CN", "tl": "vi",
                        "dt": "t", "q": s["text"]},
                timeout=10
            )
            s["vi"] = json.loads(r.text)[0][0][0]
        except:
            s["vi"] = s["text"]
        if i % 10 == 0:
            print(f"     {i}/{len(subs)}")
    return subs

def write_srt(subs, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(subs, 1):
            vi = s.get("vi", s["text"])
            if not vi.strip():
                continue
            def fmt(sec):
                h = int(sec // 3600)
                m = int((sec % 3600) // 60)
                sv = sec % 60
                return f"{h:02d}:{m:02d}:{sv:06.3f}".replace(".", ",")
            f.write(f"{i}\n{fmt(s['start'])} --> {fmt(s['end'])}\n{vi}\n\n")

def burn_sub(video_in, srt_path, video_out):
    print("  Ghi sub vao video...")
    subprocess.run([FFMPEG, "-i", video_in, "-vf",
                    f"subtitles={srt_path}:force_style='Fontname=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00808080,BorderStyle=3,Outline=2,MarginV=40'",
                    "-c:a", "copy", "-y", video_out],
                   capture_output=True, check=True)
    print(f"  -> {video_out}")

def main():
    parser = argparse.ArgumentParser(description="Vietsub Video (Whisper + Google Translate)")
    parser.add_argument("input", help="File video (.mp4, .avi, .mkv...)")
    parser.add_argument("-o", "--output", help="File output (mac dinh: input_vietsub.mp4)")
    parser.add_argument("-m", "--model", default="base",
                        choices=["tiny", "base", "small", "medium", "large-v3"])
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[!] File khong ton tai: {args.input}")
        sys.exit(1)

    out = args.output or args.input.rsplit(".", 1)[0] + "_vietsub.mp4"
    start = time.time()

    print(f"[1/3] Xy ly audio...")
    audio = extract_audio(args.input)

    print(f"[2/3] Nhan dang + dich...")
    subs = transcribe(audio, args.model)
    os.unlink(audio)
    print(f"     {len(subs)} doan van ban")
    subs = translate(subs)

    print(f"[3/3] Xuat video...")
    srt = tempfile.mktemp(suffix=".srt")
    write_srt(subs, srt)
    burn_sub(args.input, srt, out)
    os.unlink(srt)

    elapsed = time.time() - start
    print(f"\n[OK] Xong! {elapsed:.0f}s")
    print(f"     Output: {out}")

if __name__ == "__main__":
    main()
