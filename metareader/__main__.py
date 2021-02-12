#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
"""Command-line user interface
"""
from __future__ import print_function, unicode_literals
from __future__ import absolute_import
from __future__ import division

import sys
from site import USER_BASE
import os
import errno
from io import open
import argparse
import logging
logger = logging.getLogger(__name__)
# import argcomplete
try:
    # Python 3.0 and later
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    # Python 2
    from urllib2 import urlopen
    from urllib2 import HTTPError
import json

__dev__ = True


def restricted_float(float_arg):
    """float [0.0, 1.0]"""
    float_arg = float(float_arg)
    if float_arg < 0.0 or float_arg > 1.0:
        raise argparse.ArgumentTypeError("{} not in range [0.0, 1.0]".format(
            float_arg))
    return float_arg


def positive_int(int_arg):
    """int [1,2,3,4,...]"""
    int_arg = int(int_arg)
    if int_arg <= 0:
        raise argparse.ArgumentTypeError("{} is not positive integer".format(
            int_arg))
    return int_arg


def image_size(xy_str):
    from ast import literal_eval
    x, y = literal_eval(xy_str)
    return tuple((positive_int(x), positive_int(y)))


def load_json(file_url_or_path):
    """Returns contents of file located in argument from path or url."""

    try:
        # INPUT FILE AS URL
        json_file = urlopen(file_url_or_path)
        loaded_json = json.loads(json_file.read())
    except ValueError:  # invalid URL
        # INPUT FILE AS PATH
        with open(file_url_or_path, "r", encoding="utf-8") as json_file:
            loaded_json = json.loads(json_file.read())
    finally:
        try:
            json_file.close()
        except:
            # s there any error here I would like to catch really?
            pass
    return loaded_json


def input_metadata(file_url_or_path):
    try:
        metadata = load_json(file_url_or_path)
    except HTTPError as error_msg:
        raise argparse.ArgumentTypeError("Invalid url: {}\n{}".format(
            file_url_or_path, error_msg))
    except IOError as error_msg:
        raise argparse.ArgumentTypeError(
            "No such file found: {}\n{}".format(
                file_url_or_path, error_msg)
        )
    except ValueError as error_msg:
        raise argparse.ArgumentTypeError(
            "Input file not valid JSON-file: {}\n{}".format(
                file_url_or_path, error_msg)
        )
    return metadata


class ValidateExternalOntology(argparse.Action):
    # Source: https://stackoverflow.com/a/8624107
    def __call__(self, parser, args, values, option_string=None):
        choices = ('gkg',)
        ontology, concept_id = values
        if ontology not in choices:
            msg = "invalid choice: '{}' (currently supported external ontologies are: {})".format(
                    ontology, ", ".join(c for c in choices))
            raise argparse.ArgumentError(self, msg)
        setattr(args, self.dest, tuple((ontology, concept_id)))


class AddArguments:
    @staticmethod
    def list_detections(parser):
        parser.add_argument(
            "metadata_file", type=input_metadata,
            help="Valossa Core metadata file to examine"
        )
        parser.add_argument(
            "--output-file", default=None, metavar="FILE",
            help="Output results to FILE instead of stdout."
        )
        parser.add_argument(
            "-f", "--output-format",
            default="csv", choices=["csv", "free"],
            help="Choose one of the supported output formats."
        )
        parser.add_argument(
            "-n", "--n-most-prominent-detections-per-type", type=positive_int, metavar="N",
            help=("List only N most prominent detections from each detection type, "
                  "N given by user")
        )
        parser.add_argument(
            "-t", "--detection-types", default=None,
            metavar="TYPE", nargs="+",
            help="Space-separated list of detection types to read."
        )
        parser.add_argument(
            "-c", "--category", default=None,
            metavar="CATEGORY", nargs="+",
            help="Space separated list of categories."
        )
        parser.add_argument(
            "-l", "--detection-label", default=None, metavar="LABEL",
            help=("Detection label to read. "
                  "Example: dog")
        )
        parser.add_argument(
            "-p", "--detection-persons", "--similar-to", default=None, metavar="PERSON",
            help=("Comma-separated list of person names to read. Example: "
                  "\"George Clooney,*Willis\"")
        )
        parser.add_argument(
            "-i", "--detection-valossa-cid", default=None, metavar="ID",
            help="Valossa Concept ID to read. Example: \"sEl5Jb8H_WG7\""
        )
        parser.add_argument(
            "--detection-external-concept-id", nargs=2, action=ValidateExternalOntology, metavar=("ONTOLOGY", "ID"),
            help=("Name of external ontology followed by Concept ID to read. "
                  "Example: gkg \"/m/01j61q\"")
        )
        parser.add_argument(
            "--min-confidence", type=restricted_float, default=None, metavar="FLOAT",
            help=("Specify minimum confidence from 0.5 to 1. Valossa metadata does not have "
                  "entries below 0.5 confidence. Note that some detection types does not have confidence "
                  "field and in that case this argument is ignored.")
        )
        parser.add_argument(
            "--sort-by", default="detection_id",
            choices=["prominence", "detection_id"],
            help="Sort by selected method. Default: sort by detection ID"
        )
        parser.add_argument(
            "--extra-header", nargs="+",
            choices=["similar_to", "gender", "text"],
            help="Use this option to select extra headers for output."
        )

    @staticmethod
    def list_detections_by_second(parser):
        parser.add_argument(
            "metadata_file", type=input_metadata,
            help="Valossa Core metadata file to examine"
        )
        parser.add_argument(
            "--output-file", default=None, metavar="FILE",
            help="Output results to FILE instead of stdout."
        )
        parser.add_argument(
            "-f", "--output-format",
            default="csv", choices=["csv", "free", "srt"],
            help="Choose one of the supported output formats."
        )
        parser.add_argument(
            "-t", "--detection-types", default=None,
            metavar="TYPE", nargs="+",
            help="Space-separated list of detection types to read."
        )
        parser.add_argument(
            "-c", "--category", default=None,
            metavar="CATEGORY", nargs="+",
            help=("Space separated list of categories. Asterisk (*) "
                  "wildcards can be used. If used from shell, remember to use "
                  "quotation marks with asterisk. Example: human.face,\"*iab*\"")
        )
        parser.add_argument(
            "-l", "--detection-label", default=None, metavar="LABEL",  # TODO: Output occurrences too?
            help=("Detection label to read. "
                  "Example: dog")
        )
        parser.add_argument(
            "-p", "--detection-persons", "--similar-to", default=None, metavar="PERSON",
            help=("Comma-separated list of person names to read. Example: "
                  "\"George Clooney,*Willis\"")
        )
        parser.add_argument(
            "-i", "--detection-valossa-cid", default=None, metavar="ID",
            help="Valossa Concept ID to read. Example: \"sEl5Jb8H_WG7\""
        )
        parser.add_argument(
            "--detection-external-concept-id", nargs=2, action=ValidateExternalOntology, metavar=("ONTOLOGY", "ID"),
            help=("Name of external ontology followed by Concept ID to read. "
                  "Example: gkg \"/m/01j61q\"")
        )
        parser.add_argument(
            "--min-confidence", type=restricted_float, default=None, metavar="FLOAT",
            help=("Specify minimum confidence from 0.5 to 1. Valossa metadata does not have "
                  "entries below 0.5 confidence. Note that some detection types does not have confidence "
                  "field and in that case this argument is ignored.")
        )
        parser.add_argument(
            "--start-second", type=int, default=0,
            help=("Specifies the start-position of the examined time interval as seconds from "
                  "beginning (default: 0)")
        )
        parser.add_argument(
            "--length-seconds", type=int, default=None,
            help=("Specifies the length of the examined time interval as seconds. If left out, "
                  "then all remaining seconds after the --start-second position are examined")
        )
        parser.add_argument(
            "--end-second", type=int, default=None,
            help=("Specifies the end-position of the examined time interval as seconds from "
                  "beginning (default: until the end of video)")
        )
        parser.add_argument(
            "--short", action="store_true",
            help=("Shorter version. Each row has timestamp followed by labels detected at that time. Note that each "
                  "row has variable amount of labels so csv might not be as usable.")
        )
        parser.add_argument(
            "--sentiment", action="store_true",
            help=("List sentimental data in the core metadata file. Sentiment Analysis is not currently"
                  "part of the Core Capabilities, so be sure to enable it beforehand.")
        )
        parser.add_argument(
            "--extra-header", nargs="+",
            choices=["similar_to", "gender", "valence", "text"],
            help="Use this option to select extra headers for output."
        )

    @staticmethod
    def list_categories(parser):
        parser.add_argument(
            "metadata_file", type=input_metadata,
            help="Valossa Core metadata file to examine"
        )
        parser.add_argument(
            "--output-file", default=None, metavar="FILE",
            help="Output results to FILE instead of stdout."
        )
        parser.add_argument(
            "-f", "--output-format",
            default="csv", choices=["csv", "free"],
            help="Choose one of the supported output formats."
        )
        parser.add_argument(
            "-t", "--detection-types", default=None,
            metavar="TYPE", nargs="+",
            help="Space-separated list of detection types to read."
        )
        parser.add_argument(
            "-c", "--category", default=None,
            metavar="CATEGORY", nargs="+",
            help="Space separated list of categories."
        )
        parser.add_argument(
            "--min-confidence", type=restricted_float, default=None, metavar="FLOAT",
            help=("Specify minimum confidence from 0.5 to 1. Valossa metadata does not have "
                  "entries below 0.5 confidence. Note that some detection types does not have confidence "
                  "field and in that case this argument is ignored.")
        )
        parser.add_argument(
            "--start-second", type=int, default=0,
            help=("Specifies the start-position of the examined time interval as seconds from "
                  "beginning (default: 0)")
        )
        parser.add_argument(
            "--length-seconds", type=int, default=None,
            help=("Specifies the length of the examined time interval as seconds. If left out, "
                  "then all remaining seconds after the --start-second position are examined")
        )
        parser.add_argument(
            "--end-second", type=int, default=None,
            help=("Specifies the end-position of the examined time interval as seconds from "
                  "beginning (default: until the end of video)")
        )
        parser.add_argument(
            "-n", "--n-most-longest", type=positive_int, metavar="N",
            help="List only N longest categories "  # TODO: from each detection type
        )

    @staticmethod
    def list_occurrences(parser):
        parser.add_argument(
            "metadata_file", type=input_metadata,
            help="Valossa Core metadata file to examine"
        )
        parser.add_argument(
            "--output-file", default=None, metavar="FILE",
            help="Output results to FILE instead of stdout."
        )
        parser.add_argument(
            "-f", "--output-format",
            default="csv", choices=["csv", "free"],
            help="Choose one of the supported output formats."
        )
        parser.add_argument(
            "-t", "--detection-types", default=None,
            metavar="TYPES", nargs="+",
            help="Space-separated list of detection types to read."
        )
        parser.add_argument(
            "-c", "--category", default=None,
            metavar="CATEGORY", nargs="+",
            help="Space separated list of category tags."
        )
        parser.add_argument(
            "-l", "--detection-label", default=None, metavar="LABEL",  # TODO: Output occurrences too?
            help=("Detection label to read. "
                  "Example: dog")
        )
        parser.add_argument(
            "-p", "--detection-persons", "--similar-to", default=None, metavar="PERSON",
            help=("Comma-separated list of person names to read. Example: "
                  "\"George Clooney,*Willis\"")
        )
        parser.add_argument(
            "-i", "--detection-valossa-cid", default=None, metavar="ID",
            help="Valossa Concept ID to read. Example: \"sEl5Jb8H_WG7\""
        )
        parser.add_argument(
            "--detection-external-concept-id", nargs=2, action=ValidateExternalOntology, metavar=("ONTOLOGY", "ID"),
            help=("Name of external ontology followed by Concept ID to read. "
                  "Example: gkg \"/m/01j61q\"")
        )
        parser.add_argument(
            "--min-confidence", type=restricted_float, default=None, metavar="FLOAT",
            help=("Specify minimum confidence from 0.5 to 1. Valossa metadata does not have "
                  "entries below 0.5 confidence. Note that some detection types does not have confidence "
                  "field and in that case this argument is ignored.")
        )
        parser.add_argument(
            "--start-second", type=float, default=None,
            help=("Specifies the start-position of the examined time interval as seconds from "
                  "beginning (default: 0)")
        )
        parser.add_argument(
            "--length-seconds", type=float, default=None,
            help=("Specifies the length of the examined time interval as seconds. If left out, "
                  "then all remaining seconds after the --start-second position are examined")
        )
        parser.add_argument(
            "--end-second", type=float, default=None,
            help=("Specifies the end-position of the examined time interval as seconds from "
                  "beginning (default: until the end of video)")
        )
        parser.add_argument(
            "--sort-by", default=None,
            choices=["start_second", "valence", "duration"],
            help=("Sort by selected method. Items that do not have selected property will not be "
                  "listed at all. Default: sort by detection ID")
        )
        parser.add_argument(
            "--extra-header", nargs="+",
            choices=["valence", "similar_to", "text"],
            help="Use this option to select extra headers for output."
        )

    @staticmethod
    def metadata_info(parser):
        parser.add_argument(
            "metadata_file", type=input_metadata,
            help="Valossa Core metadata file to examine"
        )
        parser.add_argument(
            "--output-file", default=None, metavar="FILE",
            help="Output results to FILE instead of stdout."
        )
        parser.add_argument(
            "-f", "--output-format",
            default="free", choices=["csv", "free"],
            help="Choose one of the supported output formats."
        )

    @staticmethod
    def summary(parser):
        parser.add_argument(
            "metadata_file", type=input_metadata,
            help="Valossa Core metadata file to examine"
        )
        parser.add_argument(
            "--output-file", default=None, metavar="FILE",
            help="Output results to FILE instead of stdout."
        )
        parser.add_argument(
            "-f", "--output-format",
            default="csv", choices=["csv", "free"],
            help="Choose one of the supported output formats."
        )
        parser.add_argument(
            "-t", "--detection-type", default=None, metavar="TYPE",
            # choices={"visual.context", "audio.context", "human.face"},
            help="Detection type to read"
        )
        parser.add_argument(
            "-c", "--category", default=None,
            metavar="CATEGORY", nargs="+",
            help=("Category tag to read. All available category tags can be found at "
                  "apidocs: https://portal.valossa.com/portal/apidocs#detectioncategories.")
        )
        parser.add_argument(
            "-n", "--n-most-prominent-detections-per-type", type=positive_int, metavar="N",
            help=("List only N most prominent detections from each detection type, "
                  "N given by user")  # TODO: Word prominent might be bad here.
        )
        parser.add_argument(
            "--separate-face-identities", action="store_true",
            help=("Summary merges human.face identities with same similar_to -field. "
                  "Use this if you wish to prevent this merging.")
        )
        parser.add_argument(
            "--skip-unknown-faces", action="store_true",
            help="Remove the human.face detections missing similar_to -field from listing."
        )
        parser.add_argument(
            "--emotion", action="store_true",
            help="Show available emotion data."
        )

    @staticmethod
    def plot(parser):
        parser.add_argument(
            "metadata_file", type=input_metadata,
            help="Valossa Core metadata file to examine"
        )
        parser.add_argument(
            "--output-file", default=None, metavar="FILE",
            help="Output results to FILE instead of stdout."
        )
        parser.add_argument(
            "-f", "--output-format",
            default=None,
            help=("Choose one of the supported output formats. Supported formats depend "
                  "on your system configuration.")
        )
        parser.add_argument(
            "--min-confidence", type=restricted_float, default=None, metavar="FLOAT",
            help=("Specify minimum confidence from 0.5 to 1. Valossa metadata does not have "
                  "entries below 0.5 confidence. Note that some detection types does not have confidence "
                  "field and in that case this argument is ignored.")
        )

        required_arguments = parser.add_argument_group("required arguments")
        plot_type = required_arguments.add_mutually_exclusive_group(required=True)
        plot_type.add_argument(
            "--bar-summary", action="store_true",
            help=("Gives presentation of detection time of each label in chosen type "
                  "as bar chart.")
        )
        plot_type.add_argument(
            "--transcript-sentiment-graph", action="store_true",
            help="If you have enabled sentimental analysis, you can use this to output valence and intensity images."
        )
        plot_type.add_argument(
            "--face-sentiment-graph", action="store_true",
            help=("If you have enabled sentimental analysis, you can use this to output facial valence each in their "
                  "own image file.")
        )

        # Bar-plot, required arguments
        required_bar_plot = parser.add_argument_group("required arguments for bar-summary")
        required_bar_plot.add_argument(
            "-n", "--n-most-prominent-detections-per-type", type=positive_int, required="--bar-summary" in sys.argv,
            metavar="N",
            help=("List only N most prominent detections from chosen detection type, "
                  "N given by user")
        )
        required_bar_plot.add_argument(
            "-t", "--detection-type", default=None, metavar="TYPE",
            # choices={"visual.context", "audio.context", "human.face"},
            required="--bar-summary" in sys.argv,
            help="Detection type to read"
        )
        # Plot, optional arguments
        # plot_file = parser.add_mutually_exclusive_group()
        # plot_file.add_argument(
        #     "--output-file", default=None,
        #     help="Choose filename to save result to. Output format will be parsed from "
        #          "filename. If filename is already taken program will add (n) after the name."
        # )
        parser.add_argument(
            "--image-size", default=None, type=image_size,
            help="Resolution in pixels"
        )
        # Bar-plot, optional arguments
        parser.add_argument(
            "--separate-face-identities", action="store_true",
            help=("On default merges human.face identities with same similar_to -field. "
                  "Use this if you wish to prevent this merging.")
        )
        parser.add_argument(
            "--skip-unknown-faces", action="store_true",
            help="Remove the human.face detections missing similar_to -field from listing."
        )
        # Plot trans/face, optional arguments
        parser.add_argument(
            "--simple", action="store_true",
            help="Create 'trinary' image with three values being 'positive', 'neutral' and 'negative'"
        )

        parser.add_argument(
            "--show-title", action="store_true",
            help="Read video title from metadata and insert to image."
        )


def parse_user_arguments():
    """Parse given arguments and return parsed arguments

    :return: Dictionary containing the arguments
    """
    parser = argparse.ArgumentParser(
        prog="metareader",
        description="Helper tool to read Valossa Core metadata.",
        epilog=("A few example commands:\n"
                "metareader summary metadata_example.json -f free -n10\n"
                "metareader list-detections metadata_example.json -t\"visual.context\""),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="mode", metavar="MODE", help="Select one of the following modes.")
    subparsers.required = True

    # LIST-DETECTIONS
    # ---------------
    list_detections = subparsers.add_parser(
        "list-detections",
        help="List detections without looking into the by_second structure."
    )
    AddArguments.list_detections(list_detections)

    # LIST-DETECTIONS-BY-SECOND
    # -------------------------
    list_detections_by_second = subparsers.add_parser(
        "list-detections-by-second",
        help=("List detections for each second, by looking into the by_second "
              "structure (note: this obviously lists only time-bound detections, "
              "so for example IAB categories are NOT listed in this mode).")
    )
    AddArguments.list_detections_by_second(list_detections_by_second)

    # LIST-CATEGORIES
    # ---------------
    list_categories = subparsers.add_parser(
        "list-categories",
        help="List category tags."
    )
    AddArguments.list_categories(list_categories)

    # LIST-OCCURRENCES
    # ---------------
    list_occurrences = subparsers.add_parser(
        "list-occurrences",
        help="List all occurrences for one or multiple detections."
    )
    AddArguments.list_occurrences(list_occurrences)

    # SUMMARY
    # -------
    summary = subparsers.add_parser(
        "summary",
        help=("Create summary view of detections based on total occurrence time of the detections. "
              "Percent values are related to total length of the video.")
    )
    AddArguments.summary(summary)

    # PLOT
    # ----
    plot = subparsers.add_parser(
        "plot",
        help="Plot chosen metadata type into bar chart. Output will be saved to a file."
    )
    AddArguments.plot(plot)

    # METADATA-INFO
    # -------------
    metadata_info = subparsers.add_parser(
        "metadata-info",
        help="List information about metadatafile"
    )
    AddArguments.metadata_info(metadata_info)

    # argcomplete.autocomplete(parser)  # TODO: configure argcomplete for Valossa detection types etc.
    args = parser.parse_args()
    return vars(args)


def plot_handler(mdr, **kwargs):
    """Gets data, plots it and returns exit code.
    :param mdr: MetadataReader-object
    :param kwargs: arguments
    :return: exit code for main function
    :rtype int
    """
    from . import mdplotter
    if kwargs.get("show_title"):
        kwargs["video_title"] = mdr.video_title

    if kwargs.get("bar_summary"):
        list_generator = mdr.list_summary(addition_method="union", **kwargs)
        plotter = mdplotter.MetadataPlotter(**kwargs)
        plotter.plot(next(list_generator)["summary"])
        return 0
    if kwargs.get("transcript_sentiment_graph") or kwargs.get("face_sentiment_graph"):
        # Get data
        graph_data = mdr.list_sentiment(**kwargs)
        # Plot data
        plotter = mdplotter.MetadataPlotter(**kwargs)
        plotter.plot(graph_data, **kwargs)
        return 0
    return 1


def load_blacklist():
    """modify blaclist_file_locations for adding more possible locations and
    their checking order
    """
    blacklist_file_locations = [
        os.path.join(USER_BASE, "metareader", "blacklist.json"),
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "blacklist.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "blacklist.json"),
    ]
    for loc in blacklist_file_locations:
        if os.path.exists(loc):
            try:
                return loc, load_json(loc)
            except ValueError as e:
                # Case blacklist.json not formatted correctly, perhaps customer edited it?
                # Notify user:
                print("blacklist.json not formatted correctly. You can either remove\n"
                      "the blacklist.json, restore it by reinstalling the software or\n"
                      "fix the format problem with following information from the decoder:\n"
                      "%s" % e, file=sys.stderr)
                sys.exit(1)
                # raise e from None  # Works only for Python 3
            except IOError as e:  # Python 3: FileNotFoundError as e:
                # Case blacklist.json can't be found at default location (or some other
                # IO related error). Perhaps check alternative locations before moving on.
                # Removing the file is valid solution to disable blacklist.
                if __dev__:
                    raise
                pass
    return None, None


def main(**arguments):
    from . import mdreader
    from . import mdprinter

    bl_path, blacklist = load_blacklist()
    if blacklist is not None:
        logger.debug("Loaded blacklist file from %s" % bl_path)
    else:
        logger.debug("Failed loading blacklist file from %s" % bl_path)

    # Create instance of mdr = MetadataReader(json) with metadata-json as argument
    mdr = mdreader.MetadataReader(arguments.pop('metadata_file'), blacklist=blacklist)

    # Depending on arguments, call mdr.function(arguments).
    mode = arguments.pop('mode')
    if mode == 'list-detections':
        list_generator = mdr.list_detections(**arguments)
    elif mode == 'list-detections-by-second':

        # Make sure all three match, discard "length_seconds" if all three given:
        if arguments.get("start_second") and arguments.get("end_second"):
            arguments["length_seconds"] = arguments["end_second"] - arguments["start_second"]
        elif arguments.get("start_second") and arguments.get("length_seconds"):
            arguments["end_second"] = arguments["start_second"] + arguments["length_seconds"]
        elif arguments.get("length_seconds") and arguments.get("end_second"):
            arguments["start_second"] = arguments["end_second"] - arguments["length_seconds"]

        list_generator = mdr.list_detections_by_second(**arguments)
    elif mode == 'list-categories':
        list_generator = mdr.list_categories(**arguments)
    elif mode == 'list-occurrences':
        list_generator = mdr.list_occurrences(**arguments)
    elif mode == 'summary':
        list_generator = mdr.list_summary(**arguments)
    elif mode == 'plot':
        ex_code = plot_handler(mdr, **arguments)
        sys.exit(ex_code)
    elif mode == 'metadata-info':
        mdr.metadata_info()
        sys.exit(0)
    else:
        print("Error: Mode not supported" + mode, file=sys.stderr)
        sys.exit(1)
    try:
        first_row = next(list_generator)
    except mdreader.AppError as e:
        raise RuntimeError("Error: " + str(e))
    except StopIteration as e:
        # logger.debug("Nothing found.")
        return
    #
    # Set up printing method:
    print_mode = arguments.get('output_format', None)
    # Give the header row for printer:
    if arguments.get('output_file') is None:
        output_file = sys.stdout
    else:
        output_file = open(arguments.get('output_file'), "w", encoding="utf-8")

    if print_mode == 'csv':
        printer = mdprinter.MetadataCSVPrinter(first_row, output_file)
    elif print_mode == 'free':
        printer = mdprinter.MetadataFreePrinter(first_row, output_file)
    elif print_mode == 'srt':
        printer = mdprinter.MetadataSubtitlePrinter(first_row, output_file)
    else:
        if output_file is not sys.stdout:
            output_file.close()
        raise RuntimeError("Error: Print mode not supported", print_mode)

    if arguments.get("short", False) and mode == 'list-detections-by-second':
        for row in list_generator:
            printer.print_line(row, combine=1)
    else:
        for row in list_generator:
            printer.print_line(row)
    if output_file is not sys.stdout:
        output_file.close()


if __name__ == '__main__':
    cmd_line_args = parse_user_arguments()
    try:
        main(**cmd_line_args)
    except IOError as e:  # Python 2 doesn't have BrokenPipeError
        if e.errno != errno.EPIPE:
            # Not a broken pipe
            raise
        pass
