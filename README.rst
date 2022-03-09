.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

=========
gornikeaf
=========

This program extracts data from a set of EAF files, summarizing segments found
in the ``Mother`` and ``Toddler`` tiers, with one row per segment written to a
CSV file.  The rows in the output file contain coded data based on annotations
found in subtiers for each of the segments, as well as the ``Time Period`` and
``Trash`` tiers.

Installation
============

Clone the repository, then use ``pip`` to install the ``gornikeaf`` tool::

  $ git clone https://github.com/gedankenexperimenter/gornikeaf

  $ cd gornikeaf

  $ pip install .

On Windows, if you're using `pyenv`, you may also need to run this command in
order to get the `gornikeaf` command in your path::

  $ pyenv rehash

This should result in a ``gornikeaf`` command line program becoming available
in your path. In a directory with EAF files containing the target data, then
run::

  $ gornikeaf *.eaf

The output data will be written to the file ``gornikeaf-output.csv``, containing
one row per ``Mother`` or ``Toddler`` utterance segment, with columns for:

- Participant ID (derived from the filename)
- Speaker (Mother=0, Toddler=1)
- Timestamp (milliseconds since the start of the recording)
- Responsivity (Passive=0, Elaborative/Collaborative=1, Disconnected=2)
- Emotion Words (number of emotion words in utterance segment)
- Type of Speech (Recited=0, Spontaneous=1)
- Directed Speech (Research Assistant=0, Toddler=1)
- Time Period (Story Reading=0, Conversation=1)
- Trash (No=0, Yes - Noisy Speech=1, Yes/Overlap=2)
