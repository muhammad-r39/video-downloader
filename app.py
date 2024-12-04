from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

@app.route('/get-formats', methods=['POST'])
def get_formats():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400

        ydl_opts = {}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            for fmt in info.get('formats', []):
                filesize_bytes = fmt.get('filesize')
                readable_filesize = format_filesize(filesize_bytes) if filesize_bytes else ''

                formats.append({
                    'format_id': fmt['format_id'],
                    'resolution': fmt.get('resolution', 'unknown'),
                    'ext': fmt['ext'],
                    'url': fmt.get('url', ''),
                    'filesize': readable_filesize
                })

        # Extract additional metadata
        video_title = info.get('title', 'Unknown Title')
        platform = info.get('extractor', 'Unknown Platform')
        thumbnail = info.get('thumbnail', '')

        return jsonify({
            "formats": formats,
            "title": video_title,
            "platform": platform.capitalize(),
            "thumbnail": thumbnail
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def format_filesize(size_bytes):
    if size_bytes is None:
        return ""
    for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
