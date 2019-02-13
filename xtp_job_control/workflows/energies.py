from ..results import Results
from ..runner import run
from .xtp_workflow import (
    create_promise_command, edit_system_options, distribute_xqmultipole_jobs,
    run_analyze, run_config_xqmultipole,
    run_dump, run_einternal, run_eqm, run_iqm, run_neighborlist, write_output)
from .workflow_components import call_xtp_cmd


def energies_workflow(options: dict) -> object:
    """
    Use the `options` to create a workflow to compute energies
    """
    workdir = options.scratch_dir

    # create results object
    results = Results({})

    # Adjust links in the system.xml file
    results['job_system'] = edit_system_options(results, options)

    # Step state
    # runs the mapping from MD coordinates to segments and creates .sql file
    # you can explore the created .sql file with e.g. sqlitebrowser
    path_state = workdir / "state.sql"
    args = create_promise_command(
        "xtp_map -t {} -c {} -s {} -f {}",
        options['topology'], options['trajectory'],
        results['job_system']['system'], path_state)

    # calls something like:
    # xtp_map -t MD_FILES/topol.tpr -c MD_FILES/conf.gro -s system.xml -f state.sql
    results['job_state'] = call_xtp_cmd(args, workdir, expected_output={'state': 'state.sql'})

    # step dump
    # output MD and QM mappings into extract.trajectory_md.pdb and
    # extract.trajectory_qm.pdb files
    results['job_dump'] = run_dump(results, options)

    # step neighborlist
    # Change options neighborlist
    results['job_neighborlist'] = run_neighborlist(results, options)

    # step config xqmultipole
    results['job_select_xqmultipole_jobs'] = run_config_xqmultipole(results, options)

    # Run xqmultipole jobs in parallel
    results['jobs_xqmultipole'] = distribute_xqmultipole_jobs(results, options)

    # # step einternal
    # read in reorganization energies stored in system.xml to state.sql
    results['job_einternal'] = run_einternal(results, options)

    # step eqm
    results['jobs_eqm'] = run_eqm(results, options)

    # step iqm
    results['jobs_iqm'] = run_iqm(results, options)

    # step eanalyze
    results['job_eanalyze'] = run_analyze(results, options, "eanalyze")

    # step ianalyze
    results['job_ianalyze'] = run_analyze(results, options, "ianalyze")

    # # step qmmm
    # results['job_qmmm'] = 
    # RUN the workflow
    output = run(results)
    path_output = "results_energies.yml"
    write_output(output, options, path_output)

    print("check output file: ", path_output)
