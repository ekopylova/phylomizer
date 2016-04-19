#!/usr/bin/python

"""
  phylomizer - automated phylogenetic reconstruction pipeline - it resembles the
  steps followed by a phylogenetist to build a gene family tree with error-control
  of every step

  Copyright (C) 2014 - Salvador Capella-Gutierrez, Toni Gabaldon

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

desc = """
  --
  phylomizer - Copyright (C) 2014  Salvador Capella-Gutierrez, Toni Gabaldon
  [scapella, tgabaldon]_at_crg.es

  This program comes with ABSOLUTELY NO WARRANTY;
  This is free software, and you are welcome to redistribute it
  under certain conditions;
  --
  Phylogenetic tree reconstruction pipeline. It comprises three main steps:

  1) Homology search using tools such as BLAST or HMMER.

  2) Multiple Sequence Alignment (MSA) including the usage of different
     aligners and the generation of alignments in different directions,
     the generation of a meta-alignment and the trimming of these meta-
     MSA using information from individual alignments.

  3) Phylogenetic tree reconstruction using fast model selection over NJ
     trees. It is possible to reconstruct trees using AA, NT or Codons.
"""

import os
import sys
import argparse
import datetime

from module_homology import homology
from module_trees import phylogenetic_trees
from module_alignments import alignment, min_seqs_analysis
from module_utils import readConfig, printConfig, default_verbose, format_time
from module_utils import lookForFile, lookForDirectory, verbose_levels

## Get dinamically version
#~ from _version import get_versions
#~ __version = get_versions()['version']
#~ del get_versions

__version = "1.0.0"

if __name__ == "__main__":

  usage = ("\n\npython %(prog)s -i seed_sequence/s -c config_file -d output_"
    + "directory -b sequences_db [other_options]\n")

  parser = argparse.ArgumentParser(description = desc, usage = usage,
    formatter_class = argparse.RawTextHelpFormatter)

  parser.add_argument("-i", "--in", dest = "inFile", type = str, default = None,
    help = "Input file containing the query sequence/s")

  parser.add_argument("--min_seqs", dest = "minSeqs", type = str, default = None,
    help = "Set the minimum sequences number to reconstruct an alignment/tree."
    + "\nThis parameter overwrites whatever is set on the config file.")

  parser.add_argument("--max_hits", dest = "maxHits", type = str, default = None,
    help = "Set the maximum accepted homology hits after filtering for e-value/"
    + "coverage.\nThis parameter overwrites whatever is set on the config file.")

  parser.add_argument("-d", "--db", dest = "dbFile", type = str, default = None,
    help = "Input file containing the target sequence database")

  parser.add_argument("--cds", dest = "cdsFile", type = str, default = None,
    help = "Input file containing CDS corresponding to input protein seqs")

  parser.add_argument("-c", "--config", dest = "configFile", default = None, \
    type = str, help = "Input configuration file")

  parser.add_argument("-o", "--out", dest = "outFolder", type = str, default = \
    ".", help = "Output folder where all generated files will be dumped")

  parser.add_argument("-p", "--prefix", dest = "prefix", type = str, default = \
    "", help = "Set the prefix for all output files generated by the pipeline")

  parser.add_argument("-r", "--replace", dest = "replace", default = False, \
    action = "store_true", help = "Over-write any previously generated file")

  parser.add_argument("--version", action = "version", version ='%(prog)s \"' \
    + __version + "\"")

  parser.add_argument("-v", "--verbose", dest = "verbose", type = str, default \
    = None, choices = sorted(verbose_levels.keys()), help = "Set how informati"
    + "on should be dumped. It could be used levels or tags\nIt overwrites what"
    + "ever is set on the configuration file.")

  ## If no arguments are given, just show the help and finish
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

  args = parser.parse_args()

  ## Get current directory - we will use this for normalizing input files and
  ## directories to their absolute paths
  current_directory = os.getcwd()

  ## Assign input parameters directly to the dictionary which will contain all
  ## current run configuration.
  parameters = {}
  parameters.setdefault("replace", args.replace)

  ## Assign which step is being executed. It is useful to know whether the log
  ## file should be replaced or not - even when the flag "replace" is set
  parameters.setdefault("step", 0)

  ## Check parameters related to files / directories
  if not lookForFile(args.inFile):
    sys.exit(("ERROR: Check input QUERY SEQUENCE/s file '%s'") % (args.inFile))
  parameters.setdefault("in_file", os.path.abspath(args.inFile))

  if not lookForFile(args.dbFile):
    sys.exit(("ERROR: Check input TARGET SEQUENCES file '%s'") % (args.dbFile))
  parameters.setdefault("db_file", os.path.abspath(args.dbFile))

  if args.cdsFile:
    if not lookForFile(args.cdsFile):
      sys.exit(("ERROR: Check input CDS file '%s'") % (args.cdsFile))
    parameters.setdefault("cds", os.path.abspath(args.cdsFile))

  if not lookForFile(args.configFile):
    sys.exit(("ERROR: Check input CONFIG file '%s'") % (args.configFile))
  parameters.setdefault("config_file", os.path.abspath(args.configFile))

  if not lookForDirectory(args.outFolder):
    sys.exit(("ERROR: Check output folder '%s'") % (args.outFolder))
  parameters.setdefault("out_directory", os.path.abspath(args.outFolder))

  ## Set output files prefix name depending on input user selection
  tag = os.path.split(args.inFile)[1].split(".")[0]
  parameters.setdefault("prefix", args.prefix if args.prefix else tag)

  ## Read the other parameters from the input config file
  parameters.update(readConfig(parameters["config_file"]))

  ## Check specific values for input parameters.
  if not "coverage" in parameters or not (0.0 < float(parameters["coverage"]) \
    <= 1.0):
    sys.exit(("ERROR: Check your 'coverage' parameter"))

  ## Overwrite maximum homology hits when set any value by command-line
  if args.maxHits:
    parameters["hits"] = args.maxHits

  if not "hits" in parameters or (parameters["hits"].isdigit() and \
    int(parameters["hits"]) < 1)  or (not parameters["hits"].isdigit() \
    and parameters["hits"] != "no_limit"):
    sys.exit(("ERROR: Check your 'homology accepted hits' upper limit value"))

  ## Set minimum sequences number for any alignment/tree has to be reconstructed
  if not "min_seqs" in parameters and not args.minSeqs:
    parameters.setdefault("min_seqs", min_seqs_analysis)

  elif args.minSeqs:
    parameters["min_seqs"] = args.minSeqs

  if not parameters["min_seqs"].isdigit() or int(parameters["min_seqs"]) < 1:
    sys.exit(("ERROR: Check your 'minimum sequnces number' value"))

  ## Check whether alignment will be reconstructed in one or two directions, i.e
  ## head and tails.
  if not "both_direction" in parameters:
    parameters["both_direction"] = True

  ## Configure level of verbosity
  if not "verbose" in parameters and not args.verbose:
    parameters["verbose"] = verbose_levels[default_verbose]

  elif "verbose" in parameters and not parameters["verbose"] in verbose_levels:
    sys.exit(("ERROR: Check your 'verbose' parameter. Available tags/levels [ '"
    + "%s' ]") % "', '".join(sorted(verbose_levels.keys())))

  else:
    key = args.verbose if args.verbose else parameters["verbose"]
    parameters["verbose"] = verbose_levels[key]

  ## Print all set-up parameters
  if parameters["verbose"] > 0:
    printConfig(parameters)

  ## If verbosity has to be redirected to no-where or to a specific log-file,
  ## open that file - depending on existence/replace flag - and dump the
  ## appropriate content there - In case of no verbosity it will be nothing.
  if parameters["verbose"] in [0, 1]:
    ## Get output folder/generic filename - and open log file
    oFile = os.path.join(parameters["out_directory"], parameters["prefix"])
    logFile = open(oFile + ".log", "w" if parameters["replace"] else "a+")

    if parameters["verbose"] == 1:
      ## We don't want to lose all configuration so we set the step to 1
      printConfig(parameters, logFile)
      parameters["step"] = 1
    logFile.close()

  ## We start counting the time for the whole process
  start = datetime.datetime.now()
  
  ## Launch the whole homology process - update some values in the parameters
  ## dictionary. It is needed to perform appropiately the next step
  parameters.update(homology(parameters))

  ## Assign which step is being executed. It is useful to know whether the log
  ## file should be replaced or not - even when the flag "replace" is set
  parameters["step"] = 1

  ## Reconstruct the Multiple Sequence Alignment for the selected sequences
  parameters.update(alignment(parameters))

  ## Assign which step is being executed. It is useful to know whether the log
  ## file should be replaced or not - even when the flag "replace" is set
  parameters["step"] = 2

  ## Reconstruct the Multiple Sequence Alignment for the input Sequences
  phylogenetic_trees(parameters)

  ## Get final time
  final = datetime.datetime.now()

  ## We return a DELTA object comparing both timestamps
  steps = "', '".join(args.steps)
  total = format_time(final - start if start else 0)

  ## Dump into stderr - when requested all verbose info or just stderr
  if parameters["verbose"] > 0:
    print(("\n###\tTOTAL Time\t[ '%s' ]\t%s\n###") % (steps, total), file=sys.stderr)

  ## Dump into logfile - when requested all verbose info or just logfile
  if parameters["verbose"] == 1:
    ## Get output folder/generic filename - Set output filename and log file
    oFile = os.path.join(parameters["out_directory"], parameters["prefix"])
    logFile = open(oFile + ".log", "a+")
    print(("\n###\tTOTAL Time\t[ '%s' ]\t%s\n###") % (steps, total), file=logFile)
    logFile.close()
