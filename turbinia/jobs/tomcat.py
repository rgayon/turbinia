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
"""Job to execute Apache Tomcat analysis task."""
from __future__ import unicode_literals
from turbinia.workers import artifact
from turbinia.workers import tomcat
from turbinia.evidence import Directory
from turbinia.evidence import DockerContainer
from turbinia.evidence import GoogleCloudDisk
from turbinia.evidence import GoogleCloudDiskRawEmbedded
from turbinia.evidence import ExportedFileArtifact
from turbinia.evidence import RawDisk
from turbinia.evidence import ReportText
from turbinia.jobs import TurbiniaJob


class TomcatExtractionJob(TurbiniaJob):
  """Extract Apache Tomcat files for analysis."""

  # The types of evidence that this Job will process
  evidence_input = [
      Directory, DockerContainer, RawDisk, GoogleCloudDisk,
      GoogleCloudDiskRawEmbedded]

  evidence_output = [ExportedFileArtifact]

  def __init__(self):
    super(TomcatExtractionJob, self).__init__(name='TomcatExtractionJob')

  def create_tasks(self, evidence):
    """Create task.

     Args:
      evidence: List of evidence object to process

     Returns:
        A list of tasks to schedule.
    """
    tasks = [
        artifact.FileArtifactExtractionTask('TomcatFiles') for _ in evidence]
    return tasks

class TomcatAnalysisJob(TurbiniaJob):
  """Create tasks to analyse Apache Tomcat files."""

  evidence_input = [ExportedFileArtifact]
  evidence_output = [ReportText]

  def __init__(self):
    super(TomcatAnalysisJob, self).__init__(name='TomcatAnalysisJob')

  def create_tasks(self, evidence):
    """Create task.

     Args:
      evidence: List of evidence object to process

     Returns:
        A list of tasks to schedule.
    """
    tasks = []

    for evidence_item in evidence:
      if evidence_item.artifact_name == 'TomcatFile':
        tasks.append(tomcat.TomcatAnalysisTask())
    return tasks
