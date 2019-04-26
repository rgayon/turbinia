# -*- coding: utf-8 -*-
# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Task for running docker-explorer."""

from __future__ import unicode_literals

import json
import logging
import os
import subprocess

from turbinia import TurbiniaException
from turbinia.evidence import DockerContainer
from turbinia.workers import TurbiniaTask

log = logging.getLogger('turbinia')


class DockerContainersEnumerationTask(TurbiniaTask):
  """Enumerates Docker containers on Linux"""

  def GetContainers(self, evidence):
    """Lists the containers from an input Evidence.

    We use subprocess to run the DockerExplorer script, instead of using the
    Python module, because we need to make sure all DockerExplorer code runs
    as root.

    Args:
      evidence (Evidence): the input Evidence.

    Returns:
      a list(dict) containing information about the containers found.

    Raises:
      TurbiniaException: when the docker-explorer tool failed to run.
    """

    docker_dir = os.path.join(evidence.mount_path, 'var', 'lib', 'docker')

    containers_info = None
    de_paths = [
        path for path in ['/usr/local/bin/de.py', '/usr/bin/de.py']
        if os.path.isfile(path)
    ]
    if not de_paths:
      raise TurbiniaException('Could not find docker-explorer script: de.py')
    de_binary = de_paths[0]

    # TODO(rgayon): use docker-explorer exposed constant when
    # https://github.com/google/docker-explorer/issues/80 is in.
    docker_explorer_command = [
        'sudo', de_binary, '-r', docker_dir, 'list', 'all_containers'
    ]
    try:
      log.info('Running {0:s}'.format(' '.join(docker_explorer_command)))
      json_string = subprocess.check_output(docker_explorer_command)
    except Exception as e:
      raise TurbiniaException(
          'Failed to run {0:s}: {1!s}'.format(
              ' '.join(docker_explorer_command), e))

    try:
      containers_info = json.loads(json_string)
    except ValueError as e:
      raise TurbiniaException(
          'Could not parse output of {0} : {1!s} .'.format(
              ' '.join(docker_explorer_command), e))

    return containers_info

  def run(self, evidence, result):
    """Run the docker-explorer tool to list containerss.

    Args:
       evidence (Evidence object):  The evidence to process
       result (TurbiniaTaskResult): The object to place task results into.

    Returns:
      TurbiniaTaskResult object.
    """

    status_report = ''
    success = False

    if evidence.is_mounted:
      status_report = (
          'Error enumerating Docker containers, evidence has no mounted '
          'filesystem')
      found_containers = []
      try:
        containers_info = self.GetContainers(evidence)
        for container_info in containers_info:
          container_id = container_info.get('container_id')
          found_containers.append(container_id)
          container_evidence = DockerContainer(container_id=container_id)
          result.add_evidence(container_evidence, evidence.config)
        success = True
        status_report = 'Found {0!s} containers: {1:s}'.format(
            len(found_containers), ' '.join(found_containers))
      except TurbiniaException as e:
        status_report = 'Error enumerating Docker containers: {0!s}'.format(e)
    else:
      status_report = (
          'Evidence {0!s} did not expose a mounted file system'.format(
              evidence))

    result.close(self, success=success, status=status_report)

    return result
