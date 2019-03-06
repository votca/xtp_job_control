Tutorial
========
The *xtp_job_control* library contains a set of  predifined workflows_ that workout
of the box. But a user may also need further capabilities over the xtp functionality,
for those cases the *xtp_job_control* allows a user to extend or create some missing
functionality that can be integrated with the predefined workflows.

.. _workflows:

Available Workflows
********************
The following family of workflows are defined in *xtp_job_control*:

 * dftgwbse_
 * transport_
 * kmc_

The dftgwbse_ workflow performs either a point energy calculation (see energy_ input example) or
geometry optimization (see optimization_ input example) using the `GW-BSE`_ method, check the **GW-BSE**
entry of the manual_ for furtner information.
The transport_ workflow contains several steps to compute charge transport networks, using a combined
coarse-grained and stochastic approach. See secion *2.10* of the manual_.

.. _dftgwbse: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/dftgwbse.py
.. _energy: https://github.com/votca/xtp_job_control/blob/master/tests/DFT_GWBSE/dftgwbse_CH4/input_dft_gwbse_CH4.yml
.. _energies: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/energies.py
.. _GW-BSE: https://en.wikipedia.org/wiki/GW_approximation
.. _kmc: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/kmc.py
.. _manual: http://doc.votca.org/xtp-manual.pdf
.. _optimization: https://github.com/votca/xtp_job_control/blob/master/tests/DFT_GWBSE/dftgwbse_CO_geoopt/input_CO_geoopt.yml
.. _transport: https://github.com/votca/xtp_job_control/blob/master/tests/Methane/input_transport.yml

Running a workflow
******************

A workflow is run by executing the following command in the terminal:

``run_xtp_workflow.py --input tests/DFT_GWBSE/dftgwbse_CH4/input_dft_gwbse_CH4.yml``

Where **run_xtp_workflow.py** is the python script that read, process and run the workflow, and the input is a file
in yaml_ format.

.. _yaml: https://pyyaml.org/wiki/PyYAMLDocumentation

Votca calculators options
*************************

Creating Your Own Workflow
**************************
