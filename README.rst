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

  $ git checkout dissertation

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
- Speaker (1 = Mother, 2 = Toddler)
- Start_Time (milliseconds since the start of the recording)
- End_Time (milliseconds since the start of the recording)
- Time_Period (1 = Story Reading, 2 = Post story conversation, 3 = Unstructured Play)
- Responsivity (2 = Passive, 3 = Collaborative, 4 = Disjointed, 5 = Directive)
- Emotion_Words (number of emotion words in utterance segment)
- Affect_Happy (intensity score from 0-4) 
- Affect_Worry (intensity score from 0-4) 
- Affect_Sad (intensity score from 0-4) 
- Affect_Angry (intensity score from 0-4) 
- Audio Quality (1 = Clear, 2 = Noisy, 3 = Unclear, 4 = Overlap)
