# -*- coding: utf-8 -*-
"""
動画分析モジュール
yt-dlpで動画DL → ffprobe/ffmpeg でカット・音声分析 → Whisper で文字起こし → スコアリング
"""
import os, json, subprocess, tempfile, re, sys

FFMPEG  = "C:/ffmpeg/bin/ffmpeg.exe"
FFPROBE = "C:/ffmpeg/bin/ffprobe.exe"

HOOK_PATTERNS = [
    (r"知らないと|損する|やばい|ヤバい", "危機感・損失回避"),
    (r"これ見て|見て|え、|なんで|どうして", "好奇心ギャップ"),
    (r"\d+秒|\d+分|\d+個|\d+選", "数字・具体性"),
    (r"ぶっちゃけ|実は|本当は|正直", "暴露・本音"),
    (r"やってみた|試してみた|行ってみた", "体験談"),
    (r"教えて|方法|コツ|やり方", "ノウハウ・How-to"),
    (r"びっくり|驚き|信じられない|まじか", "驚き・サプライズ"),
    (r"あるある|わかる|共感", "共感"),
    (r"had to|omg|wait|no way|you need", "英語フック"),
]

CTA_PATTERNS = [
    r"コメント|comment",
    r"保存|save|セーブ",
    r"フォロー|follow",
    r"リンク|link|プロフ",
    r"いいね|like",
]


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kwargs)


def get_video_info(path):
    r = run([FFPROBE, "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", path])
    return json.loads(r.stdout)


def detect_cuts(path):
    """シーンチェンジ検出でカット数・平均カット間隔を算出"""
    r = run([FFMPEG, "-i", path,
             "-vf", "select='gt(scene,0.3)',showinfo",
             "-vsync", "vfr", "-f", "null", "-"], timeout=60)
    times = [float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    return times


def extract_audio(video_path, out_path):
    run([FFMPEG, "-y", "-i", video_path, "-vn",
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out_path], timeout=60)


def transcribe(audio_path):
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(audio_path, language="ja", beam_size=3,
                                word_timestamps=False)
    segments = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segs]
    return segments


def detect_bgm(audio_path):
    """音声ファイルのRMSエネルギーでBGM有無を推定"""
    try:
        import librosa, numpy as np
        y, sr = librosa.load(audio_path, sr=16000, duration=30)
        # 高周波成分が強ければBGMあり
        stft = np.abs(librosa.stft(y))
        high = stft[stft.shape[0]//2:].mean()
        low  = stft[:stft.shape[0]//2].mean()
        return bool(high / (low + 1e-9) > 0.4)
    except Exception:
        return None


def classify_hook(segments):
    """最初のセグメント（冒頭2秒）のフック型を判定"""
    if not segments:
        return "不明", ""
    first_text = " ".join(s["text"] for s in segments if s["start"] < 3)
    for pattern, label in HOOK_PATTERNS:
        if re.search(pattern, first_text, re.IGNORECASE):
            return label, first_text
    return "その他", first_text


def detect_cta(segments):
    all_text = " ".join(s["text"] for s in segments)
    found = []
    for p in CTA_PATTERNS:
        if re.search(p, all_text, re.IGNORECASE):
            found.append(p.split("|")[0])
    return found


def analyze(video_url, meta=None):
    """
    video_url: TikTok/YouTube URL
    meta: dict（views, likes, comments, duration_sec など既取得のメタ）
    returns: dict
    """
    result = {"url": video_url, "error": None}

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        audio_path = os.path.join(tmpdir, "audio.wav")

        # 1. ダウンロード
        print("[analyzer] ダウンロード中...")
        r = run([sys.executable, "-m", "yt_dlp",
                 "-f", "mp4/best[height<=720]",
                 "-o", video_path, video_url], timeout=120)
        if not os.path.exists(video_path):
            result["error"] = "ダウンロード失敗: " + r.stderr[-200:]
            return result

        # 2. 基本情報
        print("[analyzer] 動画情報取得中...")
        info = get_video_info(video_path)
        fmt  = info.get("format", {})
        duration = float(fmt.get("duration", meta.get("duration_sec", 0) if meta else 0))
        streams = info.get("streams", [])
        vstream = next((s for s in streams if s["codec_type"] == "video"), {})
        width  = vstream.get("width", 0)
        height = vstream.get("height", 0)
        fps_raw = vstream.get("r_frame_rate", "30/1").split("/")
        fps = round(int(fps_raw[0]) / max(int(fps_raw[1]), 1), 1)
        is_vertical = height > width

        # 3. カット検出
        print("[analyzer] カット分析中...")
        cut_times = detect_cuts(video_path)
        cut_count = len(cut_times) + 1
        avg_cut_sec = round(duration / cut_count, 1) if cut_count > 0 else duration

        # 4. 音声抽出
        print("[analyzer] 音声抽出中...")
        extract_audio(video_path, audio_path)

        # 5. BGM検出
        has_bgm = detect_bgm(audio_path)

        # 6. 文字起こし
        print("[analyzer] 文字起こし中（Whisper）...")
        segments = transcribe(audio_path)
        full_text = " ".join(s["text"] for s in segments)
        char_count = len(full_text.replace(" ", ""))
        speech_pace = round(char_count / duration, 1) if duration > 0 else 0

        # 7. フック分類
        hook_type, hook_text = classify_hook(segments)

        # 8. CTA検出
        cta = detect_cta(segments)

        # 9. スコアリング（0〜100）
        score = 0
        score += min(30, int(30 * min(avg_cut_sec, 5) / 5) if avg_cut_sec <= 3 else max(0, 30 - int((avg_cut_sec - 3) * 10)))
        score += 20 if is_vertical else 0
        score += 15 if hook_type != "その他" and hook_type != "不明" else 0
        score += 10 if has_bgm else 0
        score += 10 if cta else 0
        score += min(15, int(15 * min(speech_pace, 8) / 8))

        result.update({
            "duration_sec": round(duration, 1),
            "resolution": f"{width}x{height}",
            "is_vertical": is_vertical,
            "fps": fps,
            "cut_count": cut_count,
            "avg_cut_sec": avg_cut_sec,
            "tempo": "高速" if avg_cut_sec <= 2 else "標準" if avg_cut_sec <= 4 else "低速",
            "has_bgm": has_bgm,
            "hook_type": hook_type,
            "hook_text": hook_text[:60],
            "cta": cta,
            "speech_pace": speech_pace,
            "transcript": [s["text"] for s in segments],
            "score": score,
            "score_breakdown": {
                "テンポ": min(30, score),
                "縦型フォーマット": 20 if is_vertical else 0,
                "フック強度": 15 if hook_type not in ("その他","不明") else 0,
                "BGM": 10 if has_bgm else 0,
                "CTA": 10 if cta else 0,
                "話速": min(15, int(15 * min(speech_pace, 8) / 8)),
            }
        })

    return result


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        print("Usage: python analyzer.py <url>")
        sys.exit(1)
    import pprint
    pprint.pprint(analyze(url))
