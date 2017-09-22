########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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

import os
import shutil

from cosmo_tester.framework.fixtures import image_based_manager as manager


BLUEPRINT = 'fake-agent-blueprint'
DEPLOYMENT = 'fake-agent-deployment'


def test_manager_agent_scaling(cfy, manager):
    blueprint_dir = os.path.join(
        os.path.dirname(__file__),
        '../../resources/blueprints/',
        'fake-agent-scale',
        )
    manager.upload_plugin('agent/plugins/fake-load-plugin')

    shutil.copy2(
        os.path.join(
            os.path.dirname(__file__),
            "../../resources/agent/plugins/fake-load-plugin/plugin.yaml",
        ),
        blueprint_dir,
        )
    manager.client.blueprints.upload(
            os.path.join(blueprint_dir, 'blueprint.yaml'),
            'fake-agent-blueprint',
            )

    manager.client.deployments.create(
            BLUEPRINT,
            DEPLOYMENT,
            )

    cfy.executions.start.install(['-d', DEPLOYMENT])