# BMH MinION Basecaller Workflow

Internal BMH/BFSSI script to basecall, demultiplex, then zip up a MinION run in preparation for upload to the 
BMH Genomics Portal.

Pipeline overview:
1) Samplesheet validation
2) Basecalling of FAST5 files generated with MinKNOW with [Guppy GPU](https://community.nanoporetech.com/protocols/Guppy-protocol/v/gpb_2003_v1_revo_14dec2018/linux-guppy)
3) Demultiplexing with [qcat](https://github.com/nanoporetech/qcat)
4) Compression with [7-Zip](https://www.7-zip.org/)

### SampleSheet overview
The samplesheet must be an **.xlsx** file and should look something like the following:

| Sample_ID       | Sample_Name  | Barcode   | Run_ID           | Run_Protocol               | Instrument_ID | Sequencing_Kit | Flowcell_Type | Project_ID              | Read_Type | User        |
|-----------------|--------------|-----------|------------------|----------------------------|---------------|----------------|---------------|-------------------------|-----------|-------------|
| MIN-2019-000021 | 2015026      | barcode07 | 20191118_2053_1D | Rapid Barcoding Sequencing | MN26570       | SQL-RBK004     | FLO-MIN106    | Chicken_Nugget_Project  | 1D        | Dussault, F. |
| MIN-2019-000022 | 2018001      | barcode08 | 20191118_2053_1D | Rapid Barcoding Sequencing | MN26570       | SQL-RBK004     | FLO-MIN106    | Chicken_Nugget_Project  | 1D        | Dussault, F. |
| MIN-2019-000023 | D-Prime      | barcode09 | 20191118_2053_1D | Rapid Barcoding Sequencing | MN26570       | SQL-RBK004     | FLO-MIN106    | Chicken_Nugget_Project  | 1D        | Dussault, F. |
| MIN-2019-000024 | 1185-Ampure  | barcode10 | 20191118_2053_1D | Rapid Barcoding Sequencing | MN26570       | SQL-RBK004     | FLO-MIN106    | Chicken_Nugget_Project  | 1D        | Dussault, F. |
| MIN-2019-000025 | 1185 -Zymo   | barcode11 | 20191118_2053_1D | Rapid Barcoding Sequencing | MN26570       | SQL-RBK004     | FLO-MIN106    | Chicken_Nugget_Project  | 1D        | Dussault, F. |
| MIN-2019-000026 | 1185-Spri    | barcode12 | 20191118_2053_1D | Rapid Barcoding Sequencing | MN26570       | SQL-RBK004     | FLO-MIN106    | Chicken_Nugget_Project  | 1D        | Dussault, F. |

##### Important notes on SampleSheet:
- All columns are required, must be populated, and must be named as displayed above.

- Entries in the Sample_ID column must follow the `MIN-YYYY-XXXXXX` nomenclature.

- Entries in the Project_ID column **cannot contain spaces or special characters**.

- Upon completion of the pipeline, the input samplesheet will be renamed **SampleSheet.xlsx**. 
This is required for upload to the portal.

### Installation instructions

```
git clone https://github.com/bfssi-forest-dussault/BMH_MinION_Basecaller.git
cd BMH_MinION_Basecaller
conda create -f environment.yml
conda activate BMH_MinION_Basecaller
```