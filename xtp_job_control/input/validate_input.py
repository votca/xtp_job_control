from .schemas import (schema_transport, schema_kmc, schema_dftgwbse)
from schema import SchemaError
from typing import Dict
import yaml


# available schemas
schema_simulations = {
    'transport': schema_transport, 'kmc': schema_kmc, 'dftgwbse': schema_dftgwbse}


def validate_input(input_file: str) -> Dict:
    """
    Read the input file in YAML format, validate it again the schema
    of `workflow` and return a nested dictionary with the input.
    """
    with open(input_file, 'r') as f:
        dict_input = yaml.load(f.read())

    try:
        schema = schema_simulations[dict_input['workflow']]
        return schema.validate(dict_input)

    except SchemaError as e:
        msg = "There was an error in the input provided:\n{}".format(e)
        raise RuntimeError(msg)
