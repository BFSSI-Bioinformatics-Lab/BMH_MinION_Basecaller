#!/usr/bin/env python

import click
import shutil
from pathlib import Path
from subprocess import Popen
import pandas as pd


def validate_minion_project_id(value: str):
    if ' ' in value:
        print(f"ERROR: Found whitespace character in Project_ID column with value '{value}'")
        return False
    return True


def validate_minion_sample_id(value: str, length: int = 15):
    """
      Strict validation of BMH MinION Sample ID
      :param value: sample_id
      :param length: expected length of string
      """
    components = value.split("-")

    if len(value) != length:
        print(f"MinION Sample ID '{value}' does not meet the expected length of 15 characters. "
              f"MinION Sample ID must be in the following format: 'MIN-2020-000001'")
    if len(components) != 3:
        print(f"MinION Sample ID '{value}' does not appear to meet expected format. "
              f"MinION Sample ID must be in the following format: 'BMH-2018-000001'")
    elif components[0] != 'MIN':
        print(
            f"TEXT component of MinION Sample ID ('{value}') does not equal expected 'MIN'")
    elif not components[1].isdigit() or len(components[1]) != 4:
        print(
            f"YEAR component of MinION Sample ID ('{value}') does not equal expected 'YYYY' format")
    elif not components[2].isdigit() or len(components[2]) != 6:
        print(
            f"ID component of MinION Sample ID ('{value}') does not equal expected 'XXXXXX' format")
    else:
        return True
    return False


def run_subprocess(cmd):
    p = Popen(cmd, shell=True)
    p.wait()


def validate_samplesheet(samplesheet: Path):
    expected_columns = [
        'Sample_ID',
        'Sample_Name',
        'Barcode',
        'Run_ID',
        'Run_Protocol',
        'Instrument_ID',
        'Sequencing_Kit',
        'Flowcell_Type',
        'Project_ID',
        'Read_Type',
        'User'
    ]

    samplesheet_valid = True
    df = pd.read_excel(samplesheet, index_col=None)

    while samplesheet_valid:
        for col in expected_columns:
            if col not in list(df.columns):
                print(f"ERROR: Could not find expected column '{col}' in input samplesheet!")
                samplesheet_valid = False

        for key, val in df.iterrows():
            samplesheet_valid = validate_minion_sample_id(val['Sample_ID'])
            samplesheet_valid = validate_minion_project_id(val['Project_ID'])
        break

    if not samplesheet_valid:
        print('ERROR: Quitting program due to validation error(s) in SampleSheet.')
        quit()


def call_guppy(fast5_dir, output_dir, flowcell, kit):
    output_dir = output_dir / 'guppy_basecalling'
    output_dir.mkdir(exist_ok=True, parents=True)
    print(f"Running guppy on {fast5_dir} and storing output in {output_dir}")
    print(f"Flowcell: {flowcell}")
    print(f"Kit: {kit}")
    cmd = f"guppy_basecaller -i {fast5_dir} -s {output_dir} --device cuda:0 --flowcell {flowcell} --kit {kit} --trim_barcodes --recursive --chunk_size 1700 --gpu_runners_per_device 4"
    print(cmd)
    run_subprocess(cmd)
    return output_dir


def call_cat(fastq_dir, output_dir):
    """
    Concatenates input FASTQ files into a single FASTQ. Output from this command is fed to qcat for demultiplexing.
    """
    print(f"Detected {len(list(fastq_dir.glob('*.fastq')))} FASTQ files in {fastq_dir}")
    outfile = output_dir / (output_dir.name + '_combined.fastq')
    print(f"Concatenating all FASTQ files in {fastq_dir} and storing contents in {outfile}")
    cmd = f"cat {fastq_dir}/*.fastq > {outfile}"
    print(cmd)
    run_subprocess(cmd)
    return outfile


def call_qcat(fastq, output_dir):
    """
    Demultiplexes FASTQ file according to automatically detected barcodes. Trims the barcodes.
    """
    output_dir = output_dir / 'qcat_demultiplexing'
    output_dir.mkdir(exist_ok=True, parents=True)
    print(f"Demultiplexing {fastq.name} with qcat and storing output in {output_dir}")
    cmd = f"qcat -f {fastq} -b {output_dir} --trim --tsv --kit Auto > {output_dir}/qcat_log.txt"
    print(cmd)
    run_subprocess(cmd)
    return output_dir


def call_7zip(output_dir: Path):
    """
    Runs 7zip on the output directory
    """
    print(f"Compressing all files in {output_dir}")
    outfile = output_dir.parent / output_dir.name
    cmd = f"7z a {outfile} {output_dir}/*"
    print(cmd)
    run_subprocess(cmd)
    return outfile


def call_pigz(fastq_dir):
    """
    Gzips all fastq files in a given directory. Used to gzip the contents of the qcat demultiplexed output folder.
    """
    print(f"Compressing all FASTQ files in {fastq_dir}")
    cmd = f"gzip {fastq_dir}/*.fastq"
    print(cmd)
    run_subprocess(cmd)
    return fastq_dir


def pipeline(input_dir: Path, output_dir: Path, samplesheet: Path, flowcell: str, kit: str,
             keep_intermediary_files: bool):
    validate_samplesheet(samplesheet=samplesheet)
    shutil.copy(str(samplesheet), str(output_dir / 'SampleSheet.xlsx'))
    fastq_dir = call_guppy(input_dir, output_dir, flowcell, kit)
    combined_fastq = call_cat(fastq_dir, output_dir)
    demultiplex_dir = call_qcat(combined_fastq, output_dir)
    call_pigz(demultiplex_dir)

    if not keep_intermediary_files:
        shutil.rmtree(fastq_dir)
        combined_fastq.unlink()

    call_7zip(output_dir)


@click.command(
    help="Wrapper script to conduct basecalling and demultiplexing on a MinION run.\nForest Dussault (forest.dussault@canada.ca). 2020/03/04.")
@click.option('-i', '--input-dir', type=click.STRING, required=True,
              help="Path to the MinION output folder containing FAST5 files (e.g. /var/lib/MinKNOW/data/20191118/MN26570/20191118_2053_1D/fast5).")
@click.option('-o', '--output-dir', type=click.STRING, required=True,
              help="Path to desired output directory for basecalled and demultiplexed files")
@click.option('-s', '--samplesheet', type=click.STRING, required=True,
              help="Path to samplesheet (.xlsx). Will automatically be copied to the output directory. Please refer to README.md for instructions on populating this file.")
@click.option('-f', '--flowcell', type=click.STRING,
              help="Flowcell type used for the MinION run. Defaults to FLO-MIN106.", default="FLO-MIN106")
@click.option('-k', '--kit', type=click.STRING, help="Kit used for the MinION run. Defaults to SQK-RBK004.",
              default="SQK-RBK004")
@click.option('--keep_intermediary_files', type=click.BOOL,
              help="Activate this flag to keep the Guppy basecalling output as well as the combined .fastq file. "
                   "Otherwise, only the qcat output will be maintained.",
              is_flag=True,
              default=False)
def cli(input_dir, output_dir, samplesheet, flowcell, kit, keep_intermediary_files):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    samplesheet = Path(samplesheet)
    print(f"Started Basecalling workflow")
    pipeline(input_dir, output_dir, samplesheet, flowcell, kit, keep_intermediary_files)
    print(f"Done! Output available in {output_dir}")


if __name__ == "__main__":
    cli()
