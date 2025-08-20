from flask import Flask, render_template, request, Response
from ytmusicapi import YTMusic
from cachetools import TTLCache
import yt_dlp
import requests

app = Flask(__name__, template_folder="templates")
ytm = YTMusic()
stream_cache = TTLCache(maxsize=256, ttl=60*20)  # 20 dk cache

def pick_max_thumb(thumbnails):
    if not thumbnails:
        return None
    best = max(thumbnails, key=lambda t: t.get("width",0)*t.get("height",0))
    url = best.get("url")
    if url and "hqdefault" in url:
        url = url.replace("hqdefault","maxresdefault")
    return url or best.get("url")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/search")
def api_search():
    q = request.args.get("q","").strip()
    if not q:
        return {"results":[]}
    raw = ytm.search(q, limit=20)
    results=[]
    for item in raw:
        video_id = item.get("videoId")
        if not video_id:
            continue
        title = item.get("title")
        artists = ", ".join([a["name"] for a in item.get("artists",[])]) if item.get("artists") else None
        album = (item.get("album") or {}).get("name") if item.get("album") else None
        duration = item.get("duration")
        cover = pick_max_thumb(item.get("thumbnails") or [])
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
    return {"results": results}

@app.route("/proxy/<video_id>")
def proxy(video_id):
    try:
        if video_id in stream_cache:
            url = stream_cache[video_id]
        else:
            ydl_opts = {'format':'bestaudio/best','quiet':True,'simulate':True,'forceurl':True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                url = info['url']
                stream_cache[video_id] = url
        def generate():
            with requests.get(url, stream=True) as r:
                for chunk in r.iter_content(32*1024):
                    if chunk:
                        yield chunk
        return Response(generate(), mimetype="audio/mpeg")
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
