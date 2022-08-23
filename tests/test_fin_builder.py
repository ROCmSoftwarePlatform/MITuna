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

sys.path.append("../tuna")
sys.path.append("tuna")

this_path = os.path.dirname(__file__)

from tuna.sql import DbCursor
from tuna.dbBase.sql_alchemy import DbSession
from tuna.go_fish import load_machines, compose_worker_list


def add_fin_find_compile_job():
  del_q = "DELETE FROM conv_job WHERE session = 1"
  del_q2 = "DELETE FROM conv_config_tags WHERE tag = 'test_fin_builder'"

  with DbCursor() as cur:
    cur.execute(del_q)
    cur.execute(del_q2)

  add_cfg = "{0}/../tuna/import_configs.py -t test_fin_builder --mark_recurrent -f {0}/../utils/configs/conv_configs_NCHW.txt".format(
      this_path)

  load_job = "{0}/../tuna/load_job.py -l tuna_pytest_fin_builder -t test_fin_builder \
      --fin_steps 'miopen_find_compile, miopen_find_eval' --session_id 1".format(
      this_path)

  os.system(add_cfg)
  os.system(load_job)


class Args():
  local_machine = None
  fin_steps = None
  session_id = None
  arch = None
  num_cu = None
  machines = None
  restart_machine = None
  update_applicability = None
  find_mode = None
  blacklist = None
  update_solvers = None
  config_type = None
  reset_interval = None
  dynamic_solvers_only = False
  label = None
  docker_name = None


def test_fin_builder():
  add_fin_find_compile_job()

  num_jobs = 0
  with DbCursor() as cur:
    get_jobs = "SELECT count(*) from conv_job where reason='tuna_pytest_fin_builder' and state='new';"
    cur.execute(get_jobs)
    res = cur.fetchall()
    assert (res[0][0] > 0)
    num_jobs = res[0][0]

  args = Args()
  args.local_machine = True
  args.fin_steps = "miopen_find_compile"
  args.session_id = 1

  res = load_machines(args)
  worker_lst = compose_worker_list(res, args)
  for worker in worker_lst:
    worker.join()

  with DbCursor() as cur:
    get_jobs = "SELECT count(*) from conv_job where reason='tuna_pytest_fin_builder' and state in ('compiled');"
    cur.execute(get_jobs)
    res = cur.fetchall()
    assert (res[0][0] == num_jobs)
