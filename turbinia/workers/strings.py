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
"""Task for gathering ascii strings."""

from __future__ import unicode_literals

import os

from turbinia.evidence import TextFile
from turbinia.workers import TurbiniaTask


class StringsAsciiTask(TurbiniaTask):
  """Task to generate ascii strings."""

  def run(self, evidence, result):
    """Run strings binary.

    Args:
        evidence (Evidence object):  The evidence we will process
        result (TurbiniaTaskResult): The object to place task results into.

    Returns:
        TurbiniaTaskResult object.
    """
    # Create the new Evidence object that will be generated by this Task.
    output_evidence = TextFile()
    # Create a path that we can write the new file to.
    base_name = os.path.basename(evidence.device_path)
    output_file_path = os.path.join(
        self.output_dir, '{0:s}.ascii'.format(base_name))
    # Add the output path to the evidence so we can automatically save it
    # later.
    output_evidence.source_path = output_file_path

    # Generate the command we want to run.
    cmd = 'strings -a -t d {0:s} > {1:s}'.format(
        evidence.device_path, output_file_path)
    # Add a log line to the result that will be returned.
    result.log('Running strings as [{0:s}]'.format(cmd))
    # Actually execute the binary
    self.execute(
        cmd, result, new_evidence=[output_evidence], close=True, shell=True)

    return result


class StringsUnicodeTask(TurbiniaTask):
  """Task to generate Unicode (16 bit little endian) strings."""

  def run(self, evidence, result):
    """Run strings binary.

    Args:
        evidence (Evidence object):  The evidence we will process
        result (TurbiniaTaskResult): The object to place task results into.

    Returns:
        TurbiniaTaskResult object.
    """
    # Create the new Evidence object that will be generated by this Task.
    output_evidence = TextFile()
    # Create a path that we can write the new file to.
    base_name = os.path.basename(evidence.device_path)
    output_file_path = os.path.join(
        self.output_dir, '{0:s}.uni'.format(base_name))
    # Add the output path to the evidence so we can automatically save it
    # later.
    output_evidence.source_path = output_file_path

    # Generate the command we want to run.
    cmd = 'strings -a -t d -e l {0:s} > {1:s}'.format(
        evidence.device_path, output_file_path)
    # Add a log line to the result that will be returned.
    result.log('Running strings as [{0:s}]'.format(cmd))
    # Actually execute the binary
    self.execute(
        cmd, result, new_evidence=[output_evidence], close=True, shell=True)

    return result
