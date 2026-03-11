import unittest
from threading import Lock
from unittest.mock import patch

import api


class ApiBehaviorTests(unittest.TestCase):
    def test_combined_download_uses_selected_format_with_audio(self):
        options = api.build_download_options('Example', 'both', 'video-720')

        self.assertEqual(options['format'], 'video-720+bestaudio/best')
        self.assertEqual(options['merge_output_format'], 'mp4')

    def test_video_only_download_rejects_muxed_format(self):
        with self.assertRaises(ValueError):
            api.build_download_options('Example', 'video', 'muxed-1080', selected_format_type='video+audio')

    def test_video_only_download_accepts_video_only_format(self):
        options = api.build_download_options('Example', 'video', 'video-720', selected_format_type='video_only')

        self.assertEqual(options['format'], 'video-720')
        self.assertIn('_video', options['outtmpl'])

    def test_debug_mode_is_disabled_by_default(self):
        self.assertFalse(api.should_enable_debug(None))
        self.assertFalse(api.should_enable_debug('0'))

    def test_debug_mode_can_be_enabled_explicitly(self):
        self.assertTrue(api.should_enable_debug('1'))

    def test_ydl_options_include_bilibili_headers(self):
        options = api.build_ydl_options()

        self.assertEqual(options['http_headers']['Referer'], 'https://www.bilibili.com')
        self.assertIn('Mozilla/5.0', options['http_headers']['User-Agent'])

    def test_ydl_options_enable_browser_cookies_when_available(self):
        with patch('api.find_browser_cookie_source', return_value=('chrome', None, None, None)):
            options = api.build_ydl_options()

        self.assertEqual(options['cookiesfrombrowser'], ('chrome', None, None, None))

    def test_412_error_is_rewritten_into_actionable_guidance(self):
        message = api.humanize_extractor_error('ERROR: [BiliBili] abc: Unable to download webpage: HTTP Error 412: Precondition Failed')

        self.assertIn('B 站触发了风控', message)
        self.assertIn('Chrome', message)

    def test_create_download_task_initializes_waiting_state(self):
        with patch('api.uuid4', return_value='task-1'):
            tasks = {}
            task = api.create_download_task(tasks, Lock(), {'url': 'https://example.com', 'type': 'both'})

        self.assertEqual(task['task_id'], 'task-1')
        self.assertEqual(task['status'], 'queued')
        self.assertEqual(task['progress'], 0)

    def test_progress_hook_updates_task_metrics(self):
        task = {
            'task_id': 'task-1',
            'status': 'queued',
            'progress': 0,
            'speed_text': '',
            'downloaded_text': '',
            'total_text': '',
            'eta_text': '',
            'error': '',
        }
        hook = api.make_progress_hook(task, Lock())

        hook({
            'status': 'downloading',
            'downloaded_bytes': 50,
            'total_bytes': 100,
            'speed': 1024 * 1024,
            'eta': 3,
        })

        self.assertEqual(task['status'], 'downloading')
        self.assertEqual(task['progress'], 50)
        self.assertIn('1.0 MB/s', task['speed_text'])

    def test_progress_hook_marks_finished_download(self):
        task = {
            'task_id': 'task-1',
            'status': 'downloading',
            'progress': 90,
            'speed_text': '',
            'downloaded_text': '',
            'total_text': '',
            'eta_text': '',
            'error': '',
        }
        hook = api.make_progress_hook(task, Lock())

        hook({'status': 'finished', 'filename': 'C:/tmp/file.mp4'})

        self.assertEqual(task['status'], 'processing')
        self.assertEqual(task['progress'], 100)
        self.assertEqual(task['filename'], 'C:/tmp/file.mp4')

    def test_stage_update_changes_message_without_advancing_progress(self):
        task = api.create_download_task({}, Lock(), {'url': 'https://example.com', 'type': 'both'})

        api.set_task_stage(task, Lock(), 'loading_cookies', '正在读取浏览器 cookies')

        self.assertEqual(task['status'], 'loading_cookies')
        self.assertEqual(task['message'], '正在读取浏览器 cookies')
        self.assertEqual(task['progress'], 0)

    def test_progress_hook_raises_when_task_was_cancelled(self):
        task = {
            'task_id': 'task-1',
            'status': 'downloading',
            'progress': 10,
            'speed_text': '',
            'downloaded_text': '',
            'total_text': '',
            'eta_text': '',
            'error': '',
            'cancel_requested': True,
        }
        hook = api.make_progress_hook(task, Lock())

        with self.assertRaises(api.DownloadCancelled):
            hook({'status': 'downloading', 'downloaded_bytes': 20, 'total_bytes': 100})

    def test_cancel_download_task_sets_cancelled_state(self):
        task = api.create_download_task({}, Lock(), {'url': 'https://example.com', 'type': 'both'})

        api.cancel_download_task(task, Lock())

        self.assertTrue(task['cancel_requested'])
        self.assertEqual(task['status'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
