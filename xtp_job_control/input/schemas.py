__all__ = ["schema_simulations"]

from os.path import exists
from schema import (Optional, Schema)
from typing import (Dict, List)


# "options to change from default templates
schema_change_options = Schema({

    Optional("bsecoupling", default={}): Dict,

    Optional("eqm", default={}): Dict,

    Optional("esp2multipole", default={}): Dict,

    Optional("iqm", default={}): Dict,

    Optional("jobwriter", default={}): Dict,

    Optional("jobwriter_qmmm", default={}): Dict,

    Optional("mbgft", default={}): Dict,

    Optional("mbgft_pair", default={}): Dict,

    Optional("mbgft_qmmm", default={}): Dict,

    Optional("neighborlist", default={}): Dict,

    Optional("qmmm", default={}): Dict,

    Optional("xqmultipole", default={}): Dict,

    Optional("xtpdft", default={}): Dict,

    Optional("xtpdft_pair", default={}): Dict,

    Optional("xtpdft_qmmm", default={}): Dict,
})

# Copy files from src to dest
schema_copy_option_files = Schema({

    # Source files
    "src": List,

    # Destination
    "dst": List,
})


# Workflow input
schema_simulations = Schema({

    # Name of the workflow to run
    "workflow": str,

    # path to the VOTCASHARE folder
    "path_votcashare": exists,

    # path to the system description file in xml
    "system": exists,

    # path to topology file
    "topology": exists,

    # path to the trajectory file
    "trajectory": exists,

    # path to the folder containing the mp_files
    "mp_files": exists,

    # path to the folder containing the qc_files
    "qc_files": exists,

    # number of xqmultipole jobs to run. If [] run all
    Optional("xqmultipole_jobs", default=[]): List,

    # number of eqm jobs to run. If [] run all
    Optional("eqm_jobs", default=[]): List,

    # number of iqm jobs to run. If null run all
    Optional("iqm_jobs", default=[]): List,

    # Change options from template
    Optional("change_options", default={}): schema_change_options,

    # Copy files
    Optional("copy_option_files", default={}): schema_copy_option_files
})
