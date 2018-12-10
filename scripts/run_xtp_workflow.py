#!/usr/bin/env python

from xtp_job_control import xtp_workflow
import argparse


def cli():
    """
    Create command line options
    """
    parser = argparse.ArgumentParser()
    # Add toil arguments to parsers

    parser.add_argument(
        "--input", help="Path to the input file (YAML format)", required=True)

    parser.add_argument(
        "--workdir", help="Working directory", default='.')

    # read command line args
    args = parser.parse_args()

    return {'input_file': args.input, 'workdir': args.workdir}


def main():
    options = cli()
    xtp_workflow(options)


if __name__ == "__main__":
    main()
