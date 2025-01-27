import json
import time
import hashlib
import tarfile

from cosmo_tester.framework.util import get_cli_package_url


def _prepare(cli_host, example, paths, logger):
    use_ssl = False
    if example.manager.api_ca_path:
        cli_host.put_remote_file(paths['cert'], example.manager.api_ca_path)
        use_ssl = True

    logger.info('Using manager')
    cli_host.run_command(
        '{cfy} profiles use {ip} -u admin -p admin -t {tenant}{ssl}'.format(
            cfy=paths['cfy'],
            ip=example.manager.private_ip_address,
            tenant=example.tenant,
            ssl=' -ssl -c {}'.format(paths['cert']) if use_ssl else '',
        ),
        powershell=True,
    )

    logger.info('Creating secret')
    cli_host.run_command(
        '{cfy} secrets create --secret-file {ssh_key} agent_key'.format(
            **paths
        ),
        powershell=True,
    )


def _test_upload_and_install(run, example, paths, logger):
    logger.info('Uploading blueprint')
    run('{cfy} blueprints upload -b {bp_id} {blueprint}'.format(
        bp_id=example.blueprint_id, **paths), powershell=True)

    logger.info('Creating deployment')
    run('{cfy} deployments create -b {bp_id} -i {inputs} {dep_id} '
        .format(bp_id=example.blueprint_id, dep_id=example.deployment_id,
                **paths),
        powershell=True)

    logger.info('Executing install workflow')
    run('{cfy} executions start install -d {dep_id}'.format(
        dep_id=example.deployment_id, **paths),
        powershell=True)

    example.check_files()


def _test_cfy_install(run, example, paths, logger):
    logger.info('Running cfy install for blueprint')
    run(
        '{cfy} install --blueprint-id {blueprint} '
        '--deployment-id {deployment} --inputs {inputs} '
        '{blueprint_path}'.format(
            cfy=paths['cfy'],
            blueprint=example.blueprint_id,
            deployment=example.deployment_id,
            inputs=paths['inputs'],
            blueprint_path=paths['blueprint'],
        ),
        powershell=True,
    )

    example.check_files()


def _set_ssh_in_profile(run, example, paths):
    run(
        '{cfy} profiles set --ssh-user {ssh_user} --ssh-key {ssh_key}'.format(
            cfy=paths['cfy'],
            ssh_user=example.manager.username,
            ssh_key=paths['ssh_key'],
        ),
        powershell=True,
    )


def _test_cfy_logs(run, cli_host, example, paths, tmpdir, logger):
    _set_ssh_in_profile(run, example, paths)

    # stop manager services so the logs won't change during the test
    example.manager.run_command('cfy_manager stop')

    logs_dump_filepath = [v for v in json.loads(run(
        '{cfy} logs download --json'.format(cfy=paths['cfy'])
    ).stdout.strip())['archive paths']['manager'].values()][0]

    log_hashes = [f.split()[0] for f in example.manager.run_command(
        'find /var/log/cloudify -type f -not -name \'supervisord.log\''
        ' -exec md5sum {} + | sort',
        use_sudo=True
    ).stdout.splitlines()]
    logger.info('Calculated log hashes for %s are %s',
                example.manager.private_ip_address,
                log_hashes)

    local_logs_dump_filepath = str(tmpdir / 'logs.tar')
    cli_host.get_remote_file(logs_dump_filepath, local_logs_dump_filepath)
    logger.info('Start extracting log hashes locally for %s',
                local_logs_dump_filepath)
    with tarfile.open(local_logs_dump_filepath) as tar:
        tar.extractall(str(tmpdir))

    files = list((tmpdir / 'cloudify').visit('*.*'))
    logger.info('Checking both `journalctl.log` and '
                '`supervisord.log` are exist inside %s',
                local_logs_dump_filepath)
    assert str(tmpdir / 'cloudify/journalctl.log') in files
    assert str(tmpdir / 'cloudify/supervisord.log') in files
    log_hashes_local = sorted(
        [hashlib.md5(open(f.strpath, 'rb').read()).hexdigest() for f in files
         if 'journalctl' not in f.basename
         and 'supervisord' not in f.basename]
    )
    logger.info('Calculated log hashes locally for %s are %s',
                example.manager.private_ip_address,
                log_hashes_local)
    assert set(log_hashes) == set(log_hashes_local)

    logger.info('Testing `cfy logs backup`')
    run('{cfy} logs backup --verbose'.format(cfy=paths['cfy']))
    output = example.manager.run_command('ls /var/log').stdout
    assert 'cloudify-manager-logs_' in output

    logger.info('Testing `cfy logs purge`')
    example.manager.run_command('cfy_manager stop')
    run('{cfy} logs purge --force'.format(cfy=paths['cfy']))
    # Verify that each file under /var/log/cloudify is size zero
    logger.info('Verifying each file under /var/log/cloudify is size zero')
    example.manager.run_command(
        'find /var/log/cloudify -type f -not -name \'supervisord.log\''
        ' -exec test -s {} \\; -print -exec false {} +',
        use_sudo=True
    )


def _test_teardown(run, example, paths, logger):
    logger.info('Starting uninstall workflow')
    run('{cfy} executions start uninstall -d {dep_id}'.format(
        dep_id=example.deployment_id, **paths),
        powershell=True)

    example.check_all_test_files_deleted()

    logger.info('Deleting deployment')
    run('{cfy} deployments delete {dep_id}'.format(
        dep_id=example.deployment_id, **paths),
        powershell=True)
    # With a sleep because this returns before the DB is updated
    time.sleep(4)

    logger.info('Checking deployment has been deleted.')
    deployments = json.loads(
        run('{cfy} deployments list --json'.format(**paths),
            powershell=True).stdout
    )
    assert len(deployments) == 0

    logger.info('Deleting secret')
    run('{cfy} secrets delete agent_key'.format(**paths), powershell=True)

    logger.info('Checking secret has been deleted.')
    secrets = json.loads(
        run('{cfy} secrets list --json'.format(**paths),
            powershell=True).stdout
    )
    assert len(secrets) == 0

    logger.info('Deleting blueprint')
    run('{cfy} blueprints delete {bp_id}'.format(
        bp_id=example.blueprint_id, **paths),
        powershell=True)
    # With a sleep because this returns before the DB is updated
    time.sleep(4)

    logger.info('Checking blueprint has been deleted.')
    blueprints = json.loads(
        run('{cfy} blueprints list --json'.format(**paths),
            powershell=True).stdout
    )
    assert len(blueprints) == 0


def get_linux_image_settings():
    return [
        ('centos_7', 'rhel_centos_cli_package_url', 'rpm'),
        ('rhel_7', 'rhel_centos_cli_package_url', 'rpm'),
    ]


def _install_linux_cli(cli_host, logger, url_key, pkg_type, test_config):
    logger.info('Downloading CLI package')
    cli_package_url = get_cli_package_url(url_key, test_config)
    logger.info('Using CLI package: {url}'.format(
        url=cli_package_url,
    ))
    cli_host.run_command('curl -Lo cloudify-cli.{pkg_type} {url}'.format(
        url=cli_package_url, pkg_type=pkg_type,
    ))

    logger.info('Installing CLI package')
    install_cmd = {
        'rpm': 'yum install -y',
        'deb': 'dpkg -i',
    }[pkg_type]
    cli_host.run_command(
        '{install_cmd} cloudify-cli.{pkg_type}'.format(
            install_cmd=install_cmd,
            pkg_type=pkg_type,
        ),
        use_sudo=True,
    )
