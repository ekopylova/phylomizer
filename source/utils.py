import sys, os, subprocess as sp
from operator import itemgetter
from getpass import getpass
from string import strip

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def lookForProgram(binary):
  '''
  Return if a given binary program is found in the standard file system or not
  '''
  try: pipe = sp.Popen("which " + binary, shell = True, stdout = sp.PIPE)
  except OSError, e: sys.exit("ERROR: Execution failed: " + str(e))

  program = pipe.stdout.readline().strip()
  if program: return program
  else: return None
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def lookForFile(inFile):
  '''
  Return if a given file exists or not
  '''
  return os.path.isfile(inFile) and os.path.getsize(inFile) > 0
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def lookForDirectory(inFolder, create = True):
  '''
  Return True if a given folder exists or it has been generated. Otherwise,
  return False
  '''
  if not os.path.isdir(inFolder):
    if create:
      try: sp.call("mkdir -p " + inFolder, shell = True)
      except OSError: sys.exit("ERROR: Impossible to create the directory")
  elif not os.access(inFolder, os.W_OK): return False
  return True
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

def unique(seq):
  '''
  Return a list without repetitions
  '''
  return list(set([entry for entry in seq]))
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def listDirectory(directory, fileExtList):
  '''
  Get list of file info objects for files of particular extensions
  '''
  fileList = [os.path.normcase(f) for f in os.listdir(directory)]
  return [ os.path.join(directory, f) for f in fileList \
           if os.path.splitext(f)[1] in fileExtList ]
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def sort_hits(x, y):
  '''
  Return 1, 0, -1 depending on the values comparison
  '''
  if float(x[10]) > float(y[10]):
    return 1
  elif float(x[10]) < float(y[10]):
    return -1;
  elif float(x[11]) < float(y[11]):
    return 1
  elif float(x[11]) > float(y[11]):
    return -1
  else:
    return 0
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def split_len(seq, length = 80):
  '''
  Split a given string in fields of "length"
  '''
  return [seq[i:i + length] for i in range(0, len(seq), length)]
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def readConfig(inFile, opts):
  '''
  '''
  iFile = open(inFile, "rU")

  for line in iFile.readlines():
    line = line.strip()
    if not line or line[0] == "#":
      continue
    fields = line.split()
    opts[fields[0]] = [fields[1], ' ' . join(fields[2:]) if len(fields) > 2 \
      else ""]

  binaries = [key for key in opts if opts[key][0].lower() == "binary" and \
              opts[key][1] == ""]

  for program in binaries:
    path = lookForProgram(program)
    if path != None:
      opts[program][1] = path
    else:
      sys.exit("ERROR: Impossible to find the program " + program)

  for iFile in [opts[key][1] for key in opts if opts[key][0].lower() == \
    "files" or opts[key][0].lower() == "binary"]:
    if not lookForProgram(iFile):
      sys.exit("ERROR: Impossible to find the file " + iFile)

  for iDirect in [opts[key][1] for key in opts if opts[key][0].lower() == \
    "directory"]:
    if not lookForDirectory(iDirect):
      sys.exit("ERROR: Impossible to access to the directory " + iDirect)

  for key in opts:
    opts[key] = opts[key][1]
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def ask(string, validVals, default = -1):
  '''
  Asks for a keyborad answer
  '''
  answer, values = None, []
  for i in range(len(validVals)):
    values.append(validVals[i].lower() if i != default else validVals[i].upper())

  while answer not in [value.lower() for value in values]:
    answer = raw_input("%s [%s]: " % (string, ', ' . join(map(str, values))))
    if answer == "" and default != -1: answer = values[default].lower()
    else: answer = answer.lower()

  return answer
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def ask_options(string, default = "", repeat = True):
  '''
  Asks for a keyborad answer
  '''
  answer = None

  if default != "":
    answer = raw_input("%s [%s]: " % (string, default))
    if answer == "": return default

  while True:
    if answer != None:
      if not repeat: break
      yes = raw_input("Is it correct: \"%s\"? [Y, n]: " % answer)
      if yes == "" or yes.lower() == "y": break
    answer = raw_input("%s: " % string)

  return answer
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def ask_directory(string, current = True, create = True):

  while True:
    answer = raw_input("%s: " % string)
    if answer != "" and lookForDirectory(answer, create):
      return answer
    elif answer == "" and not current:
      return ""
    elif answer == "" and lookForDirectory(".", create):
      return "."
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def ask_filename(string, default = None):

  while True:
    if default: answer = raw_input("%s [%s]: " % (string, default))
    else: answer = raw_input("%s: " % string)
    if answer == "" and default: answer = default
    if answer != "" and lookForFile(answer): return answer
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def check_date(date):
  """ Check a date structure, try to guess how it is composed and then return it
      following the MySQL scheme
  """

  if not date:
    return ""

  splitter = ""
  if date.find("/") != -1:   splitter = "/"
  elif date.find("-") != -1: splitter = "-"
  if not splitter:
    return ""

  fields = date.split(splitter)
  if len(fields) != 3:
    return ""

  if len(fields[0]) == 4:
    return ("%s-%s-%s") %(fields[0], fields[1], fields[2])
  if len(fields[2]) == 4:
    return ("%s-%s-%s") %(fields[2], fields[1], fields[0])
  return ""
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def print_proteomes(proteomes, phylome = None):

  print ("%s") % ("-" * 155)
  print ("| %-10s | %-40s | %-10s | %-40s | %-18s | %-18s |") % \
    ("DATE".center(10), "SPECIES".center(40), "PROTEOME".center(10),
    "SOURCE".center(40), "LONGEST ISOFORMS".center(18), "ISOFORMS".center(18))
  print ("%s") % ("-" * 155)

  for p in sorted(proteomes):
    species = p[3] if len(p[3]) < 41 else ("%s ...") % (p[3][:36])
    source = ""
    if p[4]:
      source = p[4] if len(p[4]) < 41 else ("%s ...") % (p[4][:36])
    print ("| %-10s | %-40s | %-10s | %-40s | %-18s | %-18s |") % (p[5],
      species, (("%s.%s") % (p[1], p[2])).center(10), source.center(40),
      p[-2].center(18), p[-1].center(18))
  print ("%s\n| Proteomes:        \t%d\n%s") % (("-" * 155), len(proteomes),
    ("-" * 155))

  if phylome:
    print ("| Seed Proteome:    \t%s") % (phylome["seed_proteome"])
    print ("| Seed Species:     \t%s") % (phylome["seed_species"])
    print ("| Phylome Name:     \t%s") % (phylome["name"])
    print ("| Longest isoforms: \t%d") % (phylome["longest"])
    print ("%s") % ("-" * 155)
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def print_phylomes(phylomes):

  print ("%s") % ("-" * 126)
  print ("| %s | %s | %s | %s | %s |") % ("ID".center(6), "NAME".center(71),\
    "PROTEOME".center(10), "DATE".center(10), "RESPONSIBLE".center(13))
  print ("%s") % ("-" * 126)

  for id, i in phylomes.iteritems():
    resp = i["responsible"] if i["responsible"] else ""
    print ("| %s | %s | %s | %s | %s |") % (str(id).center(6), \
      i["name"].ljust(71), i["seed_proteome"].center(10),
      str(i["date"]).center(10), resp.center(13))
  print ("%s") % ("-" * 126)
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def print_species(species):

  print ("%s") % ("-" * 120)
  print ("| %s | %s | %s |") % ("CODE".center(10), "TAXID".center(9), \
    "SPECIES".center(91))
  print ("%s") % ("-" * 120)

  for id, i in sorted(species.iteritems()):
    print ("| %s | %s | %s |") % (i["code"].center(10), str(i["taxid"]).\
      ljust(9), i["name"].ljust(91))
  print ("%s") % ("-" * 120)
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def get_homologs_seqs(file):
  """ Given an input file, get all sequences names from it """
  return [line[1:].strip() for line in open(file, "rU") if line[0] == ">"]

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def read_phylip_alignment(file):


  ## Update: Read alignment, if alignment is not in phylip format, convert it
  alg = {}
  alignment = map(strip, open(file, "rU").readlines())
  try:
    alg["number"], alg["len"] = map(int, alignment[0].split())

  ## If something goes wrong, try to solve it
  except:
    try:
      pipe = sp.Popen("which readal", shell = True, stdout = sp.PIPE)
    except OSError, e:
      sys.exit("ERROR: Impossible to find 'trimal'")
    bin = pipe.stdout.readline().strip()
    if not bin:
      sys.exit("ERROR: Impossible to find 'trimal'")
    ## Convert input alignment to phylip format
    try:
      pipe = sp.Popen(("%s -phylip -in %s -out %s") % (bin, file, file), \
        shell = True)
    except OSError, e:
      sys.exit("ERROR: 'readal' execution fail")
    if pipe.wait() != 0:
      sys.exit("ERROR:  'readal' execution fail")

    ## Make again same operation
    alignment = map(strip, open(file, "rU").readlines())
    try:
      alg["number"], alg["len"] = map(int, alignment[0].split())
    except:
      print ("ERROR: Handling file '%s'") % (file)
      raise
    else:
      cFile = os.path.split(file)[1]
      print ("\rWARNING: '%s' converted to PHYLIP format") % (cFile),

  for pos in range(alg["number"]):
    name, seq = alignment[pos + 1].split()
    alg.setdefault("seqs", []).append(name)
    alg.setdefault(pos, {}).setdefault("name", name)
    alg.setdefault(pos, {}).setdefault("seq", []).append(seq)

  pos = 0
  for line in alignment[alg["number"] + 1:]:
    if not line:
      continue
    alg[pos]["seq"].append(line)
    pos += 1
    if pos == alg["number"]:
      pos = 0

  for ps in range(alg["number"]):
    ln = sum([len(alg[ps]["seq"][frag]) for frag in range(len(alg[ps]["seq"]))])
    if ln != alg["len"]:
      raise NameError("Unexpected sequence length")

  return alg
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
def write_alignment(alignment):

  alg = ""
  for pos in range(alignment["number"]):
    alg += (">%s\\n") % alignment[pos]["name"]
    for frag in range(len(alignment[pos]["seq"])):
      alg += ("%s\\n") % alignment[pos]["seq"][frag]
    alg += "\\n"

  return alg
### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****

def format_time(total_time):

  days, remainder = divmod(total_time, 86400)
  hours, remainder = divmod(total_time, 3600)
  minutes, seconds = divmod(remainder, 60)
  return ("%dd:%02dh:%02dm:%02ds") % (days, hours, minutes, seconds)

### ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ****
