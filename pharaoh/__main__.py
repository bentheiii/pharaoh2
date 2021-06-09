import os
from itertools import accumulate, repeat, chain
from os import getcwd, chdir
from sys import argv
from time import perf_counter, sleep
from traceback import print_exc
from typing import List, Sequence, Callable, Any

from bidi.algorithm import get_display
from prompt_toolkit import print_formatted_text, PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.shortcuts import clear

from pharaoh.colors import RED, GREEN, GRAY, WHITE, YELLOW
from pharaoh.command import Command
from pharaoh.dl_job import Job
from pharaoh.job_factory import create_job
from pharaoh.utils import secs_to_duration


def split_args(args: Sequence[str], *types: Callable[[str], Any]) -> Sequence[Any]:
    if len(args) != len(types):
        raise ValueError(f'expected {len(types)} arguments, got {len(args)}')
    return tuple(c(v) for (c, v) in zip(types, args))


EXIT_CHECK_INTERVAL = 0.25
JOB_NAME_DISPLAY_LENGTH = 70


class App:
    def __init__(self):
        self._jobs: List[Job] = []

    def jobs_running(self):
        return [j for j in self._jobs if j.stage not in ("done", "err")]

    @Command
    def show(self, args):
        """
        Show progress for all running jobs
        """
        split_args(args, )
        parts = []
        for job, filler_char in zip(self._jobs, chain.from_iterable(repeat('·-'))):
            if len(job.name) > JOB_NAME_DISPLAY_LENGTH:
                name = job.name[:JOB_NAME_DISPLAY_LENGTH - 3] + "..."
            else:
                name = job.name.ljust(JOB_NAME_DISPLAY_LENGTH, filler_char)

            name = get_display(name)

            if job.stage == 'error':
                color = RED
                prog = 'ERR'
            elif job.stage == 'done':
                color = GREEN
                prog = 'Done'
            else:
                color = GRAY
                if job.stage == 'post-process':
                    prog = 'postprocess'
                else:
                    eta = secs_to_duration(job.progress.estimated_completion_time() - perf_counter())
                    prog = f'{job.progress.current_progress:.1%} (ETA {eta})'

            parts.extend((
                ('', name),
                ('', filler_char),
                (color, prog),
                ('', '\n'),
            ))
        print_formatted_text(FormattedText(parts))

    @Command
    def watch(self, args):
        """
        Show progress for all running jobs, and keep updating every second
        """
        split_args(args, )
        try:
            while True:
                self.show(args)
                sleep(1)
                clear()
        except KeyboardInterrupt:
            pass

    @Command
    def trim(self, args):
        """
        Show progress for all running jobs, and remove all finished and errored jobs
        """
        split_args(args, )
        self.show(args)
        self._jobs = [j for j in self._jobs if j.stage not in ("done", "err")]

    @Command
    def add(self, args):
        """
        Start a download job
        """
        url, *rest = args
        dest = ' '.join(rest) if rest else None
        self._jobs.append(create_job(url, dest))

    @Command
    def exit(self, args):
        """
        Exit the program
        """
        split_args(args, )
        while True:
            jobs_not_done = len(self.jobs_running())
            if jobs_not_done:
                print_formatted_text(f"waiting for running jobs, {jobs_not_done} left...")
                sleep(EXIT_CHECK_INTERVAL)
                clear()
            else:
                exit(0)

    @Command
    def exit_force(self, args):
        split_args(args, )
        exit(0)

    @Command
    def cd(self, args):
        """
        Change the current working directory
        """
        dest = " ".join(args)
        if not dest:
            print_formatted_text(get_display(getcwd()))
        else:
            if self.jobs_running():
                print_formatted_text(FormattedText([
                    (RED, 'cannot change directory while jobs are in progress')
                ]))
            else:
                chdir(dest)

    @Command
    def help(self, args):
        """
        Print this help message
        """
        split_args(args, )
        commands = []
        for name, value in vars(type(self)).items():
            if not getattr(value, '__command__', False):
                continue
            commands.append((
                name, getattr(value, '__doc__', None) or 'description not found'
            ))
        commands.sort()
        parts = FormattedText(list(chain.from_iterable(
            (
                (WHITE, name + ":"),
                ('', doc + "\n"),
            ) for (name, doc) in commands
        )))
        print_formatted_text(parts)

    def command(self, args: Sequence[str]):
        first, *args = args
        attr_names = accumulate(args, lambda a, b: a + "_" + b, initial=first)
        attrs = [getattr(self, name, None) for name in attr_names]
        try:
            i, last_match = next(
                (i, a) for (i, a) in enumerate(reversed(attrs))
                if getattr(a, '__command__', False)
            )
        except StopIteration:
            print_formatted_text(FormattedText([(RED, 'command not found')]))
            return

        args = args[-i:]

        try:
            last_match(args)
        except Exception:
            print_formatted_text(FormattedText([(RED, 'Error when running command')]))
            print_exc()

    def run(self):
        completer = NestedCompleter({
            'show': None,
            'trim': None,
            'add': None,
            'watch': None,
            'exit': NestedCompleter({
                'force': None
            }),
            'cd': None,
            'help': None,
        })

        prompt_session = PromptSession("enter a command:\n- ", completer=completer, bottom_toolbar=getcwd)
        interrupt_attempted = False
        while True:
            try:
                command: str = prompt_session.prompt()
                self.command([word.strip() for word in command.split()])
                interrupt_attempted = False
            except KeyboardInterrupt:
                if interrupt_attempted or not self.jobs_running():
                    raise
                interrupt_attempted = True
                print_formatted_text(FormattedText([
                    (YELLOW, 'some jobs are still running, to exit safely, use the "exit" command, to exit immediately,'
                             ' press ctrl+C again or use the "exit force" command')
                ]))


if __name__ == '__main__':
    args = argv[1:]
    if len(args) == 0:
        pass
    elif len(args) == 1:
        chdir(args[0])
    else:
        raise RuntimeError('at most 1 argument is acceptable')

    app = App()
    app.run()
