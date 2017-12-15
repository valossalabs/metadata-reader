#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Command-line user interface
"""

import sys
import argparse


def restricted_float(float_arg):
    """float [0.0, 1.0]"""
    float_arg = float(float_arg)
    if float_arg < 0.0 or float_arg > 1.0:
        raise argparse.ArgumentTypeError("{} not in range [0.0, 1.0]".format(float_arg))
    return float_arg


def positive_int(int_arg):
    """int [1,2,3,4,...]"""
    int_arg = int(int_arg)
    if int_arg <= 0:
        raise argparse.ArgumentTypeError("{} is not positive integer".format(int_arg))
    return int_arg


def image_size(xy_str):
    from ast import literal_eval
    x, y = literal_eval(xy_str)
    return tuple((positive_int(x), positive_int(y)))


def input_metadata(file_url_or_path):
    """Returns contents of file located in argument from path or url."""
    from urllib2 import urlopen
    from urllib2 import HTTPError
    import json
    try:
        # INPUT FILE AS URL
        jsonfile = urlopen(file_url_or_path)
        metadata = json.loads(jsonfile.read())
    except HTTPError, error_msg:
        raise argparse.ArgumentTypeError("Invalid url: {}\n{}".format(file_url_or_path,
                                                                      error_msg))
    except ValueError:  # invalid URL
        try:
            # INPUT FILE AS PATH
            with open(file_url_or_path, "r") as jsonfile:
                metadata = json.loads(jsonfile.read())
        except IOError, error_msg:
            raise argparse.ArgumentTypeError(
                "No such file found: {}\n{}".format(file_url_or_path, error_msg)
            )
        except ValueError, error_msg:
            raise argparse.ArgumentTypeError(
                "Input file not valid JSON-file: {}\n{}".format(file_url_or_path, error_msg)
            )
    finally:
        try:
            jsonfile.close()
        except:  # pylint: bare-except
            pass
    return metadata


def utf_type(string_arg):
    """Try to change to unicode encoding"""
    try:
        string_arg = unicode(string_arg, "utf-8")
    except TypeError:
        # string_arg already UTF-8
        pass
    return string_arg


class ValidateExternalOntology(argparse.Action):
    # Source: https://stackoverflow.com/a/8624107
    def __call__(self, parser, args, values, option_string=None):
        choices = ('gkg',)
        ontology, concept_id = values
        if ontology not in choices:
            msg = "invalid choice: '{}' (currently supported external ontologies are: {})".format(
                    ontology, ", ".join(c for c in choices))
            raise argparse.ArgumentError(self, msg)
        setattr(args, self.dest, tuple((ontology, utf_type(concept_id))))


def parse_user_arguments():
    """Parse given arguments and return parsed arguments

    :return: Dictionary containing the arguments
    """
    parser = argparse.ArgumentParser(
        prog="metareader",
        description="Helper tool to read Valossa Core metadata.",
        # Cheating whitespace-removing by using custom utf-8 whitespaces (U+2007):
        epilog=u"A few example commands:                                                     " \
               u"metareader summary metadata_example.json -f free -n10                     " \
               u"metareader list-detections metadata_example.json -t\"*name.location\"     ",
    )

    # Common arguments for subparser-modes:
    main_parent_parser = argparse.ArgumentParser(add_help=False)
    secondary_parent_parser = argparse.ArgumentParser(add_help=False)
    confidence_parent_parser = argparse.ArgumentParser(add_help=False)

    main_parent_parser.add_argument("metadata_file", type=input_metadata,
                                    help="Valossa Core metadata file to examine")
    secondary_parent_parser.add_argument(
        "-t", "--detection-types", type=utf_type,  default=None, metavar="TYPES",
        help="Comma-separated list of detection types to read. Asterisk (*) wildcards "
             "can be used. If used from shell, remember to use quotation marks with asterisk. "
             "Example: human.face,\"*iab*\""
    )
    secondary_parent_parser.add_argument(
        "-l", "--detection-label", type=utf_type, default=None, metavar="LABEL",
        help="Detection label to read. "
             "Example: dog"
    )
    secondary_parent_parser.add_argument(
        "-p", "--detection-persons", type=utf_type, default=None, metavar="PERSON",
        help="Comma-separated list of person names to read. Example: \"George Clooney,*Willis\""
    )
    secondary_parent_parser.add_argument(
        "-i", "--detection-valossa-cid", type=utf_type, default=None, metavar="ID",
        help="Comma-separated list of Valossa Concept IDs to read. Example: \"sEl5Jb8H_WG7\""
    )
    secondary_parent_parser.add_argument(
        "--detection-external-concept-id", nargs=2, action=ValidateExternalOntology, metavar=("ONTOLOGY", "ID"),
        help="Name of external ontology followed by comma-separated list of Concept IDs to read. "
             "Example: gkg \"/m/01j61q\""
    )
    confidence_parent_parser.add_argument(
        "--min-confidence", type=restricted_float, default=None, metavar="FLOAT",
        help="Specify minimum confidence from 0.5 to 1. Valossa metadata does not have "
             "entries below 0.5 confidence. Note that some detection types does not have confidence "
             "field and in that case this argument is ignored."
    )

    subparsers = parser.add_subparsers(dest="mode", metavar="MODE", help="Select one of the following modes.")

    # LIST-DETECTIONS
    # ---------------
    parser_detection = subparsers.add_parser(
        "list-detections", parents=[main_parent_parser, secondary_parent_parser, confidence_parent_parser],
        help="List detections without looking into the by_second structure."
    )
    # List-detections, optional arguments
    parser_detection.add_argument(
        "-f", "--output-format", choices=["free", "csv"], default="csv",  # TODO: json
        help="Choose one of the supported output formats."
    )
    parser_detection.add_argument(
        "-n", "--n-most-prominent-detections-per-type", type=positive_int, metavar="N",
        help="List only N most prominent detections from each detection type, "
             "N given by user"
    )

    # LIST-DETECTIONS-BY-SECOND
    # -------------------------
    parser_by_second = subparsers.add_parser(
        "list-detections-by-second",
        parents=[main_parent_parser, secondary_parent_parser, confidence_parent_parser],
        help="List detections for each second, by looking into the by_second "
             "structure (note: this obviously lists only time-bound detections, "
             "so for example IAB categories are NOT listed in this mode)"
    )
    # List-detections-by-second, optional arguments
    parser_by_second.add_argument(
        "-f", "--output-format", choices=["free", "csv", "srt"], default="csv",  # TODO: json
        help="Choose one of the supported output formats."
    )
    parser_by_second.add_argument(
        "--start-second", type=int, default=0,
        help="Specifies the start-position of the examined time interval as seconds from "
             "beginning (default: 0)"
    )
    parser_by_second.add_argument(
        "--length-seconds", type=int, default=None,
        help="Specifies the length of the examined time interval as seconds. If left out, "
             "then all remaining seconds after the --start-second position are examined"
    )
    parser_by_second.add_argument(
        "--end-second", type=int, default=None,
        help="Specifies the end-position of the examined time interval as seconds from "
             "beginning (default: until the end of video)"
    )

    # METADATA-INFO
    # -------------
    parser_metainfo = subparsers.add_parser("metadata-info", parents=[main_parent_parser],
                                            help="List information about metadatafile")
    # Metadata-info, optional arguments.
    parser_metainfo.add_argument("-f", "--output-format", choices=["free"], default="free",
                                 help="Choose one of the supported output formats.")

    # SUMMARY
    # -------
    parser_summary = subparsers.add_parser(
        "summary", parents=[main_parent_parser, confidence_parent_parser],
        help="Create summary view of detections based on total occurrence time of the detections. "
             "Percent values are related to total length of the video."
    )
    # Summary, optional arguments
    parser_summary.add_argument("-f", "--output-format", choices=["free", "csv"], default="csv",
                                help="Choose one of the supported output formats.")

    parser_summary.add_argument(
        "-t", "--detection-type", type=utf_type, default=None, metavar="TYPE",
        help="Detection type to read"
    )
    parser_summary.add_argument(
        "-n", "--n-most-prominent-detections-per-type", type=positive_int, metavar="N",
        help="List only N most prominent detections from each detection type, "
             "N given by user"
    )
    parser_summary.add_argument("--separate-face-identities", action="store_true",
                                help="Summary merges human.face identities with same similar_to -field. "
                                     "Use this if you wish to prevent this merging.")
    parser_summary.add_argument("--skip-unknown-faces", action="store_true",
                                help="Remove the human.face detections missing similar_to -field from listing.")

    # PLOT
    # ----
    parser_plot = subparsers.add_parser(
        "plot", parents=[main_parent_parser, confidence_parent_parser],
        help="Plot chosen metadata type into bar chart. Output will be saved to a file."
    )
    # Plot, required arguments
    required_plot = parser_plot.add_argument_group("required arguments")
    plot_type = required_plot.add_mutually_exclusive_group()
    plot_type.add_argument(
        "--bar-summary", action="store_true", default=True,
        help="Gives presentation of detection time of each label in chosen type "
             "as bar chart."
    )
    # Bar-plot, required arguments
    required_bar_plot = parser_plot.add_argument_group("required arguments for bar-summary")
    required_bar_plot.add_argument(
        "-n", "--n-most-prominent-detections-per-type", type=positive_int, required=True,
        metavar="N",
        help="List only N most prominent detections from chosen detection type, "
             "N given by user"
    )
    required_bar_plot.add_argument(
        "-t", "--detection-type", type=utf_type, default=None, metavar="TYPE",
        required=True,
        help="Detection type to read"
    )
    # Plot, optional arguments
    plot_file = parser_plot.add_mutually_exclusive_group()
    plot_file.add_argument(
        "-f", "--output-format", default=None,
        help="Choose one of the supported output formats. Supported formats depend "
             "on your system configuration."
    )
    plot_file.add_argument(
        "--output-file", default=None,
        help="Choose filename to save result to. Output format will be parsed from "
             "filename. If filename is already taken program will add (n) after the name."
    )
    parser_plot.add_argument("--image-size", type=image_size, help="Resolution in pixels")  # TODO: help
    # Bar-plot, optional arguments
    parser_plot.add_argument("--separate-face-identities", action="store_true",
                             help="On default merges human.face identities with same similar_to -field. "
                                  "Use this if you wish to prevent this merging.")
    parser_plot.add_argument("--skip-unknown-faces", action="store_true",
                             help="Remove the human.face detections missing similar_to -field from listing.")

    args = parser.parse_args()
    return vars(args)


def plot_handler(mdr, **kwargs):
    """Gets data, plots it and returns exit code.
    :param mdr: MetadataReader-object
    :param kwargs: arguments
    :return: exit code for main function
    :rtype int
    """
    import mdplotter
    if kwargs.get("bar_summary"):
        list_generator = mdr.list_summary(addition_method="union", **kwargs)
        plotter = mdplotter.MetadataPlotter(**kwargs)
        plotter.plot(next(list_generator)["summary"], **kwargs)
        return 0
    return 1


def main(**arguments):
    import mdreader
    import mdprinter
    import sys

    # Create instance of mdr = MetadataReader(json) with metadata-json as argument
    mdr = mdreader.MetadataReader(arguments.pop('metadata_file'))

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
    elif mode == 'summary':
        list_generator = mdr.list_summary(**arguments)
    elif mode == 'plot':
        ex_code = plot_handler(mdr, **arguments)
        sys.exit(ex_code)
    elif mode == 'metadata-info':
        mdr.metadata_info()
        sys.exit(0)
    else:
        print >> sys.stderr, "Error: Mode not supported" + mode
        sys.exit(1)
    try:
        first_row = next(list_generator)
    except mdreader.AppError, e:
        print >> sys.stderr, "Error: " + str(e)
        sys.exit(1)
    except StopIteration:
        print >> sys.stderr, "Error: No items found to iterate over. Check that the parameters have been written " \
                             "correctly."
        sys.exit(1)

    #
    # Set up printing method:
    print_mode = arguments.get('output_format', None)
    # Give the header row for printer:
    if print_mode == 'csv':
        printer = mdprinter.MetadataCSVPrinter(first_row)
    elif print_mode == 'free':
        printer = mdprinter.MetadataFreePrinter(first_row)
    elif print_mode == 'srt':
        printer = mdprinter.MetadataSubtitlePrinter(first_row)
    else:
        print "Error: Print mode not supported", print_mode
        sys.exit(1)

    for row in list_generator:
        printer.print_line(row)


if __name__ == '__main__':

    # Parse given arguments and save them to `arguments`
    arguments = parse_user_arguments()

    main(**arguments)