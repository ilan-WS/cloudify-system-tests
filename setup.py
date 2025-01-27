########
# Copyright (c) 2013-2019 Cloudify Platform Ltd. All rights reserved
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

from setuptools import setup

setup(
    name='cloudify-system-tests',
    version='6.1.0.dev1',
    author='Cloudify',
    author_email='cosmo-admin@cloudify.co',
    packages=['cosmo_tester'],
    license='LICENSE',
    description='Cosmo system tests framework',
    install_requires=[
        'fabric',
        'PyYAML',
        'requests>=2.7.0,<3.0.0',
        'path.py',
        'retrying',
        'Jinja2',
        'pywinrm',
        # Wagon version has been left out since it better reflects the user
        # use-case
        'wagon[venv]',
        'pytest',
        'pytest-xdist',
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'test-config = cosmo_tester.conf_cli:main',
        ]
    },

)
