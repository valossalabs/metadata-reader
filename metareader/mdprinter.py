# -*- coding: utf-8 -*-
"""Command-line output

Contains most functions, classes, etc. to handle the output of data.
"""
from __future__ import print_function, unicode_literals
from __future__ import absolute_import
from __future__ import division

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import OrderedDict
import sys
import os

# Available space for each label:
free_config = {
    'timestamp': 12,
    'second': 6,
    'detection ID': 13,
    'detection type': 24,
    'confidence': 11,
    'face_recognition_confidence': 28,
    'label': 30,    # (12, 24)
    'labels': 12,
    'Valossa concept ID': 19,
    'GKG concept ID': 15,
    'more information': 50,

    'name': 28,
    'screentime': 10,
    'screentime_s': 10,
    'of video length': 17,

    'speech valence': 15,
    'speech intensity': 17,
    'face valence': 15,

    '_default': 10,
}

name_config = {
    'name': 'Name',
    'screentime': 'Time (s)',
    'screentime_s': 'Time (s)',
    'confidence': 'Confidence',
    'face_recognition_confidence': 'Face recognition confidence',
    'label': 'Label',
    'of video length': 'Of video length',
    'visual.context': 'Visual context:',
    'human.face': 'Human face:',
    'audio.context': 'Audio context:',
    'audio.keyword.name.person': 'Audio keyword, person name',
    'audio.keyword.name.organization': 'Audio keyword, organization name',
    'audio.keyword.name.location': 'Audio keyword, location name',
    'audio.keyword.novelty_word': 'Audio keyword, novelty word',
    'audio.keyword.name.general': 'Audio keyword, name (general)',

    #u'speech valence': u'Speech valence',
}


class MetadataPrinter(object):
    __metaclass__ = ABCMeta

    def __init__(self, first_line, output=sys.stdout):
        if type(first_line) is OrderedDict:
            self.print_header(first_line)
            self.print_line(first_line)
        else:
            raise RuntimeError("Must be OrderedDict!")

    @abstractmethod
    def print_line(self, line_dict):
        pass

    @abstractmethod
    def print_header(self, line_dict):
        pass

    def finish(self):
        # package type printers does the printing here
        pass

    @staticmethod
    def unicode_printer(func, line):
        """This printer-function replaces characters which cause error with an
        question mark."""
        try:
            func(line)
        except UnicodeEncodeError:
            # Following error: unicode(x).decode('unicode-escape')
            # So user terminal doesn't support unicode
            for letter in line:
                try:
                    func(letter)
                except UnicodeEncodeError:
                    func('?')


def unicode_printer(func):
    def wrapper(line):
        try:
            func(line)
        except UnicodeEncodeError:
            # Following error: unicode(x).decode('unicode-escape')
            # So user terminal doesn't support unicode
            for letter in line:
                try:
                    func(letter)
                except UnicodeEncodeError:
                    func('?')
    return wrapper


class MetadataCSVPrinter(MetadataPrinter):

    def __init__(self, header_line, output=sys.stdout):
        if sys.version_info[0] < 3:
            from .lib.utils import UnicodeWriter
            self.writer = UnicodeWriter(output, lineterminator='\n')
        else:
            import csv
            self.writer = csv.writer(output, lineterminator='\n')
        if type(header_line) == dict and "summary" in header_line:
            self.print_line = self.print_summary

        super(MetadataCSVPrinter, self).__init__(header_line)

    def print_header(self, line_dict):
        try:
            self.writer.writerow(line_dict.keys())
        except UnicodeEncodeError:
            new_line_list = [cell.encode('utf-8') for cell in line_dict.keys()]
            self.writer.writerow(new_line_list)
            # Output is not anything sensible as used terminal doesn't support unicode !

    def print_line(self, line_dict, combine=None):
        try:
            self.writer.writerow(line_dict.values())
        except UnicodeEncodeError:
            new_line_list = [cell.encode('utf-8') for cell in line_dict.values()]
            self.writer.writerow(new_line_list)
            # Output is not anything sensible as used terminal doesn't support unicode !

    def print_summary(self, summary):
        for dtype in summary["summary"]:
            header_row = summary["summary"][dtype][0].keys()
            self.writer.writerow([dtype] + [''] * (len(header_row) - 1))
            self.writer.writerow(header_row)
            for item in summary["summary"][dtype]:
                if "screentime_s" in item:
                    item["screentime_s"] = "{:.2f}".format(float(item["screentime_s"]))
                self.writer.writerow(item.values())


class MetadataJSONPrinter(MetadataPrinter):
    pass


class MetadataFreePrinter(MetadataPrinter):

    def __init__(self, first_line, output=sys.stdout):
        self.write = self._writer(output)
        # self.spaces = {}

        # Summary check:
        if type(first_line) == dict and "summary" in first_line:
            self.print_row = self.print_line
            self.print_line = self.print_summary

        # Variables used in class
        self.combine = None
        self.on_one_line = None

        super(MetadataFreePrinter, self).__init__(first_line)

        try:
            rows, columns = os.popen('stty size', 'r').read().split()
        except ValueError:
            # Default values for os that doesn't support 'stty size'
            rows, columns = (40, 180)
        self.columns = int(columns)

    @staticmethod
    def _writer(output):
        def wrapper(line):
            # Print when formatted:
            try:
                print(line, file=output)
            except UnicodeEncodeError as e:
                # # Following error: unicode(x).decode('unicode-escape')
                # # So user terminal doesn't support unicode
                for letter in line:
                    try:
                        output.write(letter)
                    except UnicodeEncodeError:
                        output.write(u'?')
                output.write(u'\n')
        return wrapper

    def print_summary(self, summary):
        for dtype in summary["summary"]:
            self.write(u"Detection type: " + dtype)
            header_line = summary["summary"][dtype][0].keys()

            spaces = []
            for i, header in enumerate(header_line):
                spaces.append(free_config.get(header, free_config["_default"]))
                header_line[i] = name_config.get(header, header.capitalize())
            self.print_row(header_line)
            self.write('-'*(sum(spaces)+len(spaces)-1))
            for item in summary["summary"][dtype]:
                c = None
                if "confidence" in item:
                    c = "confidence"
                elif "face_recognition_confidence" in item:
                    c = "face_recognition_confidence"
                if c and item[c] != "-":
                    item[c] = "{:.1f}%".format(item[c]*100.0)
                self.print_row(item)
            self.write('\n')

    def print_header(self, line_dict):
        if type(line_dict) is not OrderedDict:
            raise RuntimeError("Must be ordered dict...")
        self._print_line(line_dict, is_header=True)

    def print_line(self, line_dict, combine=None):
        if type(line_dict) is not OrderedDict:
            raise RuntimeError("Must be ordered dict...")
        self._print_line(line_dict)

    def _print_line(self, line_dict, combine=None, is_header=False):
        line = ""

        for header, cell in line_dict.items():

            space = free_config[header] if header in free_config else len(header)+1
            text = header if is_header else cell

            if header == 'more information':
                line += "{}".format(text)
            elif line == "":
                line += "{:<{s}}".format(text, s=space)
            else:
                line += "{:>{s}}  ".format(text, s=space)

        self.write(line)


class MetadataSubtitlePrinter(MetadataPrinter):

    def __init__(self, first_line, output=sys.stdout):
        self.writer = output
        self.line_number = 1
        self.writer = unicode_printer(output.write)

        super(MetadataSubtitlePrinter, self).__init__(first_line)

    def print_header(self, first_line):
        """srt does not have headers."""
        return

    def print_line(self, line_dict, **kwargs):
        self.writer(str(self.line_number)+'\n')
        self.line_number += 1
        self.writer("{} --> {}\n".format(self.srt_timestamp(line_dict["start_time"]),
                                         self.srt_timestamp(line_dict["end_time"])))

        limit = len(line_dict["labels"]) // 2 if len(line_dict["labels"]) > 5 else None
        line = ", ".join(line_dict["labels"][:limit])
        if limit:
            line += "\n" + ", ".join(line_dict["labels"][limit:])

        self.writer(line + "\n\n")

    @staticmethod
    def srt_timestamp(seconds_par):
        """Transforms float into srt timestamp

        Format: hh:mm:ss,mmm
        """
        hours = int(seconds_par // 3600)
        minutes = int(seconds_par // 60) - 60 * hours
        sec = seconds_par - 3600 * hours - 60 * minutes
        seconds = int(sec)
        milliseconds = int(round(1000 * (sec - seconds)))

        # Float causes inaccuracy:
        if milliseconds == 1000:
            seconds += 1
            milliseconds = 0
        if seconds == 60:
            minutes += 1
            seconds = 0
        if minutes == 60:
            hours += 1
            minutes = 0

        if minutes >= 60 or seconds >= 60 or milliseconds >= 1000:
            e_msg = "srt_timestamp fail: {:02}:{:02}:{:02},{:03}".format(
                    hours, minutes, seconds, milliseconds)
            e_msg += "Input: {}".format(seconds_par)
            raise RuntimeError(e_msg)
        return "{:02}:{:02}:{:02},{:03}".format(
                hours, minutes, seconds, milliseconds)
