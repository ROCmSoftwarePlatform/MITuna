###############################################################################
#
# MIT License
#
# Copyright (c) 2023 Advanced Micro Devices, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
###############################################################################

import os
import sys
import argparse
import logging
import random

sys.path.append("../tuna")
sys.path.append("tuna")

this_path = os.path.dirname(__file__)

from utils import ExampleArgs
from multiprocessing import Value
from tuna.sql import DbCursor
from tuna.machine import Machine
from tests.test_importconfigs_rocmlir import test_importconfigs_rocmlir
from tuna.rocmlir.load_job import add_jobs
from tuna.rocmlir.rocmlir_tables import RocMLIRDBTables, clear_tables, SessionRocMLIR
from tuna.rocmlir.rocmlir_worker import RocMLIRWorker
from tuna.rocmlir.config_type import ConfigType


def test_cfg_compose():
  """check the config query function for args tags and cmd intake"""
  clear_tables(ConfigType.convolution)
  test_importconfigs_rocmlir()  # to get the configs in place
  count_configs = "SELECT count(*) FROM rocmlir_conv_config;"
  with DbCursor() as cur:
    cur.execute(count_configs)
    res = cur.fetchall()
    config_count = res[0][0]

  args = ExampleArgs()
  args.init_session = True
  args.label = "test_load_job"
  args.load_factor = 1
  args.config_type = ConfigType.convolution
  machine = Machine(hostname="test", local_machine=True)
  worker = RocMLIRWorker(config_type=args.config_type,
                         session_id=None,
                         machine=machine,
                         num_procs=Value('i', 0))
  session_id = SessionRocMLIR().add_new_session(args, worker)

  dbt = RocMLIRDBTables(session_id=session_id)
  args = argparse.Namespace(session_id=session_id)
  job_count = add_jobs(args, dbt)
  assert job_count == config_count
