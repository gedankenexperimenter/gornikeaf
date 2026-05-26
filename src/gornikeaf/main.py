# -*- coding: utf-8 -*-
"""
This is a program for extracting data from EAF files and writing that data to a
CSV file for Megan Gornik's thesis project.
"""

import argparse
import csv
import logging
import os
import pathlib
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
MOTHER_TIER_NAME = 'FA1'
CHILD_TIER_NAME = 'CHI'
SPEAKER_CODES = {
    MOTHER_TIER_NAME : 1,
    CHILD_TIER_NAME  : 2,
}

ACTIVITY_TIER_NAME = 'PHS@TIME'
RESPONSIVITY_TIER_NAME = 'RES@FA1'
EFW_SUBTIER_NAME = 'EFW'
AFFECT_SUBTIER_DICT = {
    'HAPPY' : 'Affect_Happy',
    'SAD'   : 'Affect_Sad',
    'ANGER' : 'Affect_Angry',
    'WORRY' : 'Affect_Worry',
}
QUALITY_TIER_NAME = 'QLT@TRA'

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
        description="Generate summary of data in EAF file(s)"
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
    participant_id = pathlib.Path(eaf_file).stem

    output_records = []

    eaf = pympi.Elan.Eaf(eaf_file)

    tier_names = eaf.get_tier_names()
    logging.debug("All tiers: %s", format(list(tier_names)))

    if MOTHER_TIER_NAME not in tier_names:
        raise InputError(f"Missing {MOTHER_TIER_NAME} tier in file {eaf_file}")

    if CHILD_TIER_NAME not in tier_names:
        raise InputError(f"Missing {CHILD_TIER_NAME} tier in file {eaf_file}")

    output_records = []

    for speaker, speaker_code in SPEAKER_CODES.items():
        for segment in eaf.get_annotation_data_for_tier(speaker):
            logging.debug("%s segment: %s", speaker, format(segment))
            data = collect_segment_data(eaf, speaker, segment)
            data['Participant_ID'] = participant_id
            data['Speaker'] = speaker_code
            output_records.append(data)

    return output_records

# ------------------------------------------------------------------------------
def collect_segment_data(eaf, speaker, segment):
    """Return all the relevant data for a given segment
    """
    data = {}
    (start, end) = segment[:2]
    data['Start_Time'] = start
    data['End_Time'] = end
    data['Time_Period'] = get_activity_code(eaf, start)
    data['Emotion_Words'] = get_efw_count(eaf, speaker, start)
    data['Audio_Quality'] = get_audio_quality(eaf, start)
    for key, value in get_affect_codes(eaf, speaker, start).items():
        data[key] = value
    data['Responsivity'] = ''
    if speaker == MOTHER_TIER_NAME:
        data['Responsivity'] = get_responsivity_code(eaf, start)
    return data

# ------------------------------------------------------------------------------
def get_activity_code(eaf, start):
    """Get activity code at given time from time period subtier
    """
    seg = eaf.get_annotation_data_at_time(ACTIVITY_TIER_NAME, start + 1)
    if seg is None or len(seg) < 1:
        return 0
    activity = seg[0][2]
    if re.search(r'reading', activity, re.IGNORECASE):
        return 1
    if re.search(r'conversation', activity, re.IGNORECASE):
        return 2
    if re.search(r'play', activity, re.IGNORECASE):
        return 3
    return 0

# ------------------------------------------------------------------------------
def get_responsivity_code(eaf, start):
    """Get responsivity code at given time
    """
    seg = eaf.get_annotation_data_at_time(RESPONSIVITY_TIER_NAME, start + 1)
    if seg is None or len(seg) < 1:
        return '?'
    desc = seg[0][2]
    if re.search(r'passive', desc, re.IGNORECASE):
        return 2
    if re.search(r'elaborative', desc, re.IGNORECASE):
        return 3
    if re.search(r'disjointed', desc, re.IGNORECASE):
        return 4
    if re.search(r'directive', desc, re.IGNORECASE):
        return 5
    return '?'

# ------------------------------------------------------------------------------
def get_efw_count(eaf, speaker, start):
    """Get emotion-focused word count for speaker (mother or child) at given time
    """
    tier = EFW_SUBTIER_NAME + "@" + speaker
    seg = eaf.get_annotation_data_at_time(tier, start + 1)
    logging.debug("annotation data for tier %s at %s: %s", tier, start, format(seg))
    if seg is None or len(seg) < 1:
        logging.debug("timestamp: %s", format(seg))
        return '?'
    desc = seg[0][2]
    logging.debug("desc = %s", desc)
    m = re.match(r'.*(\d+)', desc)
    if m is not None:
        return m.group(1)
    return 0

# ------------------------------------------------------------------------------
def get_affect_codes(eaf, speaker, start):
    """Get affect data for speaker (mother or child) at given time
    """
    codes = {}
    for subtier, field in AFFECT_SUBTIER_DICT.items():
        tier = subtier + "@" + speaker
        seg = eaf.get_annotation_data_at_time(tier, start + 1)
        if seg is None or len(seg) < 1:
            codes[field] = ''
            continue
        desc = seg[0][2]
        m = re.match(r'^(\d)', desc)
        if m is not None:
            codes[field] = m.group(0)
        else:
            codes[field] = ''
            if re.search(r'neutral', desc, re.IGNORECASE):
                codes[field] = '0'
    return codes

# ------------------------------------------------------------------------------
def get_audio_quality(eaf, start):
    """Get audio recording quality at given time
    """
    seg = eaf.get_annotation_data_at_time(QUALITY_TIER_NAME, start + 1)
    if seg is None or len(seg) < 1:
        return '?'
    desc = seg[0][2]
    if re.search(r'noisy', desc, re.IGNORECASE):
        return 2
    if re.search(r'^y', desc, re.IGNORECASE):
        return 1
    if re.search(r'^n', desc, re.IGNORECASE):
        return 3
    if re.search(r'^o', desc, re.IGNORECASE):
        return 4
    return '?'

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
        'Participant_ID',
        'Speaker',
        'Start_Time',
        'End_Time',
        'Time_Period',
        'Responsivity',
        'Emotion_Words',
        'Affect_Happy',
        'Affect_Worry',
        'Affect_Sad',
        'Affect_Angry',
        'Audio_Quality',
    ])

    for eaf_file in args.eaf_files:
        try:
            output_records = collect_input_data(eaf_file)
            for record in output_records:
                output.writerow([
                    record['Participant_ID'],
                    record['Speaker'],
                    record['Start_Time'],
                    record['End_Time'],
                    record['Time_Period'],
                    record['Responsivity'],
                    record['Emotion_Words'],
                    record['Affect_Happy'],
                    record['Affect_Worry'],
                    record['Affect_Sad'],
                    record['Affect_Angry'],
                    record['Audio_Quality'],
                ])
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
