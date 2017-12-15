# -*- coding: utf-8 -*-
"""Plotting with matplotlib

This module has all plotting related functions, classes, etc.
Tested with matplotlib 1.5.3 and 2.1.0
"""


import sys
import datetime
import matplotlib
matplotlib.use("Agg")  # This allows to use without DISPLAY, and prevents usage of DISPLAY
import numpy
import matplotlib.pyplot as plt
import matplotlib.ticker


config = {
    "default_image_size": (640, 640),  # pixels
    "simple_image_size": (640, 100),
    "window_title": "Bar diagram generated by metadatareader",
    "bar_color": "#6eb9db",
    "bar_edge_color": "#6eb9db",
    "text_in_bar_color": "#E3F6FF",
    "text_out_bar_color": "#137FB0",
    "font": {
        "family": "sans-serif",
        "sans-serif": "roboto",
        "size": 12,
    },
    "line_color": "#636b6f",

}


class MetadataPlotter(object):

    def __init__(self, **kwargs):
        """

        :param kwargs: Arguments used here:
            - 'size_multiplier' (int/float). Image size in inches. Default 5 inch.
            - 'image_size' (int). Image size in pixels. Default in config['default_image_size']
            - 'simple' (bool). Simple plot has different default image size in pixels.
            - 'transparent_bg' (bool). Default True, if one doesn't want transparent background, set this to False.
            - 'output_file' (string). Define name for resulting file. Either this or 'output_format' is needed for
              generating file.
            - 'output_format' (string). Define format for resulting file. Either this or 'output_file' is needed for
              generating file.
        """
        # Setup basic values:

        # -- Image size settings ---------------------------------------------------------------------------------------
        basic_size_inch = kwargs.get("size_multiplier", 5)
        if kwargs.get("image_size") is None:
            image_size = config["default_image_size"]
        else:
            image_size = kwargs.get("image_size")
        self.dpi = image_size[0] / basic_size_inch
        self.width = image_size[0] / self.dpi
        self.height = image_size[1] / self.dpi

        # -- Miscellaneous settings ------------------------------------------------------------------------------------
        self.transparency = kwargs.get("transparent_bg", True)
        self.number_format = kwargs.get("number_format", "not_seconds")

        if kwargs.get("output_file") is not None:
            self.filename = self._new_filename(filename=kwargs.get("output_file"))
        elif kwargs.get("output_format") is not None:
            self.filename = self._new_filename(file_format=kwargs.get("output_format"))
        else:
            self.filename = None

        # -- Font settings ---------------------------------------------------------------------------------------------
        self.prop = matplotlib.font_manager.FontProperties()
        if "font_file" in kwargs:
            self.prop.set_file(kwargs['font_file'])
        elif "font" in kwargs:  # [font, font_family, size]
            self.prop.set_name(kwargs['font'][0])
            if len(kwargs['font']) > 1:
                self.prop.set_family(kwargs['font'][1])
            if len(kwargs['font']) > 2:
                self.prop.set_size(kwargs['font'][2])
        if "font_size" in kwargs:
            self.prop.set_size(kwargs['font_size'])
        self.ticklabel_prop = self.prop.copy()
        self.ticklabel_prop.set_size(self.prop.get_size() - 2)

    def plot_barh(self, amounts, labels, **kwargs):
        """Plot horizontal bar chart.

        kwargs can include `title`, `filename`

        :param amounts: list of amounts, used as bar width.
        :param labels: list of labels associated with amounts.
        :param kwargs: Arguments used here:
            - 'font_file' (string). Set the filename of the fontfile to use. In this case, all other properties will be
              ignored.
            - 'font' (list). List of font, font_family and font size or None.
            - 'font_size' (int/string). Font size overrides size given in 'font'.
            - 'strict_n' (bool). Prevents scaling of the plot caused if there are less labels than given n.
            - 'image_size' (list/tuple). If not given, this plot has own default height value depending on amount of
              labels. len(labels) / 3 + 2 as inches
            - 'sort_method' (string). If string 'count', amounts are not seconds. Else assume that amounts are seconds.
            - 'video_length' (float). Calculate percent labels for bars.
            - 'time_label' (string). If string 'timestamp_and_percent' and video_length is given, print 'hh:mm:ss (xx%)'
              into bar. If string 'percent' and video_length is given, print 'xx%' into bar. Else print 'hh:mm:ss' into
              bar.
            - 'title' (string). If not None, print contained string into plot.
            - 'label_location' (string). If string 'left_side', print labels left side of plot. Otherwise print labels
              on bar if bar is wide enough, else right side of bar.
        :return: filename of plot in list or None
        """
        # if "filename" in kwargs:
        #     # This allows to use without DISPLAY
        #     import matplotlib
        #     matplotlib.use("Agg")
        if len(labels) == 0:
            # If no labels to print, return empty list.
            return []
        if kwargs.get("strict_n", False):
            while len(amounts) < kwargs.get("n_most_prominent_detections_per_type", len(amounts)):
                amounts.append(0)
                labels.append("")

        # Override default value:
        if kwargs.get("image_size") is None:
            self.height = len(labels) / 2.5 + 0.5

        fig, ax = plt.subplots(figsize=(self.width, self.height), dpi=self.dpi)
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.xaxis.set_ticks_position("bottom")
        ax.tick_params(axis='y',
                       which='both',
                       left='off',
                       right='off')
        ax.tick_params(axis='x',
                       direction='out')
        ax.set_yticklabels([])

        def delta_formatter(x, pos):
            """Custom formatter

            :param x: a tick value as seconds
            :param pos: a position (required even if unused)
            :return: corresponding tick label
            """
            if kwargs.get("sort_method", None) == "count":
                return int(x)

            if self.number_format == "seconds":
                format_string = u'{}'.format(int(x))
                return format_string
            d = datetime.timedelta(seconds=x)
            format_string = u'{}'.format(str(d))
            return format_string

        def time_label_formatter(x, pos):
            """Custom formatter time_label: ['timestamp', 'timestamp_and_percent', 'percent']

            :param x: a tick value as seconds
            :param pos: a position (required even if unused)
            :return: corresponding tick label
            """
            if kwargs.get("sort_method", None) == "count":
                return int(x)
            if kwargs.get('video_length') is not None:
                percent = 100.0*x/kwargs['video_length']
                if percent > 100.0:
                    n = 0
                    percent = 100.0
                elif percent > 10.0:
                    n = 0
                elif percent > 1.0:
                    n = 1
                elif percent > 0.1:
                    n = 2
                else:
                    n = 3
            else:
                percent = None

            if kwargs.get("time_label") is not None:
                if kwargs["time_label"] == "timestamp_and_percent" and percent is not None:
                    format_string = u'{}, {:.{n}f}%'.format(str(datetime.timedelta(seconds=x)), percent, n=n)
                elif kwargs["time_label"] == "percent" and percent is not None:
                    format_string = u'{:.{n}f}%'.format(percent, n=n)
                else:  # kwargs["time_label"] == "timestamp":
                    format_string = str(datetime.timedelta(seconds=x))
            elif kwargs.get('video_length') is not None:
                format_string = u'{:.{n}f}%'.format(percent, n=n)
            else:
                format_string = str(datetime.timedelta(seconds=x))
            return format_string

        ax.locator_params(axis='x', nbins=kwargs.get('max_ticks', 6), integer=True)

        formatter = matplotlib.ticker.FuncFormatter(delta_formatter)
        ax.xaxis.set_major_formatter(formatter)
        plt.xticks(fontproperties=self.ticklabel_prop)

        if "title" in kwargs:
            plt.title(kwargs["title"], fontproperties=self.prop)

        # amounts is the amount of rest of the labels
        y = numpy.arange(len(amounts)) + 0.5
        rects = ax.barh(y, amounts, edgecolor=config["bar_edge_color"], color=config["bar_color"],
                        align="center")

        if kwargs.get("label_location") == "left_side":
            plt.yticks(y, labels)
        bar_width = int(rects[0].get_width())
        for index, rect in enumerate(rects):
            width = rect.get_width()
            yloc = rect.get_y() + rect.get_height() * 0.5
            if kwargs.get("label_location") == "left_side":
                if width > bar_width * 0.5:
                    xloc = width * 0.98
                    align = "right"
                    color = config["text_in_bar_color"]
                else:
                    xloc = width + bar_width / 100.0
                    align = "left"
                    color = config["text_out_bar_color"]

                ax.text(xloc, yloc, time_label_formatter(int(width), None), horizontalalignment=align,
                        verticalalignment='center', color=color, weight='bold',
                        fontproperties=self.prop)
            else:  # on_bar

                # -- Label in bar, left alignment; Percent in bar, right alignment -------------------------------------
                if width > bar_width * 0.75:
                    xloc_label = bar_width * 0.02
                    xloc = width - bar_width * 0.02
                    label_color = config["text_in_bar_color"]
                    color = config["text_in_bar_color"]
                    label_align = "left"
                    ax.text(xloc, yloc, time_label_formatter(int(width), None), horizontalalignment="right",
                            verticalalignment='center', color=color, weight='bold',
                            fontproperties=self.prop)

                # -- Label in bar, left alignment; Percent outside bar, left alignment ---------------------------------
                elif width > bar_width * 0.5:
                    xloc_label = bar_width * 0.02
                    xloc = width + bar_width * 0.02
                    label_color = config["text_in_bar_color"]
                    color = config["text_out_bar_color"]
                    label_align = "left"
                    ax.text(xloc, yloc, time_label_formatter(int(width), None), horizontalalignment="left",
                            verticalalignment='center', color=color, weight='bold',
                            fontproperties=self.prop)

                # -- Label outside bar, left alignment; Percent inside bar, right alignment ----------------------------
                elif width > bar_width * 0.20 and kwargs.get("time_label") != "percent":
                    xloc_label = width + bar_width * 0.02
                    xloc = width - bar_width * 0.02
                    label_color = config["text_out_bar_color"]
                    color = config["text_in_bar_color"]
                    label_align = "left"
                    ax.text(xloc, yloc, time_label_formatter(int(width), None), horizontalalignment="right",
                            verticalalignment='center', color=color, weight='bold',
                            fontproperties=self.prop)

                # -- Label outside bar, left alignment; Percent inside bar, right alignment ----------------------------
                elif width > bar_width * 0.1 and kwargs.get("time_label") == "percent":
                    xloc_label = width + bar_width * 0.02
                    xloc = width - bar_width * 0.02
                    label_color = config["text_out_bar_color"]
                    color = config["text_in_bar_color"]
                    label_align = "left"
                    ax.text(xloc, yloc, time_label_formatter(int(width), None), horizontalalignment="right",
                            verticalalignment='center', color=color, weight='bold',
                            fontproperties=self.prop)

                # -- Label outside bar, left alignment; Percent not visible --------------------------------------------
                else:  # width <= bar_width * 0.5
                    xloc_label = width + bar_width * 0.02
                    label_color = config["text_out_bar_color"]
                    label_align = "left"
                ax.text(xloc_label, yloc, labels[index], horizontalalignment=label_align,
                        verticalalignment='center', color=label_color, weight='bold',
                        fontproperties=self.prop)

        fig.gca().invert_yaxis()
        fig.set_tight_layout(True)

        if self.filename is not None:
            try:
                plt.savefig(self.filename, transparent=self.transparency, dpi=self.dpi)
            except ValueError, msg:
                print >> sys.stderr, "Invalid output-file: {}".format(msg)
            else:
                plt.close(fig)
                return [self.filename]
            plt.close(fig)
        else:
            fig.canvas.set_window_title(config["window_title"])

            plt.show()

    @staticmethod
    def _new_filename(prefix="image_bar_", suffix="", file_format=None, filename=None):
        """Creates timestamp'd filename.

        Commented out: Prevents overwriting existing file by adding (i) to filename

        :param prefix: If file_format given, starts file name with this.
        :param suffix: if file_format given, ends file name with this.
        :param file_format: Use this as extension or type for the file.
        :param filename: Ignore this method if this is given, unless overwriting protection is restored.
        :return: name for the file.
        """
        if filename:
            pass
        elif file_format:
            timestamp = str(datetime.datetime.now()).replace(":", ".").replace(" ", "_")
            filename = "{}{}{}.{}".format(prefix, timestamp, suffix, file_format)
        else:
            return None

        # Prevent overwriting existing file by adding (i) to filename
        # name, ext = filename.rsplit(".", 1)
        # i = 1
        # while os.path.exists(filename):
        #     filename = "{}({}).{}".format(name, i, ext)
        #     i += 1
        return filename

    @staticmethod
    def new_filename(**kwargs):
        """
        :param kwargs: Arguments used here:
            - 'prefix' (string).
            - 'suffix' (string).
            - 'file_format' (string).
            - 'filename' (string).
        :return: name for the file
        """
        return MetadataPlotter._new_filename(**kwargs)

    def plot(self, summary, **kwargs):
        """Method to call when intending to plot something.


        :param summary: For bar_summary, list_summary -generator.
                        For sentiment graphs, list_sentiment -generator
        :param kwargs: Arguments used here:
            - 'bar_summary' (bool).
            - 'transcript_sentiment_graph' (bool).
            - 'face_sentiment_graph' (bool).
            - 'output_file' (string). Modifies the value for sentiment graphs.
        :return: File paths and names for successfully created images.
        :rtype: list
        """
        saved_files = list()

        if kwargs.get("bar_summary"):
            labels = []
            amounts = []
            for cells in summary.itervalues():
                for cell in cells:
                    labels.append(cell[0])
                    amounts.append(float(cell[1]))
                try:
                    saved_files.extend(self.plot_barh(amounts, labels, **kwargs))
                except TypeError:
                    pass
        return saved_files
