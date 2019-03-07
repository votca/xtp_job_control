__all__ = ["schema_dftgwbse", "schema_kmc", "schema_transport"]

from os.path import exists
from schema import (And, Optional, Schema, Use)
from typing import (Dict, List)


# "options to change from default templates
schema_votca_calculators_options = Schema({

    Optional("bsecoupling", default={}): Dict,

    Optional("dftgwbse", default={"dftpackage": "xtpdft.xml"}): Dict,

    Optional(
        "eqm", default={
            "gwbse_options": "mbgft.xml", "dftpackage": "xtpdft.xml",
            "esp_options": "esp2multipole.xml"}): Dict,

    Optional("esp2multipole", default={}): Dict,

    Optional("gen_cube", default={}): Dict,

    Optional("iqm", default={}): Dict,

    Optional("jobwriter", default={}): Dict,

    Optional("jobwriter_qmmm", default={}): Dict,

    Optional("kmclifetime", default={}): Dict,

    Optional("kmcmultiple", default={}): Dict,

    Optional("mbgft", default={}): Dict,

    Optional("mbgft_pair", default={}): Dict,

    Optional("mbgft_qmmm", default={}): Dict,

    Optional("neighborlist", default={}): Dict,

    Optional("partialcharges", default={}): Dict,

    Optional("qmmm", default={}): Dict,

    Optional("xqmultipole", default={}): Dict,

    Optional("xtpdft", default={}): Dict,

    Optional("xtpdft_pair", default={}): Dict,

    Optional("xtpdft_qmmm", default={}): Dict,
})


schema_kmc = Schema({
    # Name of the workflow to run
    "workflow": And(str, Use(str.lower),
                    lambda s: s in ("kmc")),

    # path to the VOTCASHARE folder
    "path_votcashare": exists,

    "state": exists,

    Optional("lifetimes_file", default="lifetimes.xml"): exists,

    # Change_Options options from template
    Optional("votca_calculators_options", default={}): schema_votca_calculators_options

})

schema_dftgwbse = Schema({

    # Name of the workflow to run
    "workflow": And(
        str, Use(str.lower), lambda s: s in ("dftgwbse")),

    # Type of calculation
    Optional("mode", default="energy"): And(
        str, Use(str.lower), lambda s: s in ("energy", "optimize")),

    # Molecular geometry:
    "molecule": exists,

    # Functional
    Optional("functional", default="XC_HYB_GGA_XC_PBEH"): str,

    # Basis
    Optional("dftbasis", default="ubecppol"): str,
    Optional("gwbasis", default="aux-ubecppol"): str,

    # path to the VOTCASHARE folder
    "path_votcashare": exists,

    # Change_Options options from template
    Optional("votca_calculators_options", default={}): schema_votca_calculators_options
})


schema_transport = Schema({

    # Name of the workflow to run
    "workflow": And(str, Use(str.lower),
                    lambda s: s in ("transport")),

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

    # Change_Options options from template
    Optional("votca_calculators_options", default={}): schema_votca_calculators_options
})
