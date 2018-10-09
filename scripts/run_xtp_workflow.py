from xtp_job_control import xtp_workflow
import argparse


def cli():
    """
    Create command line options
    """
    parser = argparse.ArgumentParser()
    # Add toil arguments to parsers

    parser.add_argument(
        "--votcashare", help="Path to votca share folder", required=True)
    parser.add_argument(
        "--system", help="path to the system description file in xml",
        default="system.xml")
    parser.add_argument(
        "--tpr", help="path to topology file", default="topol.tpr")
    parser.add_argument(
        "--gro", help="path to the trajectory file", default="conf.gro")

    parser.add_argument(
        "--workdir", help=("Work directory"), default='.')

    # read command line args
    args = parser.parse_args()
    opts = ['votcashare', 'system', 'tpr', 'gro', 'workdir']

    return {key: getattr(args, key) for key in opts}


def main():
    options = cli()
    xtp_workflow(options)


if __name__ == "__main__":
    main()
