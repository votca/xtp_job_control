********
Tutorial
********

The *xtp_job_control* library contains a set of  predifined workflows_ that workout
of the box. But a user may also need further capabilities over the xtp functionality,
for those cases the *xtp_job_control* allows a user to extend or create some missing
functionality that can be integrated with the predefined workflows.

.. _workflows:


Available Workflows
===================
The following family of workflows are defined in *xtp_job_control*:

 * dftgwbse_
 * transport_
 * kmc_

dftgwbse
********
The dftgwbse_ workflow performs either a point energy calculation (see energy_ input example) or
geometry optimization (see optimization_ input example) using the `GW-BSE`_ method, check the **GW-BSE**
entry of the manual_ for furtner information.

Transport
*********
The transport_ workflow contains several steps to compute charge transport networks, using a combined
coarse-grained and stochastic approach (see `input transport`_ example). For further reading, see secion *2.10* of the manual_.

kmc
***
The kmc_ worklow performs a hopping simulation of charge carriers using a `kinetic Monte Carlo`_ approach (see `input kmc` example).
For further information, see Chapter *2* of the manual_.

.. _dftgwbse: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/dftgwbse.py
.. _energy: https://github.com/votca/xtp_job_control/blob/master/tests/DFT_GWBSE/dftgwbse_CH4/input_dft_gwbse_CH4.yml
.. _energies: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/energies.py
.. _GW-BSE: https://en.wikipedia.org/wiki/GW_approximation
.. _input kmc: https://github.com/votca/xtp_job_control/blob/master/tests/KMC/input_kmc.yml
.. _input transport: https://github.com/votca/xtp_job_control/blob/master/tests/Methane/input_transport.yml
.. _kinetic monte Carlo: https://en.wikipedia.org/wiki/Kinetic_Monte_Carlo
.. _kmc: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/kmc.py
.. _manual: http://doc.votca.org/xtp-manual.pdf
.. _optimization: https://github.com/votca/xtp_job_control/blob/master/tests/DFT_GWBSE/dftgwbse_CO_geoopt/input_CO_geoopt.yml
.. _transport: https://github.com/votca/xtp_job_control/blob/master/tests/Methane/input_transport.yml


Running a workflow
==================

A workflow is run by executing the following command in the terminal:

``run_xtp_workflow.py --input tests/DFT_GWBSE/dftgwbse_CH4/input_dft_gwbse_CH4.yml``

Where **run_xtp_workflow.py** is the python script that read, process and run the workflow, and the input is a file
in yaml_ format. 

.. _yaml: https://pyyaml.org/wiki/PyYAMLDocumentation

After the command finishes it returns another yaml file called result_<workflow>_<time-stamp>.yml containing a
summary of the workflow results and a file called ``xtp.log`` with the standard output and error returned by
the *Votca-XTP* calculators.

How it works
************
First, the library scan the input and checks its validity (using a set of predifined schemas_), then a `dependency graph_` is
built between the different jobs involved in the workflow. This graph allows to run in parallel those jobs that do not
dependent on each other, while creating explicit dependencies between jobs that need to run in a sequential mode, injecting
the ouput of one job as input of the next one. Finally, the jobs are running in different folders while the dependecies between
them are automatically track. 

Both the construction and execution of the dependency graph is carried out by the Noodles_ library.
When the ``run_xtp_workflow.py`` command is invoked,
Noodles_ traverses the graph of job dependencies and checks against its internal database for a reference to the job results,
if such reference does not exist the job is executed and the resulting output metainformation is stored in the database. 

If the execution of the workflow is stopped by the user or fails for technical reasons, the generated database with metadata
can be used to restart the workflows. _Noodles will walk through the dependencies tree in the same way as when started from scratch,
but will query the database for already existing results and execute only the tasks that were not yet successfully completed.

.. _schemas: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/input/schemas.py
.. _Noodles: http://nlesc.github.io/noodles/


Votca calculators options
=========================
The arguments and default values for running simulations with *Votca-XTP* are define in different xml_ files, leaving
at the *VOTCASHARE* folder. When an *XTP* command is invoked, *Votca-XTP* reads from these *xml* files the available values.
Since, *xml* files can have nested *xml* files it is a non-trivial task to setup correctly the simulation values for a given simulation.

In order to improved the aforemention situation, the *xtp_job_control* library allows the users to create a section
called **votca_calculators_options** in the input file. Every subsection on it, corresponds to an xml file and subsequently
subsections are values that the user wish to change. For example, see the next snippet taken from
the input example for a `single point energy`_ calculation:
.. code-block:: yaml

   votca_calculators_options:
     dftgwbse:
       dftpackage:
         xtpdft.xml

     xtpdft:
       threads: 1

It saids that in the *dftgwbse* xml option file, the argument ``dftpackage`` must be set equal to *xtpdft.xml*. While
in the *xtpdft* xml option file, the number of ``threads`` should be set to 1.

.. _single point energy: https://github.com/votca/xtp_job_control/blob/master/tests/DFT_GWBSE/dftgwbse_CH4/input_dft_gwbse_CH4.yml

How it works
************
Before the jobs are executed, all the Option files in the *VOTCASHARE* folder are copy to a temporary folder. These temporary
files are combined with **votca_calculators_options** provided by the users, generating a new set of files containing
the options to call the *Votca-XTP* functionality.

.. _xml: https://en.wikipedia.org/wiki/XML
