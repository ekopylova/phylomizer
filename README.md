# Phylomizer

**Phylomizer** is an automated phylogenetics pipeline which aims to reproduce the three main step follow by traditional phylogeneticists. These steps, as shown in the image, are 1) Homology search, 2) Multiple Sequence Alignment Reconstruction, and 3) Phylogenetic Tree reconstruction.

**Phylomizer** can be used to reconstruct a single gene tree. However, it aims to assist on the reconstruction of large collection of phylogenies. In fact, **Phylomizer** has been used in [phylomedb.org](http://phylomedb.org) to generate more than 5.6 million phylogenetic trees, as January, 2016.

<img src="https://github.com/Gabaldonlab/phylomizer/blob/master/docs/pipeline.2016.png" width="400">

## Using **Phylomizer** from the command-line in UNIX environments.

There are two scripts included in the **Phylomizer** package. Please be ware that **by default** the multiple sequence alignment used for phylogenetic tree reconstruction is generated as follow: 1) three different alignment programs are used to generate alignments in forward and reverse sequences orientation; 2) these 6 alignments are combined into a consensus one using M-Coffee; 3) final alignment is generated by trimAl after removing those columns from the consensus alignments with a low consistency score e.g. no column has been seed in any of the 6 alignment used to generate the consensus one.

**phylomizer.py** allows the user to perform the whole phylogenetic pipeline, specific steps e.g. homology searches, or specific combinations e.g. homology searches + multiple sequence alignment reconstruction 

```bash
## Just reconstructing the best fitting evoluionary model for a ML tree.

$> ./source/phylomizer.py -i input_msa_alignment --steps trees -c config_file -o output_folder
```

Here we have access to all available options which are shared (most of them) by both scripts.
```bash
## Check input options for phylomizer.py - assuming we are at the ROOT directory of the package

$> ./source/phylomizer.py -h

optional arguments:
  -h, --help            show this help message and exit
  -i INFILE, --in INFILE
                        Input file containing the query sequence/s
  --min_seqs MINSEQS    Set the minimum sequences number to reconstruct an alignment/tree.
                        This parameter overwrites whatever is set on the config file.
  --max_hits MAXHITS    Set the maximum accepted homology hits after filtering for e-value/coverage.
                        This parameter overwrites whatever is set on the config file.
  --steps [{all,homology,alignments,trees} [{all,homology,alignments,trees} ...]]
                        Set which step/s should be performed by the script
  -d DBFILE, --db DBFILE
                        Input file containing the target sequence database
  --cds CDSFILE         Input file containing CDS corresponding to input protein seqs
  -c CONFIGFILE, --config CONFIGFILE
                        Input configuration file
  -o OUTFOLDER, --out OUTFOLDER
                        Output folder where all generated files will be dumped
  -p PREFIX, --prefix PREFIX
                        Set the prefix for all output files generated by the pipeline
  -r, --replace         Over-write any previously generated file
  --version             show program\'s version number and exit
  -v {0,1,2,logfile,none,stderr}, --verbose {0,1,2,logfile,none,stderr}
                        Set how information should be dumped. It could be used levels or tags
                        It overwrites whatever is set on the configuration file.
```

**pipeline.py** aims to perform the three main steps implemented in the pipeline following the configuration set on the configuration file.

```bash
## Given a single input sequence, retrieve its homologous sequences from a predefined DB using e.g. BLAST, reconstruct the
## alignment for this set of sequences, and then the best fitting ML tree.

$> ./source/pipeline.py -i input_single_sequence_file -d input_DB_file -c config_file -o output_folder
```

## Configuration File.

[Configuration File example](config/config.pipeline). This file includes all currently supported programs and the standard parameters used with all of them. Additional parameters and execution modes e.g. MPI call, can be set editing this file. 

[PhylomeDB Phylomizer Configuration file KMM](config/PhylomeDB Configuration - KMM). It uses 3 different aligner (KAlign, Muscle, and Mafft) to generate a consensus alignment of **3 aligners x 2 sequences orientation** using M-Coffee. Later on this consensus alignment is processed by trimAl to remove low consistency columns. The use of KAlign instead of DiAlign-TX considerably speeds up the whole alignment generation process with a sligthly degratation on performance. Therefore, this configuration is the **default** one in PhylomeDB, as January 2016.

[PhylomeDB Phylomizer Configuration file DMM](config/PhylomeDB Configuration - KMM). It uses 3 different aligner (DiAlign-TX, Muscle, and Mafft) to generate a consensus alignment of **3 aligners x 2 sequences orientation** using M-Coffee. Later on this consensus alignment is processed by trimAl to remove low consistency columns. 

## Citation.






