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

import os
import re
import sys
import datetime
import subprocess as sp

import numpy as np

from Bio import SeqIO
from hashlib import md5
from string import strip
from socket import getfqdn
from getpass import getuser
from module_utils import lookForFile, splitSequence
from module_utils import format_time, lookForDirectory

## Define the minimum sequences number to reconstruct any alignment/tree
min_seqs_analysis = "3"

file_extension = {
  "prank":          "prk",
  "mafft":          "mft",
  "kalign":         "kal",
  "muscle":         "msl",
  "clustalw":       "clw",
  "t_coffee":       "tce",
  "dialign_tx":     "dtx",
  "clustal_omega":  "clo",
}

## Exit code meanings
##  80: Not enough sequences
exit_codes = {
  "trimal":         82,    ##  82: Problems trimming input alignment using trimAl
  "readal":         81,    ##  81: Problems handling input sequence/msa files

  "prank":          92,    ##  92: Problems aligning with PRANK
  "mafft":          87,    ##  87: Problems aligning with MAFFT
  "kalign":         89,    ##  89: Problems aligning with KAlign
  "muscle":         86,    ##  86: Problems aligning with MUSCLE
  "t_coffee":       90,    ##  90: Problems using T-Coffee and its flavors
  "m_coffee":       90,
  "dialign_tx":     88,    ##  88: Problems aligning with DiAlign-TX
  "clustalw":       91,    ##  91: Problems aligning with Clustal-W
  "clustal_omega":  92,    ##  92: Problems aligning with Clustal-Omega

  "generic":        95,    ##  95: Program not supported
}

def alignment(parameters):

  ## Get output folder/generic filename
  oFile = os.path.join(parameters["out_directory"], parameters["prefix"])

  current_directory = os.getcwd()
  ## Change current directory to the output folder. Any temporary file will be
  ## generated therefore in this folder
  os.chdir(parameters["out_directory"])

  ## Depending on the verbosity level - set the appropriate logfile value
  if not "verbose" in parameters or parameters["verbose"] == 0:
    logFile = open(os.devnull, 'wb')

  ## ALL/logfile
  elif parameters["verbose"] == 1:
    ## Set output filename and log file
    mode = "w" if parameters["replace"] and parameters["step"] == 0 else "a+"
    logFile = open(oFile + ".log", mode)

  ## ALL/Stderr
  elif parameters["verbose"] == 2:
    logFile = sys.stderr

  start = datetime.datetime.now()
  date = start.strftime("%H:%M:%S %m/%d/%y")
  print >> logFile, ("###\n###\tSTEP\tMultiple Sequence Alignment\tSTART\t%s"
    + "\n###") % (date)
  logFile.flush()

  ## Get which program/s will be used to align the input sequences. Check such
  ## program/s are listed among the available binaries
  if not "alignment" in parameters:
    sys.exit("ERROR: Check your configuration file. There is no definition for "
      + "the ALIGNMENT step")

  for program in parameters["alignment"]:
    if not program in parameters:
      sys.exit(("ERROR: Selected program '%s' is not available accordding to "
        "the configuration file") % (program))

  ## Check whether "readAl" is available or not. It is useful for sequences
  ## manipulation independently of the input format.
  if not "readal" in parameters:
    sys.exit("ERROR: Check your CONFIG file. 'readAl' is not available")

  ## Evaluate whether input sequences will be aligned following one direction,
  ## forward - left to right - or both directions meaning forward/reverse
  if isinstance(parameters["both_direction"], basestring):
    parameters["both_direction"] = parameters["both_direction"].lower() =="true"

  ## Check whether if an special mode has been selected - for instance
  ## "prot2codon" or "prot2nuc" - and a CDS file has been defined
  ## If not mode is define, we will work with a datatype - normally proteins
  if "cds" in parameters and (not "residue_datatype" in parameters or \
    not parameters["residue_datatype"] in ["prot2codon", "prot2nuc"]):
    sys.exit("ERROR: To use an additional CDS file, you should set the <parame"
      + "ter> 'residue_datatype' to either 'prot2codon' or 'prot2nuc'")

  if not "cds" in parameters and parameters["residue_datatype"] in \
    ["prot2codon", "prot2nuc"]:
    sys.exit("ERROR: When 'residue_datatype' is set to either 'prot2codon' or "
      + "'prot2nuc', an input CDS file is needed")

  ## In normal cases, we don't really need to define a specific datatype to
  ## build alignments but we need the variable defined to avoid crashed in some
  ## checks
  if not "residue_datatype" in parameters:
    parameters["residue_datatype"] = ""

  ## Get some information such as number of input sequences and the presence of
  ## selenocysteine/pyrrolysine residues
  numSeqs, selenocys, pyrrolys = check_count_sequences(parameters["in_file"])

  ## Set the minimum number of sequences required to reconstruct an alignment
  min_seqs = int(parameters["min_seqs"] if "min_seqs" in parameters else \
    min_seqs_analysis)
  
  ## Finish when there are not enough sequences to make an alignment
  if numSeqs < min_seqs:
    print >> logFile, ("### INFO: It is necessary, at least, %d sequences to "
      + "to reconstruct an alignment (%d)") % (min_seqs, numSeqs)
    sys.exit(80)

  ## Otherwise, process the input sequence, substitute rare amino-acids and
  ## reverse input sequences when neccesary
  
  ## Reverse input sequences if needed it
  if parameters["both_direction"]:

    ## If get an positive answer means, the reverse sequence file has been
    ## generated and therefore any downstream file should be over-written
    out_file = ("%s.seqs.reverse") % (oFile)

    if reverseSequences(parameters["readal"], parameters["in_file"], \
      out_file, parameters["replace"], logFile):
      parameters["replace"] = True

  ## Substitute rare amino-acids if needed it
  if selenocys or pyrrolys:

    out_file = ("%s.seqs.no_rare_aa") % (oFile)

    ## If the output file has been generated, over-write, if any, downstream
    ## files
    if replaceRareAminoAcids(parameters["in_file"], out_file, \
      parameters["replace"], logFile, parameters["in_letter"]):
      parameters["replace"] = True

    ## If there is a reverse file, replace also the rare amino-acids in that one
    if parameters["both_direction"]:

      in_file = ("%s.seqs.reverse") % (oFile)
      out_file = ("%s.seqs.no_rare_aa.reverse") % (oFile)

      ## Replace any downstream file is the current one is generated again
      if replaceRareAminoAcids(in_file, out_file, parameters["replace"], \
        logFile, parameters["in_letter"]):
        parameters["replace"] = True

  ## Set in which directions alignments will be reconstructed
  directions = ["forward"]
  if parameters["both_direction"]:
    directions.append("reverse")

  generated_alignments = set()
  ## Once all required sequence files has been set-up, proceed to build the
  ## alignments itself.
  for prog in parameters["alignment"]:

    ## Get binary as well as any input parameters for each aligner and the
    ## output file extension
    binary = parameters[prog]

    key = ("%s_params") % (prog)
    params = parameters[key] if key in parameters else ""

    altern_ext = ("%s%s") % (prog[:2], prog[-1])
    extension = file_extension[prog] if prog in file_extension else altern_ext

    ## Generate as many alignments as needed
    for direc in directions:

      ## Set the input file depending on the presence of rare amino-acids
      if direc == "forward":
        in_file = ("%s.seqs.no_rare_aa") % (oFile) if selenocys \
          or pyrrolys else parameters["in_file"]
      else:
        in_file = ("%s.seqs.no_rare_aa.reverse") % (oFile) if selenocys \
          or pyrrolys else ("%s.seqs.reverse") % (oFile)

      out_file = ("%s.alg.%s%s.%s") % (oFile, "no_rare_aa." if selenocys \
        or pyrrolys else "", direc, extension)

      ## Perfom alignment and check whether it has been generated or already
      ## exist
      if perfomAlignment(prog, binary, params, in_file, out_file,
        logFile, parameters["replace"]):
        parameters["replace"] = True

      ## If any Selenocysteine or Pyrrolyseine is present, generate the final
      ## alignment removing the wild cards and putting back the original amino-
      ## acids
      if selenocys or pyrrolys:
        ## Get real output filename
        alt_file = ("%s.alg.%s.%s") % (oFile, direc, extension)

        ## Make the change and record whether files has been generated de-novo
        if replaceRareAminoAcids(out_file, alt_file, parameters["replace"], \
          logFile, parameters["in_letter"], back = True):
          parameters["replace"] = True

        ## We over-write out_file variable with the current outfile name.We will
        ## store such output file in case a meta-alignment has to be generated
        out_file = alt_file

      ## For reverse alignment, get its reverse - meaning get residues according
      ## to the initial order
      if direc == "reverse":
        in_file = ("%s.alg.reverse.%s") % (oFile, extension)
        out_file = ("%s.alg.reverse.forw.%s") % (oFile, extension)

        if reverseSequences(parameters["readal"], in_file, out_file, \
          parameters["replace"], logFile):
          parameters["replace"] = True

      ## Store all output alignments
      generated_alignments.add(out_file)

  if len(generated_alignments) > 1 and "consensus" in parameters:
    prog = parameters["consensus"][0]
    if not prog in parameters:
      sys.exit(("ERROR: Selected program '%s' is not available accordding to "
        "the configuration file") % (prog))

    ## Get binary as well as any input parameters for each aligner and the
    ## output file extension
    binary = parameters[prog]
    prog_params = ("%s_params") % (prog)

    params = parameters[prog_params] if prog_params in parameters else ""
    params = ("%s -aln %s") % (params, " ".join(generated_alignments))

    out_file = ("%s.alg.metalig") % (oFile)
    if perfomAlignment(prog, binary, params, parameters["in_file"], out_file,
      logFile, parameters["replace"]):
      parameters["replace"] = True

    ## Make such untrimmed alignment it is in phylip format
    convertInputFile_Format("readal", parameters["readal"], out_file,out_file,
      "phylip", logFile, parameters["replace"])

  ## Set the current output alignment as the one generated at a previous step
  else:
    out_file = generated_alignments.pop()

    ## Make such untrimmed alignment it is in phylip format
    convertInputFile_Format("readal", parameters["readal"], out_file,out_file,
      "phylip", logFile, parameters["replace"])

  ## Either we have to trim the final alignment or we have to backtranslate to
  ## codons/nucleotides, we will need to check for a program - hopefully
  ## trimAl - to make the job
  if parameters["residue_datatype"] in ["prot2codon","prot2nuc"] or "trimming" \
    in parameters:

    prog = parameters["trimming"][0]
    if not prog in parameters:
      sys.exit(("ERROR: Selected program '%s' is not available accordding to "
        "the configuration file") % (prog))

    ## Get binary as well as any input parameters for each aligner and the
    ## output file extension
    binary = parameters[prog]

  ## If the modes "prot2codon" or "prot2nuc" are selected - backtranslated the
  ## untrimmed/final alignment
  if parameters["residue_datatype"] in ["prot2codon", "prot2nuc"]:

    prog_params = ("%s_cds") % (prog)
    params = parameters[prog_params] if prog_params in parameters else ""

    if (trimmingAlignment(prog, binary, params, out_file + "_cds", logFile,
      parameters["replace"], in_file = out_file, cds = parameters["cds"])):
      parameters["replace"] = True

    ## Make such untrimmed alignment it is in phylip format
    convertInputFile_Format("readal", parameters["readal"], out_file + "_cds",
      out_file + "_cds" ,"phylip", logFile, parameters["replace"])

  ## If set, trim resulting alignment
  if "trimming" in parameters:
    prog = parameters["trimming"][0]
    if not prog in parameters:
      sys.exit(("ERROR: Selected program '%s' is not available accordding to "
        "the configuration file") % (prog))

    ## Get binary as well as any input parameters for each aligner and the
    ## output file extension
    prog_params = ("%s_params") % (prog)
    params = parameters[prog_params] if prog_params in parameters else ""

    clean_file = ("%s.alg.clean") % (oFile)

    prog_params = ("%s_compare") % (prog)
    if len(generated_alignments) > 1:
      if prog_params in parameters:
        params = ("%s %s") % (params, parameters[prog_params])

      path_file = ("%s.alg.paths") % (oFile)
      print >> open(path_file, "w"), "\n".join(generated_alignments)

      trimmingAlignment(prog, binary, params, clean_file, logFile,
        parameters["replace"], compare_msa = path_file, force_refer_msa = \
        out_file)

      ## If the backtranslation to codon/nucleotides is required, do it
      if parameters["residue_datatype"] in ["prot2codon", "prot2nuc"]:
        prog_params = ("%s_cds") % (prog)
        if prog_params in parameters:
          params = ("%s %s") % (params, parameters[prog_params])

        trimmingAlignment(prog, binary, params, clean_file + "_cds", logFile,
          parameters["replace"], compare_msa = path_file, force_refer_msa = \
          out_file, cds = parameters["cds"])

    else:
      trimmingAlignment(prog, binary, params, clean_file, logFile,
        parameters["replace"], in_file = out_file)

      ## If the backtranslation to codon/nucleotides is required, do it
      if parameters["residue_datatype"] in ["prot2codon", "prot2nuc"]:
        prog_params = ("%s_cds") % (prog)
        if prog_params in parameters:
          params = ("%s %s") % (params, parameters[prog_params])

        trimmingAlignment(prog, binary, params, clean_file + "_cds", logFile,
          parameters["replace"], in_file = out_file, cds = parameters["cds"])

    ## After the trimming, set the final output file as the trimmed file
    out_file = clean_file + ("_cds" if parameters["residue_datatype"] in \
      ["prot2codon", "prot2nuc"] else "")

  final = datetime.datetime.now()
  date = final.strftime("%H:%M:%S %m/%d/%y")
  print >> logFile, ("###\n###\tSTEP\tMultipple Sequence Alignment\tEND\t"
    + "%s") % (date)

  ## We return a DELTA object comparing both timestamps
  total = format_time(final - start if start else 0)
  print >> logFile, ("###\tTOTAL Time\tMultiple Sequence Alignment\t%s"
    + "\n###") % (total)

  ## We just close logfile and clean it up when it is a file
  if "verbose" in parameters and parameters["verbose"] == 1:
    logFile.close()

    ## Clean-up log directory from undesirable lines
    try:
      sp.call(("sed -i '/^$/d' %s.log") % (oFile), shell = True)
      sp.call(("sed -i '/^M/d' %s.log") % (oFile), shell = True)
      sp.call(("sed -i '/\r/d' %s.log") % (oFile), shell = True)
    except OSError:
      print >> sys.stderr, ("ERROR: Impossible to clean-up '%s.log' log file") \
        % (oFile)

  ## Update the input file parameter and return the dictionary containing all
  ## parameters. Those parameters may be used in other steps
  parameters["in_file"] = out_file

  ## Before returning to the main program, get back to the original working
  ## directory
  os.chdir(current_directory)

  return parameters

def check_count_sequences(in_file, in_format = "fasta"):
  '''
  Given a set of sequences, return how many there are as well as if any
  selenocysteine or pyrrolysine is detected among the sequences
  '''

  numb_sequences, selenocys, pyrrolys = 0, False, False
  for record in SeqIO.parse(in_file, in_format):
    numb_sequences += 1

    seq = str(record.seq).upper()
    ## Detect any ocurrence of selenocysteine/pyrrolysine residues
    if seq.count("U") != 0:
      selenocys = True
    if seq.count("O") != 0:
      pyrrolys = True

  return numb_sequences, selenocys, pyrrolys

def reverseSequences(binary, in_file, out_file, replace, logFile):
  '''
  Reverse the input sequences using readAl for that purpose
  '''

  ## Check whether the output file already exists. If it is not set to replace
  ## it, just return to the calling function
  if lookForFile(out_file) and not replace:
    return False

  ## Define the command-line for getting the sequences reverse independently of
  ## being aligned or not and of the input format
  cmd = ("%s -in %s -out %s -reverse") % (binary, in_file, out_file)

  name = getfqdn()
  print >> logFile, ("###\n###\treadAl - reverse seqs")
  print >> logFile, ("###\t[%s]\tCommand-line\t%s\n###") % (name, cmd)

  try:
    proc = sp.Popen(cmd, shell = True, stderr = logFile, stdout = logFile)
  except OSError, e:
    print >> sys.stderr, "ERROR: Execution failed: " + str(e)
    sys.exit(exit_codes["readal"])

  if proc.wait() != 0:
    print >> sys.stderr, ("ERROR: Execution failed: readAl")
    sys.exit(exit_codes["readal"])

  return True

def replaceRareAminoAcids(in_file, out_file, replace, logFile, combinations, \
  back = False, in_format = "fasta"):
  '''
  Replace rare amino-acids occurrence by wildcards, and vice-versa. It will only
  works with input files in FASTA format
  '''

  ## Check whether the output file already exists. If it is not set to replace
  ## it, just return to the calling function
  if lookForFile(out_file) and not replace:
    return False

  subs = {}
  for comb in map(strip, combinations.split()):
    ## Depending on the direction of the conversion, make it on one way or in
    ## the way around
    src, dst = comb.split(":")[::-1] if back else comb.split(":")
    subs.setdefault(src, dst)

  ## Record some stats about which amino-acids and how many times they have been
  ## detected
  stats = dict([(letter, 0) for letter in subs])

  oFile = open(out_file, "w")
  for record in SeqIO.parse(in_file, in_format):
    seq = str(record.seq)
    for letter in subs:
      seq = seq.replace(letter, subs[letter])
      stats[letter] += seq.count(subs[letter])
    print >> oFile, (">%s\n%s") % (record.id, splitSequence(seq))
  oFile.close()

  output = "|\t".join([("'%s' > '%s'\tfreq: %d") % (aa, subs[aa], stats[aa]) \
    for aa in stats if stats[aa] > 0])

  name = getfqdn()
  print >> logFile, ("###\n###\t[%s]\tSubstituting Rare Amino-Acids") % (name)
  print >> logFile, ("###\tReport\t%s") % (output)
  logFile.flush()

  return True

def perfomAlignment(label, binary, parameters, in_file, out_file, logFile, \
  replace):

  '''
  Function to format the command-line of different multiple sequence alignment
  programs and execute such command lines. It is also support a generic call
  for those programs which has no specific support in the pipeline
  '''

  ## Check whether the output file already exists. If it is not set to replace
  ## it, just return to the calling function
  if lookForFile(out_file) and not replace:
    return False

  if label in ["muscle", "kalign"]:
    cmd = ("%s %s -in %s -out %s") % (binary, parameters, in_file, out_file)

  elif label in ["clustalw"]:
    cmd = ("%s %s -INFILE=%s -OUTFILE=%s") % (binary, parameters, in_file, \
      out_file)

  elif label in ["clustal_omega"]:
    cmd = ("%s %s --in %s --out %s") % (binary, parameters, in_file, out_file)

  ## elif label in ["mafft", "dialign_tx"]:
  elif label in ["mafft"]:
    cmd = ("%s %s %s > %s") % (binary, parameters, in_file, out_file)

  elif label in ["prank"]:
    cmd = ("%s %s -d=%s -o=%s") % (binary, parameters, in_file, out_file)

  ## Starting for newer DiAlign-TX versions
  elif label in ["dialign_tx"]:
    cmd = ("%s %s %s %s") % (binary, parameters, in_file, out_file)

  ## On t-coffee case, we need to set-up some ENV variables to be able to run
  ## smoothly the program
  elif label in ["t_coffee", "m_coffee"]:

    sp.call(("mkdir -p -m0777 /tmp/tcoffee"), shell = True)
    drc = ("/tmp/tcoffee/%s") % (getuser())
    sp.call(("mkdir -p -m0777 %s") % (drc), shell = True)
    os.putenv("LOCKDIR_4_TCOFFEE", drc)
    os.putenv("TMP_4_TCOFFEE", drc)

    cmd = ("%s %s %s -outfile %s") % (binary, in_file, parameters, out_file)

  ## In any other case, finish with a generic error
  else:
    sys.exit(exit_codes["generic"])

  ## Record the time and precise command-line
  name = getfqdn()
  start = datetime.datetime.now()
  date = start.strftime("%H:%M:%S %m/%d/%y")

  print >> logFile, ("###\n###\t%s - Alignment\t%s") % (label.upper(), date)
  print >> logFile, ("###\t[%s]\tCommand-line\t%s\n###") % (name, cmd)
  logFile.flush()

  try:
    proc = sp.Popen(cmd, shell = True, stderr = logFile, stdout = logFile)
  except OSError, e:
    print >> sys.stderr, "ERROR: Execution failed: " + str(e)
    sys.exit(exit_codes[label])

  if proc.wait() != 0:
    print >> sys.stderr, ("ERROR: Execution failed: %s [exit code != -1]") \
      % (label.upper())
    sys.exit(exit_codes[label])

  final = datetime.datetime.now()
  ## We return a DELTA object comparing both timestamps
  total = format_time(final - start if start else 0)
  print >> logFile, ("###\tTime\t%s\n###") % (total)
  logFile.flush()

  ## If we are working with PRANK, move output file - which should have a suffix
  ## depending on the output format
  if label in ["prank"]:
    suffix = "fas" if parameters.find("-f=") == -1 else \
      "nex" if parameters.find("-f=nexus") != -1 else "phy"
    if lookForFile(out_file + ".best." + suffix):
      sp.call(("mv %s.best.%s %s") % (out_file, suffix, out_file), shell = True)

  ## If any mode of t_coffee is used: t_coffee or m_coffee, we should remove the
  ## guide tree generate during the program execution
  if label in ["t_coffee", "m_coffee"]:
    guide_tree = ".".join(os.path.split(in_file)[1].split(".")[:-1])
    sp.call(("rm -f %s.dnd") % (guide_tree), shell = True)

  ## Check whether the output alignment has been already generated.
  ## In case something goes wrong, remove the output file and finish the
  ## current execution
  if not checkAlignment(in_file, out_file):
    print in_file, out_file
    print >> sys.stderr, ("ERROR: Execution failed: %s [file check]") % \
      (label.upper())
    # sp.call(("rm -f %s") % (out_file), shell = True)
    sys.exit(exit_codes[label])

  return True

def trimmingAlignment(label, binary, parameters, out_file, logFile, replace, \
  in_file = None, compare_msa = None, force_refer_msa = None, cds = None):
  '''
  Function to trim a given multiple sequence alignment according to a number of
  parameters. It may also returns the output file in codons if appropiate
  parameters are used.
  '''

  ## Check whether the output file already exists. If it is not set to replace
  ## it, just return to the calling function
  if lookForFile(out_file) and not replace:
    return False

  cmd = ""
  ## Construct a customize trimAl command-line call
  ## If an input CDS file is set, generate the output alignment using such
  ## information
  if cds:
    cmd = ("%s -backtrans %s ") % (cmd, cds)
  if compare_msa:
    cmd = ("%s -compareset %s ") % (cmd, compare_msa)
  if force_refer_msa:
    cmd = ("%s -forceselect %s ") % (cmd, force_refer_msa)
  if in_file:
    cmd = ("%s -in %s ") % (cmd, in_file)
  cmd = ("%s %s -out %s %s") % (binary, cmd, out_file, parameters)

  ## Record the time and precise command-line
  name = getfqdn()
  start = datetime.datetime.now()
  date = start.strftime("%H:%M:%S %m/%d/%y")

  print >> logFile, ("###\n###\tTrimming Input MSA\t%s") % (date)
  print >> logFile, ("###\t[%s]\tCommand-line\t%s\n###") % (name, cmd)
  logFile.flush()

  try:
    proc = sp.Popen(cmd, shell = True, stderr = logFile, stdout = logFile)
  except OSError, e:
    print >> sys.stderr, "ERROR: Execution failed: " + str(e)
    sys.exit(exit_codes[label])

  if proc.wait() != 0:
    print >> sys.stderr, ("ERROR: Execution failed: %s") % (label.upper())
    sys.exit(exit_codes[label])

  final = datetime.datetime.now()
  ## We return a DELTA object comparing both timestamps
  total = format_time(final - start if start else 0)
  print >> logFile, ("###\tTime\t%s\n###") % (total)
  logFile.flush()

  return True

def checkAlignment(ifile_1, ifile_2, iformat_1 = "fasta", iformat_2 = "fasta"):
  '''
  Read two giving input files and check both contain the same sequences and
  the same input strings
  '''

  ## We introduce a delay to ensure data is already written in the disk.
  ## With high-computing facilities, sometimes there are some problems of
  ## writing to disk the already computed results
  if not lookForFile(ifile_1) or not lookForFile(ifile_2, attempts = 5):
    return False

  ## Read both input files - remvoving ambiguous characters and checking for
  ## duplicate names. We used regular expressions for removing any character
  inSeqs_1 = {}
  for record in SeqIO.parse(ifile_1, iformat_1):
    if record.id in inSeqs_1:
      print >> sys.stderr, ("ERROR: Repeated sequence '%s' ['%s']") \
        % (record.id, ifile_1)
      return False
    seq = re.sub(r'[^a-zA-Z]', '', str(record.seq))
    inSeqs_1.setdefault(record.id, seq.upper().strip())

  inSeqs_2 = {}
  for record in SeqIO.parse(ifile_2, iformat_2):
    if record.id in inSeqs_2:
      print >> sys.stderr, ("ERROR: Repeated sequence '%s' ['%s']") \
        % (record.id, ifile_2)
      return False
    seq = re.sub(r'[^a-zA-Z]', '', str(record.seq))
    inSeqs_2.setdefault(record.id, seq.upper().strip())

  ## If there are inconsistencies among sequences, inform about them
  if set(inSeqs_1.keys()) ^ set(inSeqs_2.keys()) != set():
    print >> sys.stderr,("ERROR: Non-overlapping sequences identifier detected "
      + "between input ['%s'] and output ['%s'] files ") % (ifile_1, ifile_2)
    return False

  ## Check that sequences in both files contain the same residues
  for seq in inSeqs_1:
    if inSeqs_1[seq] != inSeqs_2[seq]:
      print >> sys.stderr, ("ERROR: Different sequence composition for '%s' bet"
        + "ween input ['%s'] and output ['%s'] files") % (seq, ifile_1, ifile_2)
      return False

  ## If everything is OK, inform about it
  return True

def getFileFormat(label, binary, in_file, logFile):
  '''
  Get format for the input sequences file using readAl
  '''

  ## Define the command-line for getting the input file format
  cmd = ("%s -in %s -format") % (binary, in_file)

  name = getfqdn()
  print >> logFile, ("###\n###\t%s - get format") % (label.upper())
  print >> logFile, ("###\t[%s]\tCommand-line\t%s\n###") % (name, cmd)
  logFile.flush()

  try:
    proc = sp.Popen(cmd, shell = True, stderr = logFile, stdout = sp.PIPE)
  except OSError, e:
    print >> sys.stderr, "ERROR: Execution failed: " + str(e)
    sys.exit(exit_codes[label])

  in_file_format, aligned = None, None
  for line in map(strip, proc.communicate()[0].split("\n")):
    if line.startswith("## Input file format") and not in_file_format:
      in_file_format = map(strip, line.split("\t"))[1].lower()
    if line.startswith("## Input file aligned") and not aligned:
      aligned = map(strip, line.split("\t"))[1].lower() == "yes"

  return in_file_format, aligned

def convertInputFile_Format(label, binary, in_file, out_file, out_format, \
  logFile, replace):
  '''
  Convert a giving input file into a given output format
  '''

  ## Check whether the output file already exists. If it is not set to replace
  ## it, just return to the calling function
  if lookForFile(out_file) and not replace:
    return False

  ## Define the command-line for getting the input file format
  cmd = ("%s -in %s -out %s -%s") % (binary, in_file, out_file, out_format)

  name = getfqdn()
  print >> logFile, ("###\n###\t%s - get format") % (label.upper())
  print >> logFile, ("###\t[%s]\tCommand-line\t%s\n###") % (name, cmd)
  logFile.flush()

  try:
    proc = sp.Popen(cmd, shell = True, stderr = logFile, stdout = logFile)
  except OSError, e:
    print >> sys.stderr, "ERROR: Execution failed: " + str(e)
    sys.exit(exit_codes[label])

  if proc.wait() != 0:
    print >> sys.stderr, ("ERROR: Execution failed: %s") % (label.upper())
    sys.exit(exit_codes[label])

  return True
