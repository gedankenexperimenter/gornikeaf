# -*- coding: utf-8 -*-
"""
This is a program for extracting data from EAF files and writing that data to a
CSV file for Megan Gornik's thesis project.
"""

import argparse
import csv
import logging
import os
import re
import sys

# pympi-ling is required for parsing of EAF files
import pympi

from gornikeaf import __version__

__author__ = "Michael Richters"
__copyright__ = "Michael Richters"
__license__ = "MIT"

# ==============================================================================
# Constants
ACTIVITY_TIER_NAME = 'Time Period sub'
NOISE_TIER_NAME = 'Trash sub'
MOTHER_TIER_NAME = 'Mother'
MOTHER_SUBTIER_NAMES = ['Responsivity', 'Emotion Words', 'Directed Speech', 'Type of Speech']
CHILD_TIER_NAME = 'Toddler'
CHILD_SUBTIER_NAMES = ['Emotion Words - Toddler']

# ==============================================================================
class Error(Exception):
    """Base class for errors in this module"""

class InputError(Error):
    """Exception raised for errors that occur when reading input

    Attributes:
        message (string): an description of the error condition
    """
    def __init__(self, message):
        super().__init__()
        self.message = message

# ==============================================================================
def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate summary of MusicBurst  tier data in EAF file(s)"
    )
    parser.add_argument(
        '--version',
        action  = 'version',
        version = "gornikeaf {ver}".format(ver=__version__),
    )
    parser.add_argument(
        '-v', '--verbose',
        dest    = 'loglevel',
        help    = "set loglevel to INFO",
        action  = 'store_const',
        const   = logging.INFO,
    )
    parser.add_argument(
        '-vv', '--very-verbose', '--debug',
        dest    = 'loglevel',
        help    = "set loglevel to DEBUG",
        action  = 'store_const',
        const   = logging.DEBUG,
    )
    parser.add_argument(
        '-o', '--output',
        metavar = '<csv_file>',
        type    = argparse.FileType('w'),
        default = 'gornikeaf-output.csv',
        help    = "Write output to <csv_file> (default: '%(default)s')",
    )
    parser.add_argument(
        '-d', '--delimiter',
        choices = ['tab', 'comma', 'ascii'],
        default = 'comma',
        help    = "Use <delimiter> as CSV output field separator (default: '%(default)s')",
    )
    parser.add_argument(
        'eaf_files',
        metavar = '<eaf_file>',
        nargs   = '+',
        help    = "The name(s) of the EAF file(s) to process",
    )
    return parser.parse_args(args)

# ==============================================================================
def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "%(levelname)s: %(message)s"
    logging.basicConfig(
        level   = loglevel,
        stream  = sys.stdout,
        format  = logformat,
        datefmt = "%Y-%m-%d %H:%M:%S",
    )

# ==============================================================================
def setup_output(filename, delimiter):
    """Setup CSV output and write header row

    Args:
      :obj:`argparse.Namespace`: command line parameters namespace

    Returns:
      :obj:`csv.writer`: CSV output object
    """

    # Create the CSV writer object as specified by args
    output = csv.writer(filename,
                        delimiter      = delimiter,
                        quoting        = csv.QUOTE_MINIMAL,
                        lineterminator = '\n')
    return output

# ==============================================================================
def collect_input_data(eaf_file):
    """Collect data from an EAF file

    Args:
      eaf_file (string): filename of an EAF file to analyze

    Returns:
      :obj:`OutputRecord`: record containing the output data
    """
    logging.info("Processing %s", eaf_file)

    output_records = []

    eaf = pympi.Elan.Eaf(eaf_file)

    tier_names = eaf.get_tier_names()
    logging.debug("All tiers: %s", format(list(tier_names)))

    if ACTIVITY_TIER_NAME not in tier_names:
        raise InputError(f"Missing {ACTIVITY_TIER_NAME} tier in file {eaf_file}")

    activity_segments = eaf.get_annotation_data_for_tier(ACTIVITY_TIER_NAME)

    for segment in activity_segments:
        logging.debug("%s segment: %s", ACTIVITY_TIER_NAME, format(segment))

    if NOISE_TIER_NAME not in tier_names:
        raise InputError(f"Missing {NOISE_TIER_NAME} tier in file {eaf_file}")

    noise_segments = eaf.get_annotation_data_for_tier(NOISE_TIER_NAME)

    for segment in noise_segments:
        logging.debug("%s segment: %s", NOISE_TIER_NAME, format(segment))

    if MOTHER_TIER_NAME not in tier_names:
        raise InputError(f"Missing {MOTHER_TIER_NAME} tier in file {eaf_file}")

    mother_segments = eaf.get_annotation_data_for_tier(MOTHER_TIER_NAME)

    for segment in mother_segments:
        (start, end, annotation) = segment[:3]
        logging.debug("%s segment: %s",
                      MOTHER_TIER_NAME, format((start, end, annotation)))
        data = get_mother_segment_data(eaf, start, end)
        data['Trash'] = get_noise_value(eaf, noise_segments, start, end)
        data['Time Period'] = get_activity_value(eaf, start)
        data['speaker'] = 0
        data['filename'] = eaf_file
        data['timestamp'] = start
        logging.info("%s", format(data))
        output_records.append(data)

    child_segments = eaf.get_annotation_data_for_tier(CHILD_TIER_NAME)

    for segment in child_segments:
        (start, end, annotation) = segment[:3]
        logging.debug("%s segment: %s",
                      CHILD_TIER_NAME, format((start, end, annotation)))
        data = get_child_segment_data(eaf, start, end)
        data['Trash'] = get_noise_value(eaf, noise_segments, start, end)
        data['Time Period'] = get_activity_value(eaf, start)
        data['Emotion Words'] = data.pop('Emotion Words - Toddler')
        data['speaker'] = 1
        data['Responsivity'] = ''
        data['Type of Speech'] = ''
        data['Directed Speech'] = ''
        data['filename'] = eaf_file
        data['timestamp'] = start
        logging.info("%s", format(data))
        output_records.append(data)

    return output_records

# ------------------------------------------------------------------------------
def get_noise_value(eaf, noise_segments, start, end):
    """Get prioritized noise segment annotation
    """
    segments = eaf.get_annotation_data_at_time(NOISE_TIER_NAME, start + 1)
    for noise_segment in noise_segments:
        if noise_segment[0] <= start:
            continue
        if noise_segment[0] >= end:
            break
        segments.append(noise_segment)

    noisy = False
    for segment in segments:
        if re.search(r'^no', segment[-1], re.IGNORECASE):
            return 0
        if (re.search(r'noisy', segment[-1], re.IGNORECASE) or
            re.search(r'overlap', segment[-1], re.IGNORECASE)):
            noisy = True
    if noisy:
        return 1
    return 2

# ------------------------------------------------------------------------------
def get_activity_value(eaf, start):
    """Get value from time period
    """
    segment = eaf.get_annotation_data_at_time(ACTIVITY_TIER_NAME, start + 1)[0]
    return segment[-1]

# ------------------------------------------------------------------------------
def get_mother_segment_data(eaf, start, end):
    """Get annotations from relevant subtiers
    """
    data = {}
    data['speaker'] = 'mother'
    logging.debug("Gather mother data from t=%s", start)
    for tier in MOTHER_SUBTIER_NAMES:
        segment = eaf.get_annotation_data_at_time(tier, start + 1)[0]
        if (segment[0] != start or segment[1] != end):
            logging.warning("Tier '%s' segment at %s doesn't match '%s' at %s",
                            tier, segment[0], MOTHER_TIER_NAME, start)
        logging.debug("%s: %s", tier, segment[-1])
        data[tier] = segment[-1]
    return data

# ------------------------------------------------------------------------------
def get_child_segment_data(eaf, start, end):
    """Get annotations from relevan subtiers
    """
    data = {}
    data['speaker'] = 'toddler'
    logging.debug("Gathering toddler data from t=%s", start)
    for tier in CHILD_SUBTIER_NAMES:
        segment = eaf.get_annotation_data_at_time(tier, start + 1)[0]
        if (segment[0] != start or segment[1] != end):
            logging.warning("Tier '%s' segment at %s doesn't match '%s' at %s",
                            tier, segment[0], CHILD_TIER_NAME, start)
        logging.debug("%s: %s", tier, segment[-1])
        data[tier] = segment[-1]
    return data

# ------------------------------------------------------------------------------
def convert_output_record(data):
    """Covert data record into a list for output csv
    """
    output_record = []

    # Participant ID
    output_record.append(os.path.basename(data['filename']).replace('.eaf', ''))

    # Speaker
    output_record.append(data['speaker'])

    # Timestamp
    output_record.append(data['timestamp'])

    # Responsivity
    responsivity = data['Responsivity']
    if re.search(r'passive', responsivity, re.IGNORECASE):
        responsivity = 0
    elif re.search(r'aborative', responsivity, re.IGNORECASE):
        responsivity = 1
    elif re.search(r'disconnected', responsivity, re.IGNORECASE):
        responsivity = 2
    else:
        responsivity = ''
    output_record.append(responsivity)

    # Emotion Words (count)
    match = re.search(r'\d+', data['Emotion Words'])
    if match is not None:
        output_record.append(match.group(0))
    else:
        output_record.append(0)

    # Type of Speech
    type_of_speech = data['Type of Speech']
    if re.search(r'recited', type_of_speech, re.IGNORECASE):
        type_of_speech = 0
    elif re.search(r'spontan', type_of_speech, re.IGNORECASE):
        type_of_speech = 1
    output_record.append(type_of_speech)

    # Directed Speech
    directed_speech = data['Directed Speech']
    if re.search(r'assistant', directed_speech, re.IGNORECASE):
        directed_speech = 0
    elif re.search(r'toddler', directed_speech, re.IGNORECASE):
        directed_speech = 1
    elif data['speaker'] == 0:
        logging.warning("Unexpected annotation value found for 'Directed Speech': %s",
                        data['Directed Speech'])
    output_record.append(directed_speech)

    # Time Period
    time_period = data['Time Period']
    if re.search(r'story', time_period, re.IGNORECASE):
        time_period = 0
    elif re.search(r'conversation', time_period, re.IGNORECASE):
        time_period = 1
    else:
        logging.warning("Unexpected annotation value found for 'Time Period': %s",
                        data['Time Period'])
    output_record.append(time_period)

    # Trash (noise)
    output_record.append(data['Trash'])

    return output_record

# ==============================================================================
def main(args):
    """Command-line interface function for the script to parse EAF files for
    segments in the 'Mother' and 'Toddler' tiers.  For each EAF file specified
    on the command line, it parses the data and writes a row for each segment to
    a CSV file, using code numbers for the different expected values.

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--verbose", "42"]``).

    """
    args = parse_args(args)
    setup_logging(args.loglevel)

    # First, set the output delimiter character from args
    output_delimiter = '\t'
    if args.delimiter == 'comma':
        output_delimiter = ','
    elif args.delimiter == 'ascii':
        output_delimiter = '\x1f'

    output = setup_output(args.output, output_delimiter)
    output.writerow([
        'Participant ID',
        'Speaker',
        'Timestamp',
        'Responsivity',
        'Emotion Words',
        'Type of Speech',
        'Directed Speech',
        'Time Period',
        'Trash',
    ])

    for eaf_file in args.eaf_files:
        try:
            output_records = collect_input_data(eaf_file)
            for record in output_records:
                output.writerow(convert_output_record(record))
        except InputError as err:
            logging.warning(err.message)
            continue

    if args.output != sys.stdout:
        args.output.close()

# ------------------------------------------------------------------------------
def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    # ^  This is a guard statement that will prevent the following code from
    #    being executed in the case someone imports this file instead of
    #    executing it as a script.
    #    https://docs.python.org/3/library/__main__.html

    # After installing your project with pip, users can also run your Python
    # modules as scripts via the ``-m`` flag, as defined in PEP 338::
    #
    #     python -m gornikeaf.main 42
    #
    run()
