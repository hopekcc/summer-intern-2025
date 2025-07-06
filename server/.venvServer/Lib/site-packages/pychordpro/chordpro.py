import subprocess


class Song:
    def __init__(self, filename, notes):
        self.filename = filename
        self.notes = notes
        self.options = []

    def open(self, mode):
        self.file = open(self.filename, mode)

    def close(self):
        self.file.close()

    def read(self):
        return self.file.read()

    def readlines(self):
        return self.file.readlines()

    def write(self, content):
        with open(self.filename, 'w') as file:
            file.write(content)
            
    def append(self, content):
        with open(self.filename, 'a') as file:
            file.write(content)

    def cover(self, filename):
        self.options.append('--cover=%s' % filename)

    def csv(self):
        self.options.append('--csv')

    def decapo(self):
        self.options.append('--decapo')

    def diagrams(self, which):
        self.options.append('--diagrams=%s' % which)

    def encoding(self, enc):
        self.options.append('--encoding=%s' % enc)

    def filelist(self, filename):
        self.options.append('--filelist=%s' % filename)

    def lyrics_only(self):
        self.options.append('--lyrics-only')

    def meta(self, data: dict):
        for key, value in data.items():
            self.options.append('--meta=%s=%s' % (key, value))

    def no_csv(self):
        self.options.append('--no-csv')

    def no_toc(self):
        self.options.append('--no-toc')

    def output(self, value, generate=None):
        if generate:
            self.options.append('--generate=%s' % generate)

        else:
            self.options.append('--output=%s' % value)

    def start_page_number(self, n):
        self.options.append('--start-page-number=%d' % n)

    def toc(self):
        self.options.append('--toc')

    def transcode(self, notation):
        self.options.append('--transcode=%s' % notation)

    def transpose(self, value):
        self.options.append('--transpose=%d' % value)

    def chord_font(self, font):
        self.options.append('--chord-font=%s' % font)

    def chord_font(self, n):
        self.options.append('--chord-grid-size=%d' % n)

    def chord_grids(self):
        self.options.append('--chord-grids')

    def chords_grids_sorted(self):
        self.options.append('--chords-grids-sorted')

    def chord_size(self, n):
        self.options.append('--chord-size=%d' % n)

    def dump_chords(self):
        self.options.append('--dump-chords')

    def dump_chords_text(self):
        self.options.append('--dump-chords-text')

    def easy_chord_grids(self):
        self.options.append('--easy-chord-grids')

    def even_pages_number_left(self):
        self.options.append('--even-pages-number-left')

    def no_easy_chord_grids(self):
        self.options.append('--no-easy-chord-grids')

    def no_chord_grids(self):
        self.options.append('--no-chord-grids')

    def odd_pages_number_left(self):
        self.options.append('--odd-pages-number-left')

    def page_number_logical(self):
        self.options.append('--page-number-logical')

    def page_size(self, fmt):
        self.options.append('--page-size=%s' % fmt)

    def single_space(self):
        self.options.append('--single-space')

    def text_font(self, font):
        self.options.append('--text-font=%s' % font)

    def text_size(self, n):
        self.options.append('--text-size=%d' % n)

    def user_chord_grids(self):
        self.options.append('--user-chord-grids')

    def vertical_space(self, n):
        self.options.append('--vertical-space=%d' % n)

    def two_up(self):
        self.options.append('--2-up')

    def four_up(self):
        self.options.append('--4-up')

    def config(self, json):
        self.options.append('--config=%s' % json)

    def define(self, item):
        self.options.append('--define=%s' % item)

    def no_default_configs(self):
        self.options.append('--no-default-configs')

    def noconfig(self):
        self.options.append('--noconfig')

    def nolegacyconfig(self):
        self.options.append('--nolegacyconfig')

    def nosysconfig(self):
        self.options.append('--nosysconfig')

    def nouserconfig(self):
        self.options.append('--nouserconfig')

    def print_default_config(self):
        self.options.append('--print-default-config')

    def print_final_config(self):
        self.options.append('--print-final-config')

    def sysconfig(self, cfg):
        self.options.append('--sysconfig=%s' % cfg)

    def userconfig(self, cfg):
        self.options.append('--userconfig=%s' % cfg)

    def compile(self):
        command = ['chordpro %s' % self.filename, '--config notes:%s' % self.notes]
        command.extend(self.options)

        subprocess.call(' '.join(command), shell=True)
