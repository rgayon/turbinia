# -*- coding: utf-8 -*-
# Copyright 2017 Google Inc.
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
"""Turbinia Evidence objects."""

from __future__ import unicode_literals

import json
import os
import sys

from turbinia import config
from turbinia import TurbiniaException
from turbinia.processors import mount_local

# pylint: disable=keyword-arg-before-vararg

config.LoadConfig()
if config.TASK_MANAGER == 'PSQ':
  from turbinia.processors import google_cloud

def evidence_decode(evidence_dict):
  """Decode JSON into appropriate Evidence object.

  Args:
    evidence_dict: JSON serializable evidence object (i.e. a dict post JSON
                   decoding).

  Returns:
    An instantiated Evidence object (or a sub-class of it).

  Raises:
    TurbiniaException: If input is not a dict, does not have a type attribute,
                       or does not deserialize to an evidence object.
  """
  if not isinstance(evidence_dict, dict):
    raise TurbiniaException(
        'Evidence_dict is not a dictionary, type is {0:s}'.format(
            str(type(evidence_dict))))

  type_ = evidence_dict.get('type', None)
  if not type_:
    raise TurbiniaException(
        'No Type attribute for evidence object [{0:s}]'.format(
            str(evidence_dict)))

  try:
    evidence = getattr(sys.modules[__name__], type_)()
  except AttributeError:
    raise TurbiniaException(
        'No Evidence object of type {0:s} in evidence module'.format(type_))

  evidence.__dict__ = evidence_dict
  return evidence


class Evidence(object):
  """Evidence object for processing.

  In most cases, these objects will just contain metadata about the actual
  evidence.

  Attributes:
    config (dict): Configuration options from the request to be used when
        processing this evidence.
    cloud_only: Set to True for evidence types that can only be processed in a
        cloud environment, e.g. GoogleCloudDisk.
    copyable: Whether this evidence can be copied.  This will be set to True for
        object types that we want to copy to/from storage (e.g. PlasoFile, but
        not RawDisk).
    name: Name of evidence.
    description: Description of evidence.
    saved_path (string): Path to secondary location evidence is saved for later
        retrieval (e.g. GCS).
    saved_path_type (string): The name of the output writer that saved evidence
        to the saved_path location.
    source: String indicating where evidence came from (including tool version
        that created it, if appropriate).
    local_path: A string of the local_path to the evidence.
    tags: dict of extra tags associated with this evidence.
    request_id: The id of the request this evidence came from, if any
  """

  def __init__(self, name=None, description=None, source=None, local_path=None,
               tags=None, request_id=None):
    """Initialization for Evidence."""
    self.copyable = False
    self.config = {}
    self.cloud_only = False
    self.description = description
    self.source = source
    self.local_path = local_path
    self.tags = tags if tags else {}
    self.request_id = request_id

    # List of jobs that have processed this evidence
    self.processed_by = []
    self.type = self.__class__.__name__
    self.name = name if name else self.type
    self.saved_path = None
    self.saved_path_type = None

  def __str__(self):
    return '{0:s}:{1:s}:{2!s}'.format(self.type, self.name, self.local_path)

  def serialize(self):
    """Return JSON serializable object."""
    return self.__dict__

  def to_json(self):
    """Convert object to JSON.

    Returns:
      A JSON serialized string of the current object.

    Raises:
      TurbiniaException: If serialization error occurs.
    """
    try:
      serialized = json.dumps(self.serialize())
    except TypeError as e:
      msg = 'JSON serialization of evidence object {0:s} failed: {1:s}'.format(
          self.type, str(e))
      raise TurbiniaException(msg)

    return serialized

  def copy_context(self):
    """Copies attributes needed for saving the context (ie: for cleanup).

    This is used when a Task generates a new Evidence from an input Evidence,
    and wants to make sure the new Evidence will be pre&post processed properly.
    """
    pass

  def preprocess(self):
    """Preprocess this evidence prior to task running.

    This gets run in the context of the local task execution on the worker
    nodes prior to the task itself running.  This can be used to prepare the
    evidence to be processed (e.g. attach a cloud disk, mount a local disk etc).
    """
    pass

  def postprocess(self):
    """Postprocess this evidence after the task runs.

    This gets run in the context of the local task execution on the worker
    nodes after the task has finished.  This can be used to clean-up after the
    evidence is processed (e.g. detach a cloud disk, etc,).
    """
    pass


class Directory(Evidence):
  """Filesystem directory evidence."""
  pass


class RawDisk(Evidence):
  """Evidence object for Disk based evidence.

  Attributes:
    mount_path: The mount path for this disk (if any).
    mount_partition: The mount partition for this disk (if any).
    path_to_disk: The path to the underlying data (block device or disk image).
    size:  The size of the disk in bytes.
  """

  def __init__(self, mount_partition=None, size=None, *args,
               **kwargs):
    """Initialization for raw disk evidence object."""
    super(RawDisk, self).__init__(*args, **kwargs)
    self.mount_partition = mount_partition
    self.path_to_disk = self.local_path
    self.size = size
    self._loopdevice_path = None
    self._disk_mount_path = None

  def copy_context(self, target_evidence):
    target_evidence.mount_partition = self.mount_partition
    target_evidence.path_to_disk = self.path_to_disk
    target_evidence.size = self.size
    target_evidence._disk_mount_path = self._disk_mount_path
    target_evidence._loopdevice_path = self._loopdevice_path

  def preprocess(self):
    # First use losetup to parse the RawDisk eventual partition table
    # and make block devices per partitions.
    self._losetup_device = mount_local.PreprocessLoSetup(self.path_to_disk)
    # Then we mount the partition
    self._disk_mount_path = mount_local.PreprocessMountDisk(
        self._losetup_device, self.mount_partition)
    self.local_path = self._disk_mount_path

  def postprocess(self):
    mount_local.PostprocessUnmountPath(self._disk_mount_path)
    self._disk_mount_path = None
    mount_local.PostprocessDeleteLosetup(self._losetup_device)
    self._losetup_device = None
    self.local_path = None


class EncryptedDisk(RawDisk):
  """Encrypted disk file evidence.

  Attributes:
    encryption_type: The type of encryption used, e.g. FileVault or Bitlocker.
    encryption_key: A string of the encryption key used for this disk.
    unencrypted_path: A string to the unencrypted local path
  """

  def __init__(self, encryption_type=None, encryption_key=None,
               unencrypted_path=None, *args, **kwargs):
    """Initialization for Encrypted disk evidence objects."""
    # TODO(aarontp): Make this an enum, or limited list
    self.encryption_type = encryption_type
    self.encryption_key = encryption_key
    # self.local_path will be the encrypted path
    self.unencrypted_path = unencrypted_path
    super(EncryptedDisk, self).__init__(*args, **kwargs)


class GoogleCloudDisk(RawDisk):
  """Evidence object for Google Cloud Disks.

  Attributes:
    project: The cloud project name this disk is associated with.
    zone: The geographic zone.
    disk_name: The cloud disk name.
  """

  def __init__(self, project=None, zone=None, disk_name=None, *args, **kwargs):
    """Initialization for Google Cloud Disk."""
    self.project = project
    self.zone = zone
    self.disk_name = disk_name
    super(GoogleCloudDisk, self).__init__(*args, **kwargs)
    self.cloud_only = True

  def preprocess(self):
    self.local_path = google_cloud.PreprocessAttachDisk(self.disk_name)
    super(GoogleCloudDisk, self).preprocess()

  def postprocess(self):
    super(GoogleCloudDisk, self).postprocess()
    google_cloud.PostprocessDetachDisk(self.disk_name, self.local_path)
    self.local_path = None


class GoogleCloudDiskRawEmbedded(GoogleCloudDisk):
  """Evidence object for raw disks embedded in Persistent Disks.

  This is for a raw image file that is located in the filesystem of a mounted
  GCP Persistent Disk.  This can be useful if you want to process a raw disk
  image originating from outside cloud, and it is much more performant and
  reliable option than reading it directly from GCS FUSE.

  Attributes:
    embedded_path: The path of the raw disk image inside the Persistent Disk
  """

  def __init__(self, embedded_path=None, *args, **kwargs):
    """Initialization for Google Cloud Disk."""
    self.embedded_path = embedded_path
    super(GoogleCloudDiskRawEmbedded, self).__init__(*args, **kwargs)

  def preprocess(self):
    super(GoogleCloudDiskRawEmbedded, self).preprocess()
    self.local_path = os.path.join(self._disk_mount_path, self.embedded_path)

  def postprocess(self):
    super(GoogleCloudDiskRawEmbedded, self).post()


class PlasoFile(Evidence):
  """Plaso output file evidence.

  Attributes:
    plaso_version: The version of plaso that processed this file.
  """

  def __init__(self, plaso_version=None, *args, **kwargs):
    """Initialization for Plaso File evidence."""
    self.plaso_version = plaso_version
    super(PlasoFile, self).__init__(*args, **kwargs)
    self.copyable = True


class PlasoCsvFile(PlasoFile):
  """Psort output file evidence.  """

  def __init__(self, plaso_version=None, *args, **kwargs):
    """Initialization for Plaso File evidence."""
    self.plaso_version = plaso_version
    super(PlasoCsvFile, self).__init__(*args, **kwargs)


# TODO(aarontp): Find a way to integrate this into TurbiniaTaskResult instead.
class ReportText(Evidence):
  """Text data for general reporting."""

  def __init__(self, text_data=None, *args, **kwargs):
    self.text_data = text_data
    super(ReportText, self).__init__(*args, **kwargs)
    self.copyable = True


class TextFile(Evidence):
  """Text data."""

  def __init__(self, *args, **kwargs):
    super(TextFile, self).__init__(*args, **kwargs)
    self.copyable = True


class FilteredTextFile(TextFile):
  """Filtered text data."""
  pass


class ExportedFileArtifact(Evidence):
  """Exported file artifact."""

  def __init__(self, artifact_name):
    """Initializes an exported file artifact."""
    super(ExportedFileArtifact, self).__init__()
    self.artifact_name = artifact_name
    self.copyable = True
