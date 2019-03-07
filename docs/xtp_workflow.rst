Workflow components
===================
As mentioned in the tutorial, Noodles_ is the workflow engine used both to create
the *dependency graph* between the jobs and to run such graph. Noodles_ provides
a *python decorator* call ``schedule`` that when applied to a function or method returns
a *promise* or *future* object (see `noodles schedule`_ tutorial).

The *xtp_job_control* library, wraps the different *XTP* calculators into their
own functions decorated with ``schedule``. These *scheduled* functions can then
be organized in different workflows by injecting the output of one function
as the input of another function. For example, the `single point energy` workflow
is implemented like:

.. code-block:: python

   def dftgwbse_workflow(options: dict) -> object:

    # create results object
    results = Results({})

    # Run DFT + GWBSE
    results['dftgwbse'] = run_dftgwbse(results, options)

    # Compute partial charges
    results['partialcharges'] = run_partialcharges(
        results, options, promise=results["dftgwbse"]["system"])

    output = run(results)

In the previous example, both functions ``run_dftgwbse`` and ``run_partialcharges``
are *scheduled* functions implemented in the `xtp_workflow`_ module. ``Results``, is
a subclass of the Python dictionary extended with functionality to handle the
jobs booking.

Notice that jobs are stored as nodes in the ``results`` dictionary and also
the *promised* object ``results['dftgwbse']`` contains a *system* property that
can be passed to a *partial charges* calculator.
    
The resulting *dependency graph* in this particular case, contains two nodes, one
for each job and a edge representing the system dependency.

.. _Noodles: http://nlesc.github.io/noodles/
.. _noodles schedule: http://nlesc.github.io/noodles/sphinxdoc/html/eating.html
.. _single point energy: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/dftgwbse.py
.. _xtp_workflow: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/xtp_workflow.py

runner
******
The ``run`` function in the previous snippet is implemented in the runner_ module and encapsulate
the noodles details. Noodles_ offers a different variety of runner for different architectures
and purposes (see runners_). Currently, the *xtp_job_control* library use a parallel multithread
runner with an sqlite_ interface for storing the jobs metadata.

.. _runner: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/runner.py
.. _runners: http://nlesc.github.io/noodles/sphinxdoc/html/development.html#module-noodles.run.scheduler
.. _sqlite: https://www.sqlite.org/index.html
