import os
import shlex
import subprocess
from os import environ
from subprocess import DEVNULL
from threading import Thread
from typing import Optional, Dict, Any, List

from youtube_dl import YoutubeDL

from pharaoh.progress_tracker import ProgressTracker


class Job:
    def __init__(self, source: str, name: str, destination: str, opts: Dict[str, Any], pp_input_opts: List[str],
                 pp_output_opts: List[str]):
        opts['progress_hooks'] = [self.progress_hook]
        self.name = name
        self.client = YoutubeDL(opts)
        self.destination = destination
        self.source = source
        self.pp_filename = None
        self.post_process_opts_input = pp_input_opts
        self.post_process_opts_output = pp_output_opts
        self.stage = 'download'
        self.progress: Optional[ProgressTracker] = ProgressTracker()
        self.downloader_thread = Thread(target=self._target)
        self.downloader_thread.start()

    def _target(self):
        try:
            self.client.download([self.source])
            self.stage = 'post-process'
            ffmpeg_path = shlex.split(environ.get('FFMPEG', 'ffmpeg'))

            args = [*ffmpeg_path, '-loglevel', '-8', '-y', *self.post_process_opts_input, '-i', self.pp_filename,
                    *self.post_process_opts_output, self.destination]
            subprocess.run(args, stdin=DEVNULL)
            self.stage = 'done'
            os.remove(self.pp_filename)
        except Exception:
            self.stage = 'error'
            raise

    def progress_hook(self, d):
        if d['status'] == 'error':
            self.stage = 'error'
            return
        if fn := d.get('filename'):
            self.pp_filename = fn
        if d['status'] == 'finished':
            self.progress.update_progress(1.0)
            return
        downloaded = d.get('downloaded_bytes')
        if downloaded is None:
            return
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        if total is None:
            return
        self.progress.update_progress(downloaded / total)
