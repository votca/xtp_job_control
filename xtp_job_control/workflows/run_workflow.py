"""Module containing the command line interface."""

import argparse

from ..input import validate_input
from ..results import Options
from .dftgwbse import dftgwbse_workflow
from .kmc import kmc_workflow
from .xtp_workflow import initial_config, recursively_create_path

available_workflows = {
    'kmc': kmc_workflow, 'dftgwbse': dftgwbse_workflow}


def cli():
    """Create command line options."""
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
    """Run the workflow."""
    options = cli()
    run_workflow(options)


def run_workflow(options: dict):
    """Workflow to run a complete xtp ssimulation using `options`."""
    # validate_input
    input_dict = recursively_create_path(
        validate_input(options['input_file']))

    # Merge inputs
    options.update(input_dict)
    # run workflow
    molecule = options["molecule"]
    if molecule.is_file():
        run_single_molecule(options)
    else:
        for mol in molecule.glob("*xyz"):
            options["molecule"] = mol
            run_single_molecule(options)


def run_single_molecule(options: dict):
    """Run the workflow specified by the user for a single molecule."""
    # Setup environment to run xtp
    options = Options(initial_config(options))

    # Run the given workflow
    print("running workflow: ", options.workflow)
    fun = available_workflows[options.workflow]
    fun(options)
