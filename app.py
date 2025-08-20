import os
from flask import Flask, jsonify, request, redirect, send_from_directory, render_template
from ytmusicapi import YTMusic
import yt_dlp
from cachetools import TTLCache

app = Flask(__name__, template_folder="templates")

# YTMusic: anonim arama için yeterli
ytm = YTMusic()

# VideoID -> stream URL cache (yenilenebilir, kısa TTL)
stream_cache = TTLCache(maxsize=256, ttl=60 * 20)  # 20 dk

def pick_max_thumb(thumbnails):
    # ytmusicapi thumbnails: [{url,width,height}, ...] -> en büyük alanı seç
    if not thumbnails:
        return None
    best = max(thumbnails, key=lambda t: (t.get("width", 0) * t.get("height", 0)))
    # bazen url'ler s=.. ile küçük gelir; maxres denemesi:
    url = best.get("url")
    if url and "hqdefault" in url:
        url = url.replace("hqdefault", "maxresdefault")
    return url or best.get("url")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    # ytmusicapi: filter="songs" + "videos" karışık sonuç için sadece search
    raw = ytm.search(q, limit=20)
    results = []
    for item in raw:
        video_id = item.get("videoId")
        if not video_id:
            continue
        title = item.get("title")
        artists = ", ".join([a["name"] for a in item.get("artists", [])]) if item.get("artists") else None
        album = (item.get("album") or {}).get("name") if item.get("album") else None
        duration = item.get("duration")
        thumbnails = item.get("thumbnails") or []
        cover = pick_max_thumb(thumbnails)
        is_explicit = bool(item.get("isExplicit"))
        results.append({
            "videoId": video_id,
            "title": title,
            "artists": artists,
            "album": album,
            "duration": duration,
            "cover": cover,
            "explicit": is_explicit
        })
    return jsonify({"results": results})

def ytdlp_best_audio_url(video_id: str) -> str:
    if video_id in stream_cache:
        return stream_cache[video_id]
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        direct = info.get("url")
        if not direct:
            # bazı durumlarda format listesine bak
            fmts = info.get("formats") or []
            audio_only = [f for f in fmts if f.get("acodec") != "none"]
            audio_only.sort(key=lambda f: (f.get("abr") or 0, f.get("tbr") or 0), reverse=True)
            if audio_only:
                direct = audio_only[0].get("url")
        if not direct:
            raise RuntimeError("Akış URL’si bulunamadı.")
        stream_cache[video_id] = direct
        return direct

@app.route("/stream/<video_id>")
def stream(video_id):
    try:
        direct = ytdlp_best_audio_url(video_id)
        # Tarayıcı <audio> için 302 ile gerçek GoogleVideo akışına yönlendir
        return redirect(direct, code=302)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (Opsiyonel) Basit health check
@app.route("/healthz")
def health():
    return "ok"
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
