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

    # read command line args
    args = parser.parse_args()
    opts = ['input', 'workdir']

    return {key: getattr(args, key) for key in opts}


def main():
    options = cli()
    xtp_workflow(options)


if __name__ == "__main__":
    main()
