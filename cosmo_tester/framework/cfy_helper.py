########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


import tempfile
import shutil
import json

import sh
from path import path
from cloudify_cli.constants import DEFAULT_REST_PORT

from cloudify_cli.utils import load_cloudify_working_dir_settings
from cosmo_tester.framework.util import sh_bake


cfy = sh_bake(sh.cfy)


DEFAULT_EXECUTE_TIMEOUT = 1800


class CfyHelper(object):

    def __init__(self,
                 cfy_workdir=None,
                 management_ip=None,
                 port=DEFAULT_REST_PORT):
        self._cfy_workdir = cfy_workdir
        self.tmpdir = False
        if cfy_workdir is None:
            self.tmpdir = True
            self._cfy_workdir = tempfile.mkdtemp(prefix='cfy-')
        self.workdir = path(self._cfy_workdir)
        if management_ip is not None:
            self.use(management_ip, port)

    def bootstrap(self,
                  blueprint_path,
                  inputs_file=None,
                  install_plugins=True,
                  keep_up_on_failure=False,
                  validate_only=False,
                  reset_config=False,
                  task_retries=5,
                  verbose=False):
        with self.workdir:
            cfy.init(reset_config=reset_config).wait()

            if not inputs_file:
                inputs_file = self._get_inputs_in_temp_file({}, 'manager')

            cfy.bootstrap(
                blueprint_path=blueprint_path,
                inputs=inputs_file,
                install_plugins=install_plugins,
                keep_up_on_failure=keep_up_on_failure,
                validate_only=validate_only,
                task_retries=task_retries,
                verbose=verbose).wait()

    def recover(self):
        with self.workdir:
            cfy.recover(force=True).wait()

    def teardown(self,
                 ignore_deployments=True,
                 ignore_validation=False,
                 verbose=False):
        with self.workdir:
            cfy.teardown(
                ignore_deployments=ignore_deployments,
                ignore_validation=ignore_validation,
                force=True,
                verbose=verbose).wait()

    def upload_deploy_and_execute_install(
            self,
            blueprint_path,
            blueprint_id,
            deployment_id,
            verbose=False,
            include_logs=True,
            execute_timeout=DEFAULT_EXECUTE_TIMEOUT,
            inputs=None):
        with self.workdir:
            self.upload_blueprint(
                blueprint_path=blueprint_path,
                blueprint_id=blueprint_id,
                verbose=verbose)
            self.create_deployment(
                blueprint_id=blueprint_id,
                deployment_id=deployment_id,
                verbose=verbose,
                inputs=inputs)
            self.execute_install(
                deployment_id=deployment_id,
                execute_timeout=execute_timeout,
                verbose=verbose,
                include_logs=include_logs)

    def create_deployment(self,
                          blueprint_id,
                          deployment_id,
                          verbose=False,
                          inputs=None):
        with self.workdir:
            inputs_file = self._get_inputs_in_temp_file(inputs, deployment_id)
            cfy.deployments.create(
                blueprint_id=blueprint_id,
                deployment_id=deployment_id,
                verbose=verbose,
                inputs=inputs_file).wait()

    def delete_deployment(self, deployment_id,
                          verbose=False,
                          ignore_live_nodes=False):
        with self.workdir:
            cfy.deployments.delete(
                deployment_id=deployment_id,
                ignore_live_nodes=ignore_live_nodes,
                verbose=verbose).wait()

    def delete_blueprint(self, blueprint_id,
                         verbose=False):
        with self.workdir:
            cfy.blueprints.delete(
                blueprint_id=blueprint_id,
                verbose=verbose).wait()

    def execute_install(self,
                        deployment_id,
                        verbose=False,
                        include_logs=True,
                        execute_timeout=DEFAULT_EXECUTE_TIMEOUT):
        self.execute_workflow(
            workflow='install',
            deployment_id=deployment_id,
            execute_timeout=execute_timeout,
            verbose=verbose,
            include_logs=include_logs)

    def execute_uninstall(self,
                          deployment_id,
                          verbose=False,
                          include_logs=True,
                          execute_timeout=DEFAULT_EXECUTE_TIMEOUT):
        self.execute_workflow(
            workflow='uninstall',
            deployment_id=deployment_id,
            execute_timeout=execute_timeout,
            verbose=verbose,
            include_logs=include_logs)

    def upload_blueprint(self,
                         blueprint_id,
                         blueprint_path,
                         verbose=False):
        with self.workdir:
            cfy.blueprints.upload(
                blueprint_path=blueprint_path,
                blueprint_id=blueprint_id,
                verbose=verbose).wait()

    def download_blueprint(self, blueprint_id):
        with self.workdir:
            cfy.blueprints.download(blueprint_id=blueprint_id).wait()

    def use(self, management_ip, port):
        with self.workdir:
            cfy.use(management_ip=management_ip, port=port).wait()

    def get_management_ip(self):
        with self.workdir:
            settings = load_cloudify_working_dir_settings()
            return settings.get_management_server()

    def get_provider_context(self):
        with self.workdir:
            settings = load_cloudify_working_dir_settings()
            return settings.get_provider_context()

    def close(self):
        if self.tmpdir:
            shutil.rmtree(self._cfy_workdir)

    def execute_workflow(self,
                         workflow,
                         deployment_id,
                         verbose=False,
                         include_logs=True,
                         execute_timeout=DEFAULT_EXECUTE_TIMEOUT,
                         parameters=None):
        params_file = self._get_inputs_in_temp_file(parameters, workflow)
        with self.workdir:
            cfy.executions.start(
                workflow=workflow,
                deployment_id=deployment_id,
                timeout=execute_timeout,
                verbose=verbose,
                include_logs=include_logs,
                parameters=params_file).wait()

    def _get_inputs_in_temp_file(self, inputs, inputs_prefix):
        inputs = inputs or {}
        inputs_file = tempfile.mktemp(prefix='{0}-'.format(inputs_prefix),
                                      suffix='-inputs.json',
                                      dir=self.workdir)
        with open(inputs_file, 'w') as f:
            f.write(json.dumps(inputs))
        return inputs_file
