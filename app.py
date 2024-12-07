from flask import Flask, request, jsonify, send_file, after_this_request
import yt_dlp
import os
import subprocess
import uuid

app = Flask(__name__)

OUTPUT_FOLDER = "/app/converted_videos"

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/get-formats', methods=['POST'])
def get_formats():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400

        ydl_opts = {}

        # Add Instagram authentication if URL is from Instagram
        if 'instagram.com' in url:
            try:
                ydl_opts.update({
                    'cookiefile': 'instagram_cookies.txt',
                })
            except KeyError as e:
                return jsonify({"error": f"Instagram extractor error: {str(e)}"}), 500

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            for fmt in info.get('formats', []):

                filesize_bytes = fmt.get('filesize')
                readable_filesize = format_filesize(filesize_bytes) if filesize_bytes else ''
                file_extension = fmt.get('ext', 'unknown')

                if 'm3u8' in fmt.get('url', ''):
                    file_extension = 'm3u8'
                elif fmt.get('vcodec') == 'none':
                    file_extension = fmt.get('ext', 'audio')

                formats.append({
                    'format_id': fmt['format_id'],
                    'resolution': fmt.get('resolution', 'unknown'),
                    'ext': file_extension,
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

@app.route('/convert', methods=['POST'])
def convert():
    try:
        data = request.get_json()
        url = data.get('url')
        format_id = data.get('format_id')
        if not url or not format_id:
            return jsonify({"error": "URL and format_id are required"}), 400

        # Use yt-dlp to download the desired format
        temp_filename = f"/tmp/{uuid.uuid4()}.m3u8"
        ydl_opts = {
            'format': format_id,
            'outtmpl': temp_filename,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Convert the m3u8 file to MP4 using FFmpeg
        output_filename = os.path.join(OUTPUT_FOLDER, f"{uuid.uuid4()}.mp4")
        ffmpeg_command = [
            'ffmpeg', '-i', temp_filename, '-c:v', 'copy', '-c:a', 'copy', output_filename
        ]
        subprocess.run(ffmpeg_command, check=True)

        # Clean up temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        return jsonify({
            "success": True,
            "message": "Conversion successful",
            "download_url": f"/converted_videos/{os.path.basename(output_filename)}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/converted_videos/<path:filename>', methods=['GET'])
def serve_converted_video(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # Cleanup logic after serving the file
    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            app.logger.error(f"Failed to delete file {file_path}: {e}")
        return response

    return send_file(file_path, as_attachment=True)

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
