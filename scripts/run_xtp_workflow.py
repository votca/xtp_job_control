from toil.common import Toil
from toil.job import Job
from xtp_job_control import (send_files_to_storage, xtp_workflow)
import argparse


def cli():
    """
    Create command line options
    """
    parser = argparse.ArgumentParser()
    # Add toil arguments to parsers
    Job.Runner.addToilOptions(parser)

    parser.add_argument(
        "--system", help="path to the system description file in xml", default="system.xml")
    parser.add_argument(
        "--tpr", help="path to topology file", default="topol.tpr")
    parser.add_argument(
        "--gro", help="path to the trajectory file", default="conf.gro")

    return parser.parse_args()


def main():
    options = cli()
    input_files = ['system', 'tpr', 'gro']
    with Toil(options) as toil:
        # new job
        if not toil.options.restart:
            dict_ids = send_files_to_storage(toil, options, input_files)
            toil.start(Job.wrapJobFn(xtp_workflow, options, dict_ids))
        # restart
        else:
            pass
            # toil.restart()


if __name__ == "__main__":
    main()
