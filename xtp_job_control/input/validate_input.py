from .schemas import schema_simulations
from schema import SchemaError
from typing import Dict
import yaml


# available schemas
schema_simulations = {'simulation': schema_simulations}


def validate_input(input_file: str, workflow_name: str='simulation') -> Dict:
    """
    Read the input file in YAML format, validate it again the schema
    of `workflow_name` and return a nested dictionary with the input.
    """
    schema = schema_simulations[workflow_name]

    with open(input_file, 'r') as f:
        dict_input = yaml.load(f.read())

    try:
        return schema.validate(dict_input)

    except SchemaError as e:
        msg = "There was an error in the input provided:\n{}".format(e)
        raise RuntimeError(msg)
