""" Various utilities."""
from __future__ import print_function, unicode_literals

import logging
import csv
import codecs
import cStringIO

if __name__ == "__main__":
    raise NotImplementedError("Not designated to be run, please use import statement.")


def dev_logger(name):
    """ Logger used in development environment.
    Format options:
    - %(pathname)s Full pathname of the source file where the logging call was issued(if available).
    - %(filename)s Filename portion of pathname.
    - %(module)s Module (name portion of filename).
    - %(funcName)s Name of function containing the logging call.
    - %(lineno)d Source line number where the logging call was issued (if available).
    """
    #FORMAT = '%(asctime)s, %(levelname)-8s [%(filename)s:%(module)s:%(funcName)s:%(lineno)d] %(message)s'

    #FORMAT = '%(asctime)s, %(levelname)-8s {%(name)s:%(funcName)s:%(lineno)d} %(message)s'
    FORMAT = '%(asctime)s, %(levelname)-8s {%(name)s:%(funcName)s:%(lineno)d} %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    l = logging.getLogger(name)
    return l


# For Python 2:
# https://docs.python.org/2.7/library/csv.html
class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        # self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow(
            self.encode_row(row))
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        # data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

    @staticmethod
    def encode_row(row):
        """Recursively encodes contents of list into 'utf-8'"""
        if type(row) is list:
            new_row = []
            for s in row:
                new_row.append(UnicodeWriter.encode_row(s))
        elif isinstance(row, int):
            new_row = UnicodeWriter.encode_row(str(row))
        elif isinstance(row, float):
            new_row = UnicodeWriter.encode_row("{:.3f}".format(row))
        else:
            new_row = row.encode("utf-8")
        return new_row
