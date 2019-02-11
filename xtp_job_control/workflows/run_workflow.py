from ..input import validate_input
from .xtp_workflow import (initial_config, recursively_create_path)
from .energies import energies_workflow
from .kmc import kmc_workflow

available_workflows = {'kmc': kmc_workflow, 'energies': energies_workflow}


def run_workflow(options: dict):
    """
    Workflow to run a complete xtp ssimulation using `options`.
    """
    # validate_input
    input_dict = recursively_create_path(
        validate_input(options['input_file']))

    # Merge inputs
    options.update(input_dict)

    # Setup environment to run xtp
    options = initial_config(options)

    # Run the given workflow
    fun = available_workflows[options['workflow']]
    fun(options)