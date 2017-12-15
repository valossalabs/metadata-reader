# -*- coding: utf-8 -*-
"""Command-line output

Contains most functions, classes, etc. to handle the output of data.
"""

from abc import ABCMeta, abstractmethod, abstractproperty
import sys
import os


# Available space for each label:
free_config = {
    'timestamp': 12,
    'second': 6,
    'detection ID': 13,
    'detection type': 24,
    'confidence': 11,
    'label': 30,    # (12, 24)
    'labels': 12,
    'Valossa concept ID': 19,
    'GKG concept ID': 15,
    'more information': 50,

    'name': 24,
    'screentime': 10,
    'of video length': 17,

}

name_config = {
    u'name': u'Name',
    u'screentime': u'Time (s)',
    u'confidence': u'Confidence',
    u'label': u'Label',
    u'of video length': u'Of video length',
    u'visual.context': u'Visual context:',
    u'human.face': u'Human face:',
    u'audio.context': u'Audio context:',
    u'audio.keyword.name.person': u'Audio keyword, person name',
    u'audio.keyword.name.organization': u'Audio keyword, organization name',
    u'audio.keyword.name.location': u'Audio keyword, location name',
    u'audio.keyword.novelty_word': u'Audio keyword, novelty word',
    u'audio.keyword.name.general': u'Audio keyword, name (general)',
}


class MetadataPrinter(object):
    __metaclass__ = ABCMeta

    def __init__(self, header_line, output=sys.stdout):
        self.print_line(header_line)

    @abstractmethod
    def print_line(self, line_list):
        pass

    def finish(self):
        # package type printers does the printing here
        pass

    @staticmethod
    def unicode_printer(func, line):
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
        import csv
        self.writer = csv.writer(output, lineterminator='\n')
        if type(header_line) == dict and "summary" in header_line:
            self.print_line = self.print_summary

        super(MetadataCSVPrinter, self).__init__(header_line)

    def print_line(self, line_list, combine=None):
        try:
            self.writer.writerow(line_list)
        except UnicodeEncodeError:
            new_line_list = list()
            for cell in line_list:
                new_line_list.append(cell.encode('utf-8'))
            self.writer.writerow(new_line_list)
            # Output is not anything sensible as used terminal doesn't support unicode !

    def print_summary(self, summary):
        for dtype in summary["summary"]:
            self.writer.writerow([dtype])
            if dtype == "human.face":
                row = ['name', 'screentime', 'confidence', 'of video length']
            else:
                row = ['label', 'screentime', 'of video length']
            self.writer.writerow(row)
            for item in summary["summary"][dtype]:
                self.writer.writerow(item)


class MetadataFreePrinter(MetadataPrinter):

    def __init__(self, header_line, output=sys.stdout):
        self.write = self._writer(output)
        self.spaces = list()

        # Summary check:
        if type(header_line) == dict and "summary" in header_line:
            self.print_row = self.print_line
            self.print_line = self.print_summary

        # Check spacing settings from free_config
        else:
            self.header_line = header_line[:]  # Copy of header
            for header in header_line:
                try:
                    self.spaces.append(free_config[header])
                except KeyError:
                    # Should account for "header (1)" type for example
                    self.spaces.append(next(v for k, v in free_config.iteritems() if k in header)+4)

        # Variables used in class
        self.combine = None
        self.on_one_line = None

        super(MetadataFreePrinter, self).__init__(header_line)

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
                print >> output, line
            except UnicodeEncodeError, e:
                # Following error: unicode(x).decode('unicode-escape')
                # So user terminal doesn't support unicode
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
            if dtype == "human.face":
                # Saving Header line allows writer to format based on header name.
                self.header_line = row = ['name', 'screentime', 'confidence', 'of video length']
            else:
                self.header_line = row = ['label', 'screentime', 'of video length']
            self.spaces = list()
            for i, header in enumerate(row):
                self.spaces.append(free_config[header])
                row[i] = name_config[header]
            self.print_row(row)
            self.write('-'*(sum(self.spaces)+len(self.spaces)-1))
            for item in summary["summary"][dtype]:
                item[-1] = "{:.2f}%".format(item[-1]*100.0)
                self.print_row(item)
            self.write('\n')

    def print_line(self, line_list, combine=None):

        line = u""
        for index, cell in enumerate(line_list[:-1]):
            space = self.spaces[index]
            if line == u"":
                line += u"{:<{s}}".format(cell, s=space)
            else:
                line += u"{:>{s}}  ".format(cell, s=space)

        # The last line starts at left if it's 'more information' field
        if self.header_line[index+1] == u'more information':
            line += u"{}".format(line_list[-1])
        else:
            line += u"{:>{s}}".format(line_list[-1], s=self.spaces[index+1])

        self.write(line)

    def print_line_with_strict_tabs(self, line_list, combine=None):
        """Prints line in free form to sys.stdout

        :param line_list: List of cells to print
        :param combine: If multiple cells of single header type
        """

        # Do formatting !!!
        line = ""
        if combine is not None:
            if self.combine is None:
                self.on_one_line = 0
                while self.columns - 1 > sum(self.spaces):
                    print "{} > {} = {}".format(self.columns - 1, sum(self.spaces), self.columns - 1 > sum(self.spaces))
                    self.on_one_line += 1
                    self.spaces.append(self.spaces[combine])
                self.spaces.pop()

                self.combine = True
            extra_newline_index = False
        else:
            # Other way of trying to handle too small console window:
            self.spaces[-1] = max(self.spaces[-1], 15)
            # One way of trying to handle too small console window:
            if self.spaces[-1] < 10:
                i = -1
                extra_newline_index = len(self.spaces) - 1
                temp = self.spaces[i]
                while temp < 10:
                    i -= 1
                    extra_newline_index -= 1
                    temp += self.spaces[i]
                    self.spaces[-1] = self.columns - sum(self.spaces[extra_newline_index:])
            else:
                extra_newline_index = False

        newline_flag = None

        while newline_flag is not False:
            if newline_flag:
                line += "\n"
            newline_flag = False
            for index, cell in enumerate(line_list):
                # One iteration generates one line:
                try:
                    cell = str(cell).decode("utf-8")
                except UnicodeEncodeError:
                    # Already unicode.
                    pass

                if combine is not None and combine <= index:

                    while index < len(line_list) - 1 and line_list[index] == "":
                        index += 1
                    total_columns = 0
                    for cell in line_list[index:]:

                        f = len(line_list[index]) / self.spaces[combine] + 1
                        if f > self.on_one_line - total_columns:
                            if False in [x == "" for x in line_list]:
                                # line += "\n"
                                newline_flag = True
                            break
                        line += u"{:<{f}}".format(line_list[index], f=self.spaces[combine] * f)
                        line_list[index] = ""
                        index += 1
                        total_columns += f
                    break
                elif len(cell) > self.spaces[index]:
                    newline_flag = True
                    if " " in cell:
                        splitter = " "
                    elif "," in cell:
                        splitter = ","
                    elif "." in cell:
                        splitter = "."
                    else:
                        print "Error: ", cell
                        print >> sys.stderr, "No space nor dot in"
                        sys.exit(1)

                    for i in range(len(cell.split(splitter))):

                        splitlist = cell.rsplit(splitter, i)

                        if len(splitlist[0]) <= self.spaces[index] - 1:
                            if line == "" or (line.endswith("\n") and index == 0) \
                                    or self.header_line[index] == "more information":
                                line += u"{:<{s}}".format(splitlist[0], s=self.spaces[index])
                            else:
                                line += u"{:>{s}}  ".format(splitlist[0], s=self.spaces[index])
                            line_list[index] = " ".join(splitlist[1:])
                            break
                    else:
                        if extra_newline_index is not False and index == extra_newline_index:
                            line += "\n"
                        if not (cell == "" and index == len(line_list) - 1):

                            # If cell in question is both empty and last one, skip following
                            if line == "" or (line.endswith("\n") and index == 0) \
                                    or self.header_line[index] == "more information":
                                line += u"{:<{s}}".format(cell[:self.spaces[index]], s=self.spaces[index])
                            else:
                                line += u"{:>{s}}  ".format(cell[:self.spaces[index]], s=self.spaces[index])
                            line_list[index] = cell[self.spaces[index]:]
                else:
                    if extra_newline_index is not False and index == extra_newline_index:
                        line += "\n"
                    if not (cell == "" and index == len(line_list) - 1):
                        # If cell in question is both empty and last one, skip following
                        if line == "" or (line.endswith("\n") and index == 0) \
                                or self.header_line[index] == "more information":
                            line += u"{:<{s}}".format(cell[:self.spaces[index]], s=self.spaces[index])
                        else:
                            line += u"{:>{s}}  ".format(cell[:self.spaces[index]], s=self.spaces[index])
                        line_list[index] = cell[self.spaces[index]:]

        # Print when formatted:
        self.write(line)


class MetadataSubtitlePrinter(MetadataPrinter):

    def __init__(self, header_line, output=sys.stdout):
        self.writer = output
        self.line_number = 1
        self.writer = unicode_printer(output.write)

        super(MetadataSubtitlePrinter, self).__init__(header_line)

    def print_line(self, line_list, **kwargs):
        self.writer(str(self.line_number)+'\n')
        self.line_number += 1
        self.writer(u"{} --> {}\n".format(self.srt_timestamp(line_list[0]), self.srt_timestamp(line_list[1])))

        limit = len(line_list[2:])

        if limit > 5:
            limit = len(line_list[2:]) / 2 - 1
        else:
            limit = len(line_list[2:])
        i = 0
        line = line_list[2]
        for label in line_list[3:]:
            if i == limit:
                line += u",\n{}".format(label)
            else:
                line += u", {}".format(label)
            i += 1

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
            print >> sys.stderr, "srt_timestamp fail: {:02}:{:02}:{:02},{:03}".format(hours, minutes, seconds,
                                                                                      milliseconds)
            print >> sys.stderr, "Input: {}".format(seconds_par)
            sys.exit(1)
        return "{:02}:{:02}:{:02},{:03}".format(hours, minutes, seconds, milliseconds)

