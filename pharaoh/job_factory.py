import re
from os import getcwd
from itertools import chain
from shlex import quote
from unicodedata import normalize

from click import confirm
from prompt_toolkit import prompt, print_formatted_text, HTML
from prompt_toolkit.validation import Validator
from prompt_toolkit.completion import FuzzyWordCompleter, WordCompleter
from unidecode import unidecode
from youtube_dl import YoutubeDL

from pharaoh.dl_job import Job

timestamp_pattern = re.compile(r'([0-9]{1,2}:)?[0-9]{1,2}:[0-9]{1,2}(\.[0-9]+)?')


def create_job(url: str, destination: str):
    info = YoutubeDL().extract_info(url, download=False, process=False)
    words = set()

    def add_words(s: str):
        current_word_start = 0
        current_word_len = 0
        ret = []

        for c in chain(s, ' '):
            if c.isalnum():
                current_word_len += 1
            else:
                if current_word_len:
                    current_word = s[current_word_start: current_word_len + current_word_start]
                    current_word = unidecode(current_word)
                    words.add(current_word)
                    ret.append(current_word)
                current_word_start += current_word_len + 1
                current_word_len = 0

        return ' '.join(ret)

    default_title = add_words(info.get('title', ''))
    add_words(info.get('alt_title', ''))
    add_words(info.get('creator', ''))
    add_words(info.get('track', ''))
    add_words(info.get('artist', ''))

    metadata = {
        k: info[k] for k in ('track', 'artist', 'title', 'album', 'year', 'genre') if k in info
    }

    # todo add completer by path

    completer = FuzzyWordCompleter(list(words))
    categories = info.get('categories', ())
    audio_only = confirm('audio only?', default='Music' in categories)

    format_ = 'bestaudio/best' if audio_only else 'best'
    if audio_only:
        default_title += '.mp3'
    else:
        default_title += '.mp4'

    if not destination:
        destination = prompt("enter destination path:\n> ", default=default_title, bottom_toolbar=getcwd(),
                             completer=completer)

    opts = {
        "format": format_,
        "quiet": True,
    }

    options = {
        "trim": "cut parts from start or end of video",
    }
    option_completer = WordCompleter(list(options.keys()))
    pp_input = []
    pp_output = list(chain.from_iterable(('-metadata', f'{k}={quote(v)}') for (k, v) in metadata.items()))
    while True:
        option = prompt("add options (? for help, empty for done):\n> ", completer=option_completer,
                        validator=Validator.from_callable(lambda s: s in options or s == ""))
        if option == "?":
            for k, v in options.items():
                print_formatted_text(HTML(f"<b>{k}</b>: {v}"))
            continue
        if option == "":
            break
        if option == "trim":
            start = prompt("enter timestamp for start of capture: ",
                           validator=Validator.from_callable(lambda s: s == "" or timestamp_pattern.fullmatch(s),
                                                             "timestamp must be of format [HH:]MM:SS"))
            if start:
                pp_input.extend(('-ss', start))
            end = prompt("enter timestamp for end of capture: ",
                         validator=Validator.from_callable(lambda s: s == "" or timestamp_pattern.fullmatch(s),
                                                           "timestamp must be of format [HH:]MM:SS"))
            if end:
                pp_input.extend(('-to', end))

    return Job(url, destination, destination, opts, pp_input, pp_output)
