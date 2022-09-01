###############################################################################
#
# MIT License
#
# Copyright (c) 2022 Advanced Micro Devices, Inc.
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
#import pytest
from multiprocessing import Value, Lock, Queue
from subprocess import Popen, PIPE

sys.path.append("../tuna")
sys.path.append("tuna")

this_path = os.path.dirname(__file__)

from tuna.worker_interface import WorkerInterface
from tuna.machine import Machine
from tuna.sql import DbCursor
from tuna.tables import ConfigType


def add_job():
  find_configs = "SELECT count(*), tag FROM conv_config_tags WHERE tag='recurrent_pytest' GROUP BY tag"

  del_q = "DELETE FROM conv_job WHERE reason = 'tuna_pytest'"
  ins_q = "INSERT INTO conv_job(config, state, solver, valid, reason, fin_step, session) \
        SELECT conv_config_tags.config, 'new', NULL, 1, 'tuna_pytest', 'not_fin', 1 \
        FROM conv_config_tags WHERE conv_config_tags.tag LIKE 'recurrent_pytest'"

  with DbCursor() as cur:
    cur.execute(find_configs)
    res = cur.fetchall()
    if len(res) == 0:
      add_cfg = "{0}/../tuna/import_configs.py -f {0}/../utils/configs/conv_configs_NCHW.txt -t recurrent_pytest".format(
          this_path)
      os.system(add_cfg)

    cur.execute(del_q)
    cur.execute(ins_q)


def get_job(w):
  with DbCursor() as cur:
    cur.execute("UPDATE conv_job SET valid=0 WHERE id>=0")
  # to force commit
  with DbCursor() as cur:
    cur.execute("SELECT id FROM conv_job WHERE reason='tuna_pytest' LIMIT 1")
    res = cur.fetchall()
    assert (len(res) == 1)
    id = res[0][0]
    assert (id)
    cur.execute(
        "UPDATE conv_job SET state='new', valid=1, retries=0 WHERE id={}".
        format(id))

  #test get_job()
  job = w.get_job('new', 'compile_start', True)
  assert job == True
  with DbCursor() as cur:
    cur.execute("SELECT state FROM conv_job WHERE id={}".format(id))
    res = cur.fetchall()
    assert (res[0][0] == 'compile_start')
    job = w.get_job('new', 'compile_start', True)
    assert job == False
    cur.execute("UPDATE conv_job SET valid=0 WHERE id={}".format(id))


def multi_queue_test(w):
  # a separate block was necessary to force commit
  with DbCursor() as cur:
    #Queue test
    cur.execute("UPDATE conv_job SET valid=0 WHERE id>=0")
  with DbCursor() as cur:
    cur.execute(
        "UPDATE conv_job SET state='new', valid=1 WHERE reason='tuna_pytest' LIMIT {}"
        .format(w.claim_num + 1))
  job = w.get_job('new', 'compile_start', True)
  assert job == True
  res = None
  with DbCursor() as cur:
    cur.execute(
        "SELECT state FROM conv_job WHERE reason='tuna_pytest' AND state='compile_start' AND valid=1"
    )
    res = cur.fetchall()
  assert (len(res) == w.claim_num)

  with DbCursor() as cur:
    cur.execute(
        "UPDATE conv_job SET state='compiling' WHERE reason='tuna_pytest' AND state='compile_start' AND valid=1"
    )
  for i in range(w.claim_num - 1):
    job = w.get_job('new', 'compile_start', True)
    with DbCursor() as cur:
      assert job == True
      cur.execute(
          "SELECT state FROM conv_job WHERE reason='tuna_pytest' AND state='compile_start' AND valid=1"
      )
      res = cur.fetchall()
      assert (len(res) == 0)

  job = w.get_job('new', 'compile_start', True)
  assert job == True
  with DbCursor() as cur:
    cur.execute(
        "SELECT state FROM conv_job WHERE reason='tuna_pytest' AND state='compile_start' AND valid=1"
    )
    res = cur.fetchall()
    assert (len(res) == 1)
    cur.execute("UPDATE conv_job SET valid=0 WHERE reason='tuna_pytest'")


def test_worker():

  cmd = 'hostname'
  subp = Popen(cmd, stdout=PIPE, shell=True, universal_newlines=True)
  hostname = subp.stdout.readline().strip()
  machine = Machine(hostname=hostname, local_machine=True)

  keys = {}
  num_gpus = Value('i', len(machine.get_avail_gpus()))
  v = Value('i', 0)
  e = Value('i', 0)

  keys = {
      'machine': machine,
      'gpu_id': 0,
      'num_procs': num_gpus,
      'barred': v,
      'bar_lock': Lock(),
      'envmt': ["MIOPEN_LOG_LEVEL=7"],
      'reset_interval': False,
      'app_test': False,
      'label': '',
      'use_tuner': False,
      'job_queue': Queue(),
      'queue_lock': Lock(),
      'end_jobs': e,
      'fin_steps': ['not_fin'],
      'config_type': ConfigType.convolution,
      'session_id': 1
  }

  w = WorkerInterface(**keys)

  add_job()
  get_job(w)
  w.queue_end_reset()
  multi_queue_test(w)
