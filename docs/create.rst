
Creating Your Own Workflow
==========================
if the available workflows do not provided simulation that you want to perform,
you can create your own worklow by glueing together the available functions
at the `xtp_workflow`_.

If non of the functions at the `xtp_workflow`_ modules satifies your needs, you
can create your own function using the :func:`xtp_job_control.workflows.workflow_components.call_xtp_cmd`
and :func:`xtp_job_control.workflows.workflow_components.call_xtp_cmd`. The following code snippet,
ilustrates the creation of a call to the ``xtp_map`` command using a promised *system* argument provided
by another job called *job_system*.

.. code-block:: python

    results = Results({})

    # Other jobs executed here
    ...

   args = create_promise_command(
       "xtp_map -t {} -c {} -s {} -f {}",
       topology, trajectory,
       results['job_system']['system'], path_state)

   results['job_state'] = call_xtp_cmd(args, workdir, expected_output={'state': 'state.sql'})

the ``expected_output`` argument in the function, search for output files created by the command.
In the current case, the ``xtp_map`` command generates a file called *state.sql*. The ouput
files can be access by other jobs using the name provided in the dictionary. For example,
the *state.sql* is available using the following notation:

.. code-block:: python

    state_file = results['job_state']['state']


.. _xtp_workflow: https://github.com/votca/xtp_job_control/blob/master/xtp_job_control/workflows/xtp_workflow.py


Command line wrappers
*********************
The following functions create an schedule call to a *Votca-XTP* command.

.. autofunction:: xtp_job_control.workflows.workflow_components.call_xtp_cmd

.. autofunction:: xtp_job_control.workflows.workflow_components.create_promise_command
