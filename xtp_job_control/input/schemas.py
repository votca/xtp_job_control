"""Schemas to validate the user input."""
__all__ = ["schema_dftgwbse", "schema_kmc", "schema_transport"]

from os.path import exists
from schema import (And, Optional, Schema, Use)


# "options to change from default templates
schema_votca_calculators_options = Schema({

    Optional("bsecoupling", default={}): dict,

    Optional("dftgwbse", default={"dftpackage": "user_input.xml", "gwbse_engine":
                                  {"gwbse_options": "gwbse.xml"}}): dict,

    Optional(
        "eqm", default={
            "dftpackage": "xtpdft.xml",
            "esp_options": "esp2multipole.xml"}): dict,

    Optional("esp2multipole", default={}): dict,

    Optional("gen_cube", default={}): dict,

    Optional("iqm", default={}): dict,

    Optional("jobwriter", default={}): dict,

    Optional("jobwriter_qmmm", default={}): dict,

    Optional("kmclifetime", default={}): dict,

    Optional("kmcmultiple", default={}): dict,

    Optional("mbgft_pair", default={}): dict,

    Optional("mbgft_qmmm", default={}): dict,

    Optional("neighborlist", default={}): dict,

    Optional("orca", default={}): dict,

    Optional("partialcharges", default={}): dict,

    Optional("qmmm", default={}): dict,

    Optional("threads", default=1): int,

    Optional("xqmultipole", default={}): dict,

    Optional("xtpdft", default={}): dict,

    Optional("xtpdft_pair", default={}): dict,

    Optional("xtpdft_qmmm", default={}): dict,
})


CALCULATORS_DEFAULTS = schema_votca_calculators_options.validate({})


schema_kmc = Schema({
    # Name of the workflow to run
    "workflow": And(str, Use(str.lower),
                    lambda s: s in ("kmc")),

    # path to the VOTCASHARE folder
    "path_votcashare": exists,

    "state": exists,

    Optional("lifetimes_file", default="lifetimes.xml"): exists,

    # Change_Options options from template
    Optional("votca_calculators_options", default=CALCULATORS_DEFAULTS): schema_votca_calculators_options

})

schema_dftgwbse = Schema({

    # Name of the workflow to run
    "workflow": And(
        str, Use(str.lower), lambda s: s in ("dftgwbse")),

    # DFT engine
    Optional("package", default="xtpdft"): str,

    # Type of calculation
    Optional("mode", default="energy"): And(
        str, Use(str.lower), lambda s: s in ("energy", "optimize")),

    # Molecular geometry:
    "molecule": exists,

    # Executable
    Optional("executable", default="/path/to/package"): str,

    # Functional
    Optional("functional", default="XC_HYB_GGA_XC_PBEH"): str,

    # Basis
    Optional("basisset", default="ubecppol"): str,
    Optional("auxbasisset", default="aux-ubecppol"): str,

    # path to the VOTCASHARE folder
    Optional("path_votcashare", default="/usr/local/share/votca"): exists,

    # Change_Options options from template
    Optional("votca_calculators_options", default=CALCULATORS_DEFAULTS): schema_votca_calculators_options
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
    Optional("xqmultipole_jobs", default=[]): list,

    # number of eqm jobs to run. If [] run all
    Optional("eqm_jobs", default=[]): list,

    # number of iqm jobs to run. If null run all
    Optional("iqm_jobs", default=[]): list,

    # Change_Options options from template
    Optional("votca_calculators_options", default=CALCULATORS_DEFAULTS): schema_votca_calculators_options
})
