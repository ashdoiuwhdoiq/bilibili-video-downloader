import json
import os
import re
import tempfile
import time
from threading import Lock, Thread
from uuid import uuid4

import requests
import yt_dlp
from flask import Flask, Response, jsonify, request, send_file, send_from_directory, stream_with_context
from flask_cors import CORS

app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*"}})

DOWNLOAD_DIR = tempfile.gettempdir()
DOWNLOAD_TASKS = {}
DOWNLOAD_TASKS_LOCK = Lock()
BILIBILI_REFERER = 'https://www.bilibili.com'
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
TERMINAL_TASK_STATUSES = {'finished', 'error', 'cancelled'}


class DownloadCancelled(Exception):
    pass


@app.route('/')
def serve_index():
    return send_from_directory('dist', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join('dist', path)):
        return send_from_directory('dist', path)
    return send_from_directory('dist', 'index.html')


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def should_enable_debug(debug_value):
    return str(debug_value).strip().lower() in {'1', 'true', 'yes', 'on'}


def format_bytes(value):
    if not value or value <= 0:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    value = float(value)
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    return f'{value:.{0 if unit_index == 0 else 1}f} {units[unit_index]}'


def format_speed(value):
    if not value or value <= 0:
        return '--'
    return f'{format_bytes(value)}/s'


def format_eta(value):
    if value is None or value < 0:
        return '--'
    minutes, seconds = divmod(int(value), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:d}:{minutes:02d}:{seconds:02d}' if hours else f'{minutes:d}:{seconds:02d}'


def get_browser_user_data_root(browser_name):
    roots = {
        'chrome': os.path.join(os.getenv('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data'),
        'edge': os.path.join(os.getenv('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data'),
        'firefox': os.path.join(os.getenv('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles'),
    }
    return roots.get(browser_name, '')


def find_browser_cookie_source():
    preferred_browser = os.getenv('BILIBILI_COOKIES_BROWSER', '').strip().lower()
    browsers = [preferred_browser] if preferred_browser else ['chrome', 'edge', 'firefox']
    for browser_name in browsers:
        if browser_name and os.path.isdir(get_browser_user_data_root(browser_name)):
            profile = os.getenv('BILIBILI_COOKIES_PROFILE') or None
            return (browser_name, profile, None, None)
    return None


def build_browser_user_agent(cookie_source):
    forced_user_agent = os.getenv('BILIBILI_USER_AGENT', '').strip()
    if forced_user_agent:
        return forced_user_agent
    if not cookie_source or cookie_source[0] not in {'chrome', 'edge'}:
        return DEFAULT_USER_AGENT
    browser_name = cookie_source[0]
    version_file = os.path.join(get_browser_user_data_root(browser_name), 'Last Version')
    version = ''
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r', encoding='utf-8') as file:
                version = file.read().strip()
        except OSError:
            version = ''
    version = version or '135.0.0.0'
    chrome_ua = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36'
    return f'{chrome_ua} Edg/{version}' if browser_name == 'edge' else chrome_ua


def build_ydl_options():
    cookie_source = find_browser_cookie_source()
    options = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'Referer': BILIBILI_REFERER,
            'User-Agent': build_browser_user_agent(cookie_source),
        },
    }
    if cookie_source:
        options['cookiesfrombrowser'] = cookie_source
    return options


def humanize_extractor_error(error_message):
    if 'HTTP Error 412' in error_message or 'Precondition Failed' in error_message:
        return '获取视频信息失败：B 站触发了风控。请先用同一台电脑上的 Chrome、Edge 或 Firefox 打开目标视频页，确认页面能正常播放并刷新一次，然后在 30 分钟内重试。如果仍然失败，可以设置环境变量 BILIBILI_COOKIES_BROWSER=chrome 或 edge 后再启动程序。'
    return error_message


def create_download_task(task_store, task_lock, payload):
    task = {
        'task_id': str(uuid4()),
        'url': payload['url'],
        'download_type': payload['type'],
        'format_id': payload.get('format_id', ''),
        'status': 'queued',
        'progress': 0,
        'speed_text': '--',
        'downloaded_text': '0 B',
        'total_text': '--',
        'eta_text': '--',
        'message': '等待开始',
        'error': '',
        'filename': '',
        'cancel_requested': False,
        'seq': 0,
        'created_at': time.time(),
    }
    with task_lock:
        task_store[task['task_id']] = task
    return task


def update_task(task, task_lock, **changes):
    with task_lock:
        task.update(changes)
        task['seq'] = task.get('seq', 0) + 1


def set_task_stage(task, task_lock, status, message):
    update_task(task, task_lock, status=status, message=message, progress=task.get('progress', 0))


def cancel_download_task(task, task_lock):
    update_task(task, task_lock, cancel_requested=True, status='cancelled', message='已取消', error='', eta_text='--')


def ensure_task_not_cancelled(task):
    if task.get('cancel_requested'):
        raise DownloadCancelled('下载已取消')


def serialize_task(task):
    return {
        'task_id': task['task_id'],
        'status': task['status'],
        'progress': task['progress'],
        'speed_text': task['speed_text'],
        'downloaded_text': task['downloaded_text'],
        'total_text': task['total_text'],
        'eta_text': task['eta_text'],
        'message': task['message'],
        'error': task['error'],
        'filename': os.path.basename(task['filename']) if task.get('filename') else '',
        'cancel_requested': task['cancel_requested'],
    }


def make_progress_hook(task, task_lock):
    def hook(progress_data):
        ensure_task_not_cancelled(task)
        status = progress_data.get('status')
        if status == 'downloading':
            downloaded_bytes = progress_data.get('downloaded_bytes') or 0
            total_bytes = progress_data.get('total_bytes') or progress_data.get('total_bytes_estimate') or 0
            progress = int(downloaded_bytes * 100 / total_bytes) if total_bytes else task.get('progress', 0)
            update_task(task, task_lock, status='downloading', progress=max(0, min(progress, 99 if total_bytes else progress)), speed_text=format_speed(progress_data.get('speed')), downloaded_text=format_bytes(downloaded_bytes), total_text=format_bytes(total_bytes) if total_bytes else '--', eta_text=format_eta(progress_data.get('eta')), message='下载中')
        elif status == 'finished':
            update_task(task, task_lock, status='processing', progress=100, filename=progress_data.get('filename', task.get('filename', '')), eta_text='0:00', message='正在合并音视频')
    return hook


def make_postprocessor_hook(task, task_lock):
    def hook(progress_data):
        ensure_task_not_cancelled(task)
        if progress_data.get('status') == 'started':
            update_task(task, task_lock, status='processing', progress=100, message='正在合并音视频')
    return hook


def build_download_options(title, download_type, format_id='', selected_format_type=''):
    base_options = build_ydl_options()
    if download_type == 'audio':
        return {**base_options, 'format': 'bestaudio/best', 'outtmpl': os.path.join(DOWNLOAD_DIR, f'{title}.%(ext)s')}
    if download_type == 'video':
        if selected_format_type and selected_format_type != 'video_only':
            raise ValueError('Video-only downloads require a video-only format')
        return {**base_options, 'format': format_id or 'bestvideo[ext=mp4]/bestvideo', 'outtmpl': os.path.join(DOWNLOAD_DIR, f'{title}_video.%(ext)s')}
    if download_type == 'both':
        options = {**base_options, 'format': f'{format_id or "bestvideo"}+bestaudio/best', 'merge_output_format': 'mp4', 'outtmpl': os.path.join(DOWNLOAD_DIR, f'{title}.%(ext)s'), 'quiet': False, 'no_warnings': False, 'overwrites': True}
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_exe = 'ffmpeg'
        if ffmpeg_exe != 'ffmpeg':
            options['ffmpeg_location'] = ffmpeg_exe
        return options
    raise ValueError('Unsupported download type')


def find_downloaded_file(prefix, excluded_suffixes=None):
    excluded_suffixes = excluded_suffixes or set()
    for filename in os.listdir(DOWNLOAD_DIR):
        if not filename.startswith(prefix) or filename.endswith('.part'):
            continue
        if any(filename.endswith(suffix) for suffix in excluded_suffixes):
            continue
        return os.path.join(DOWNLOAD_DIR, filename)
    return None


def clear_previous_downloads(prefix):
    for filename in os.listdir(DOWNLOAD_DIR):
        if filename.startswith(prefix) and not filename.endswith('.part'):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, filename))
            except OSError:
                continue


def find_selected_format_type(info, format_id):
    return next(('video+audio' if format_info.get('vcodec') != 'none' and format_info.get('acodec') != 'none' else 'video_only' if format_info.get('vcodec') != 'none' and format_info.get('acodec') == 'none' else '' for format_info in info.get('formats', []) if format_info.get('format_id') == format_id), '')


def complete_task_file(task, title):
    if task['download_type'] == 'audio':
        return find_downloaded_file(title)
    if task['download_type'] == 'video':
        return find_downloaded_file(f'{title}_video')
    return find_downloaded_file(title, {'_temp', '_video', '_audio'})


def run_download_task(task_id):
    task = DOWNLOAD_TASKS[task_id]
    try:
        set_task_stage(task, DOWNLOAD_TASKS_LOCK, 'loading_cookies', '正在读取浏览器 cookies')
        ydl_options = build_ydl_options()
        ensure_task_not_cancelled(task)
        set_task_stage(task, DOWNLOAD_TASKS_LOCK, 'parsing', '正在解析视频信息')
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(task['url'], download=False)
        ensure_task_not_cancelled(task)
        title = sanitize_filename(info.get('title', 'video'))
        selected_format_type = find_selected_format_type(info, task['format_id'])
        if task['download_type'] == 'both':
            clear_previous_downloads(title)
        download_options = build_download_options(title, task['download_type'], task['format_id'], selected_format_type)
        download_options['progress_hooks'] = [make_progress_hook(task, DOWNLOAD_TASKS_LOCK)]
        download_options['postprocessor_hooks'] = [make_postprocessor_hook(task, DOWNLOAD_TASKS_LOCK)]
        set_task_stage(task, DOWNLOAD_TASKS_LOCK, 'downloading', '开始下载')
        with yt_dlp.YoutubeDL(download_options) as ydl:
            ydl.download([task['url']])
        ensure_task_not_cancelled(task)
        output_file = complete_task_file(task, title)
        if not output_file or not os.path.exists(output_file):
            raise FileNotFoundError('文件下载失败')
        update_task(task, DOWNLOAD_TASKS_LOCK, status='finished', progress=100, filename=output_file, message='下载完成', eta_text='0:00', speed_text='--')
    except DownloadCancelled as exc:
        update_task(task, DOWNLOAD_TASKS_LOCK, status='cancelled', message='已取消', error=str(exc))
    except ValueError as exc:
        update_task(task, DOWNLOAD_TASKS_LOCK, status='error', message='下载失败', error=str(exc))
    except Exception as exc:
        update_task(task, DOWNLOAD_TASKS_LOCK, status='error', message='下载失败', error=humanize_extractor_error(str(exc)))


def start_download_task(task):
    worker = Thread(target=run_download_task, args=(task['task_id'],), daemon=True)
    worker.start()
    return worker


@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    data = request.json or {}
    url = data.get('url', '')
    if not url:
        return jsonify({'error': '请提供视频链接'}), 400
    try:
        with yt_dlp.YoutubeDL(build_ydl_options()) as ydl:
            info = ydl.extract_info(url, download=False)
        title = info.get('title', '未知标题')
        thumbnail = info.get('thumbnail', '')
        duration = info.get('duration', 0)
        uploader = info.get('uploader', '未知作者')
        formats = []
        seen_resolutions = set()
        for format_info in info.get('formats', []):
            has_video = format_info.get('vcodec') != 'none'
            has_audio = format_info.get('acodec') != 'none'
            resolution = format_info.get('resolution', 'unknown')
            if not has_video or resolution == 'unknown' or resolution in seen_resolutions:
                continue
            formats.append({'format_id': format_info['format_id'], 'resolution': resolution, 'ext': format_info.get('ext', 'mp4'), 'type': 'video+audio' if has_audio else 'video_only'})
            seen_resolutions.add(resolution)
        resolution_order = {'2160p': 7, '1440p': 6, '1080p': 5, '720p': 4, '480p': 3, '360p': 2, '240p': 1, '144p': 0}
        formats.sort(key=lambda item: resolution_order.get(item['resolution'].split('x')[0] if 'x' in item['resolution'] else item['resolution'], -1), reverse=True)
        audio_formats = []
        for format_info in info.get('formats', []):
            if format_info.get('acodec') != 'none' and format_info.get('vcodec') == 'none':
                audio_formats.append({'format_id': format_info['format_id'], 'abr': format_info.get('abr', 0), 'ext': format_info.get('ext', 'm4a'), 'type': 'audio_only'})
                break
        return jsonify({'title': title, 'thumbnail': thumbnail, 'duration': duration, 'uploader': uploader, 'formats': formats, 'audio_formats': audio_formats})
    except Exception as exc:
        return jsonify({'error': humanize_extractor_error(f'获取视频信息失败: {exc}')}), 500


@app.route('/api/download-tasks', methods=['POST'])
def create_download_task_endpoint():
    data = request.json or {}
    if not data.get('url'):
        return jsonify({'error': '请提供视频链接'}), 400
    if data.get('type', 'video') != 'audio' and not data.get('format_id'):
        return jsonify({'error': '请选择分辨率'}), 400
    task = create_download_task(DOWNLOAD_TASKS, DOWNLOAD_TASKS_LOCK, data)
    start_download_task(task)
    return jsonify({'task_id': task['task_id']})


@app.route('/api/download-tasks/<task_id>/events')
def stream_download_task_events(task_id):
    task = DOWNLOAD_TASKS.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    def event_stream():
        last_seq = -1
        while True:
            with DOWNLOAD_TASKS_LOCK:
                current_task = DOWNLOAD_TASKS.get(task_id)
                if not current_task:
                    break
                current_seq = current_task.get('seq', 0)
                payload = serialize_task(current_task)
                terminal = current_task['status'] in TERMINAL_TASK_STATUSES
            if current_seq != last_seq:
                yield f'data: {json.dumps(payload, ensure_ascii=False)}\n\n'
                last_seq = current_seq
            if terminal:
                break
            time.sleep(0.25)
    return Response(stream_with_context(event_stream()), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})


@app.route('/api/download-tasks/<task_id>/cancel', methods=['POST'])
def cancel_download_task_endpoint(task_id):
    task = DOWNLOAD_TASKS.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    if task['status'] in TERMINAL_TASK_STATUSES:
        return jsonify({'error': '任务已结束'}), 409
    cancel_download_task(task, DOWNLOAD_TASKS_LOCK)
    return jsonify({'ok': True})


@app.route('/api/download-tasks/<task_id>/file')
def download_task_file(task_id):
    task = DOWNLOAD_TASKS.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    if task['status'] != 'finished' or not task.get('filename'):
        return jsonify({'error': '文件尚未就绪'}), 409
    return send_file(task['filename'], as_attachment=True)


@app.route('/api/thumbnail')
def proxy_thumbnail():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'error': '请提供图片 URL'}), 400
    try:
        response = requests.get(url, headers={'Referer': BILIBILI_REFERER, 'User-Agent': build_browser_user_agent(find_browser_cookie_source())}, timeout=10)
        if response.status_code != 200:
            return jsonify({'error': '获取图片失败'}), 500
        return Response(response.content, mimetype=response.headers.get('Content-Type', 'image/jpeg'), headers={'Cache-Control': 'public, max-age=3600'})
    except Exception as exc:
        return jsonify({'error': f'获取图片失败: {exc}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=should_enable_debug(os.getenv('FLASK_DEBUG')))
