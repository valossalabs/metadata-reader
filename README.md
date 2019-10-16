# Valossa Metadata Reader
Helper tool for reading Valossa Core video metadata. You can also look at the
code to get insights for writing your own code for reading Valossa Core video
metadata in your application.

This tool allows you to get familiar with the metadata contents and gives you
examples of getting the contents visible. If you are a developer, this tool and
the source code of it can be useful as a reference. This tool is currently
on beta and we would like to encourage the users to send feedback on usage via
the [github issues](../../issues) page.

If you are not familiar with Valossa Labs, please visit our website at
[**valossa**.com](https://valossa.com/) for more information.

# Table of contents

* [Getting started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [First use](#first-use)
* [Features](#features)
* [Documentation](../../wiki/Documentation)
* [Use-cases](../../wiki/Use-cases)


## Getting started

These instructions walk you through from installation to first use case.


### Prerequisites

The program has been written with [Python](https://www.python.org/) so to
make sure the Python is installed, you can run

```
python --version
```

to see the version installed on your machine. The program supports both Python 2 and 3.

If you wish to use plotting options, you need to have the `matplotlib` package installed.
The program has been tested with versions 1.5.3 and 2.1.0. The version installed on
your machine can be checked in the following way:

```
python
...
>>> import matplotlib
>>> matplotlib.__version__
'2.1.0'
```

If you don't have the `matplotlib` package installed yet, the following message should appear.

```
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: No module named matplotlib
```

In this case you should install the package, for instructions see the
[official website](https://matplotlib.org/users/installing.html).


### Installation

The package isn't available on the pip yet, so the recommended way to install
would be the following.

1. Clone or download the repository.
2. Browse to the directory with command line utility and run `pip install --user .`
   for local user installation or `sudo pip install .` for global installation.
   Note that there is dot in the command.

You can uninstall the program with `pip uninstall metareader`.


### First use

You can now start the program with `python -m metareader`. Note that we use `metareader` as an
`alias metareader="python -m metareader"` across the documentation and use-cases.

Test if the program has been installed properly into your machine. The following command
lists the available arguments.

<details>
<summary><sub>Click to see expected output</sub>

```
metareader --help
```
</summary>

Expected output:

```
usage: metareader [-h] MODE ...

Helper tool to read Valossa Core metadata.

positional arguments:
  MODE                  Select one of the following modes.
    list-detections     List detections without looking into the by_second
                        structure.
    list-detections-by-second
                        List detections for each second, by looking into the
                        by_second structure (note: this obviously lists only
                        time-bound detections, so for example IAB categories
                        are NOT listed in this mode).
    list-categories     List category tags.
    list-occurrences    List all occurrences for one or multiple detections.
    summary             Create summary view of detections based on total
                        occurrence time of the detections. Percent values are
                        related to total length of the video.
    plot                Plot chosen metadata type into bar chart. Output will
                        be saved to a file.
    metadata-info       List information about metadatafile

optional arguments:
  -h, --help            show this help message and exit

A few example commands:
metareader summary metadata_example.json -f free -n10
metareader list-detections metadata_example.json -t"visual.context"
```
</details>


## Features

The information about specific features the program has with
examples on writing the commands is available in
[the documentation wiki](../../wiki/Documentation).

Most optional arguments can be combined with each other to create a
more specific listing. Some examples of this can be found in
[the use-cases wiki](../../wiki/Use-cases).

The basic way to use the program is `metareader MODE [optional arguments] -- core_metadata.json`.

#### The modes, select one
* [`list-detections`](../../wiki/Documentation#list-detections)
* [`list-detections-by-second`](../../wiki/Documentation#list-detections-by-second)
* [`list-categories`](../../wiki/Documentation#list-categories)
* [`list-occurrences`](../../wiki/Documentation#list-occurrences)
* [`summary`](../../wiki/Documentation#summary)
* [`plot`](../../wiki/Documentation#plot)
* [`metadata-info`](../../wiki/Documentation#metadata-info)

#### The optional arguments
* List detections:
    * `--output-file FILE`
    * `--output-format FORMAT` (or `-f`)
    * `--detection-types TYPE [TYPE2 ...]` (or `-t`)
    * `--detection-label LABEL` (or `-l`)
    * `--detection-persons PERSON[,...]` (or `-p`)
    * `--detection-valossa-cid ID` (or `-i`)
    * `--detection-external-concept-id ONTOLOGY ID`
    * `--min-confidence FLOAT` (FLOAT=[0..1])
    * `--sort-by METHOD`
    * `--extra-header HEADER [HEADER2 ...]`
    * `--n-most-prominent-detections-per-type N` (or (`-n`)
* List detections by second:
    * `--output-file FILE`
    * `--output-format FORMAT` (or `-f`)
    * `--detection-types TYPE [TYPE2 ...]` (or `-t`)
    * `--category CATEGORY [CATEGORY2 ...]` (or `-c`)
    * `--detection-label LABEL` (or `-l`)
    * `--detection-persons PERSON[,...]` (or `-p`)
    * `--detection-valossa-cid ID` (or `-i`)
    * `--detection-external-concept-id ONTOLOGY ID`
    * `--min-confidence FLOAT` (FLOAT=[0..1])
    * `--start-second N`
    * `--length-seconds N`
    * `--end-second N`
    * `--short`
    * `--sentiment`
    * `--extra-header HEADER [HEADER2 ...]`
* List categories:
    * `--output-file FILE`
    * `--output-format FORMAT` (or `-f`)
    * `--detection-types TYPE [TYPE2 ...]` (or `-t`)
    * `--category CATEGORY [CATEGORY2 ...]` (or `-c`)
    * `--min-confidence FLOAT` (FLOAT=[0..1])
    * `--start-second N`
    * `--length-seconds N`
    * `--end-second N`
    * `--n-most-longest N` or (`-n`)
* List occurrences:
    * `--output-file FILE`
    * `--output-format FORMAT` (or `-f`)
    * `--detection-types TYPE [TYPE2 ...]` (or `-t`)
    * `--category CATEGORY [CATEGORY2 ...]` (or `-c`)
    * `--detection-label LABEL` (or `-l`)
    * `--detection-persons PERSON[,...]` (or `-p`)
    * `--detection-valossa-cid ID` (or `-i`)
    * `--detection-external-concept-id ONTOLOGY ID`
    * `--min-confidence FLOAT` (FLOAT=[0..1])
    * `--start-second N`
    * `--length-seconds N`
    * `--end-second N`
    * `--sort-by METHOD`
    * `--extra-header HEADER [HEADER2 ...]`
* Summary:
    * `--output-file FILE`
    * `--output-format FORMAT` (or `-f`)
    * `--detection-type TYPE` (or `-t`)
    * `--category CATEGORY [CATEGORY2 ...]` (or `-c`)
    * `--n-most-prominent-detections-per-type N` (or `-n`)
    * `--separate-face-identities`
    * `--skip-unknown-faces`
    * `--emotion`
* Plot, `--bar-summary`
    * `--n-most-prominent-detections-per-type N` (or `-n`) **Required**
    * `--detection-type` (or `-t`) **Required**
    * `--output-file FILE`
    * `--output-format FORMAT` (or `-f`)
    * `--min-confidence FLOAT` (FLOAT=[0..1])
    * `--image-size`
    * `--separate-face-identities`
    * `--skip-unknown-faces`
    * `--simple`
    * `--show-title`

Available detection types are listed at [Valossa Core API Documentation](https://portal.valossa.com/portal/apidocs#detectiontypes).
