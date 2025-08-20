from flask import Flask, render_template, Response
import yt_dlp
import requests
from cachetools import TTLCache

app = Flask(__name__, template_folder="templates")

# Cache (20 dk)
stream_cache = TTLCache(maxsize=256, ttl=60*20)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/proxy/<video_id>")
def proxy(video_id):
    try:
        # Cache kontrol
        if video_id in stream_cache:
            url = stream_cache[video_id]
        else:
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'quiet': True,
                'simulate': True,
                'forceurl': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                url = info.get('url')
                if not url:
                    return f"Error: DRM’li veya erişilemeyen video", 500
                stream_cache[video_id] = url

        # Stream
        def generate():
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(32*1024):
                    if chunk:
                        yield chunk

        return Response(generate(), mimetype="audio/mpeg")

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
