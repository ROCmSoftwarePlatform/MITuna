#!/usr/bin/env python3
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
"""Interface class to set up and launch tuning functionality"""
import os
from multiprocessing import Value, Lock, Queue as mpQueue, Process
from typing import Optional, Dict, Any, List
from io import StringIO
from functools import lru_cache
import json
import logging
import argparse
import subprocess
import time
import threading
import asyncio
from datetime import timedelta
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.inspection import inspect
import aioredis
import kombu
from paramiko.channel import ChannelFile

from tuna.worker_interface import WorkerInterface
from tuna.machine import Machine
from tuna.libraries import Library
from tuna.utils.logger import setup_logger
from tuna.utils.utility import get_env_vars, SimpleDict
from tuna.dbBase.sql_alchemy import DbSession
from tuna.celery_app.celery_app import stop_active_workers, stop_named_worker
from tuna.celery_app.celery_app import get_backend_env, purge_queue
from tuna.celery_app.utility import get_q_name
from tuna.celery_app.celery_workers import launch_celery_worker
from tuna.libraries import Operation
from tuna.custom_errors import CustomError
from tuna.utils.db_utility import gen_update_query, session_retry

job_counter_lock = threading.Lock()


class MITunaInterface():  #pylint:disable=too-many-instance-attributes,too-many-public-methods
  """ Interface class extended by libraries. The purpose of this class is to define
  common functionalities. """

  def __init__(self, library=Library.MIOPEN) -> None:

    self.self: Library = self

    self.logger: logging.Logger = setup_logger(logger_name=library.value,
                                               add_streamhandler=True)
    self.args: argparse.Namespace

    self.fetch_state: set = set()
    self.max_job_retries = 10
    self.dbt = None
    self.operation = None
    self.db_name = os.environ['TUNA_DB_NAME']
    self.prefix = None

  def check_docker(self,
                   worker: WorkerInterface,
                   dockername="miopentuna") -> bool:
    """! Checking for docker
      @param worker The worker interface instance
      @param dockername The name of the docker
    """
    out2: ChannelFile
    _, out2, _ = worker.exec_command("sudo docker info")
    while not out2.channel.exit_status_ready():
      self.logger.warning(out2.readline())
    if out2.channel.exit_status > 0:
      self.logger.warning(
          "docker not installed or failed to run with sudo .... ")
      return False

    out: StringIO = StringIO()
    line: Optional[str] = None
    _, out, _ = worker.exec_command(f"sudo docker images | grep {dockername}")
    for line in out.readlines():
      if line is not None:
        if line.find(dockername) != -1:
          self.logger.warning('%s docker image exists', dockername)
          return True
    if line is None:
      self.logger.warning('%s docker image does not exist', dockername)
      return False

    return False

  def check_status(self,
                   worker: WorkerInterface,
                   b_first: int,
                   gpu_idx: int,
                   machine: Machine,
                   dockername: str = "miopentuna") -> bool:
    """! Function to check gpu_status
      @param worker The worker interface instance
      @param b_first Flag to keep track of visited GPU
      @param gpu_idx Unique ID of the GPU
      @param machine The machine instance
      @param dockername The name of the docker
    """

    if machine.chk_gpu_status(worker.gpu_id):
      self.logger.info('Machine: (%s, %u) GPU_ID: %u OK', machine.hostname,
                       machine.port, gpu_idx)
    else:
      self.logger.info('Machine: (%s, %u) GPU_ID: %u ERROR', machine.hostname,
                       machine.port, gpu_idx)

    if not b_first:
      return False
    b_first = False
    _, out, _ = worker.exec_command("docker info")
    while not out.channel.exit_status_ready():
      pass

    if out.channel.exit_status > 0:
      self.check_docker(worker, dockername)
    else:
      _, out, _ = worker.exec_command(f"docker images | grep {dockername}")
      line: Optional[str] = None
      for line in out.readlines():
        if line is not None:
          if line.find(dockername) != -1:
            self.logger.warning('%s docker image exists', dockername)
            break
        else:
          self.logger.warning('%s docker image does not exist', dockername)

    return True

  def add_tables(self) -> bool:
    """Add self specific tables"""
    return self.add_tables()

  def get_num_procs(self, machine: Machine) -> List:
    """Determine number of processes by compute capacity"""
    worker_ids: List = []
    num_procs: int
    env: Dict[str, Any]
    env = get_env_vars()
    if env['slurm_cpus'] > 0:
      num_procs = int(env['slurm_cpus'])
    else:
      num_procs = int(machine.get_num_cpus() * .6)

    worker_ids = list(range(num_procs))

    if len(worker_ids) == 0:
      self.logger.error('num_procs must be bigger than zero to launch worker')
      self.logger.error('Cannot launch worker on machine: %s', machine.id)
      worker_ids = []

    return worker_ids

  def get_f_vals(self,
                 machine: Machine,
                 worker_ids: range,
                 tuning=False) -> Dict[str, Any]:
    #pylint:disable=unused-argument
    """Determine kwargs for worker_interface"""
    f_vals: Dict[str, Any]
    f_vals = self.compose_f_vals(machine)
    f_vals['envmt'] = self.get_envmt()

    if not tuning:
      f_vals["num_procs"] = Value('i', len(worker_ids))

    return f_vals

  def get_envmt(self):
    """Get runtime envmt"""
    raise NotImplementedError("Not implemented")

  def compose_f_vals(self, machine: Machine, tuning=False) -> Dict[str, Any]:
    """! Compose dict for WorkerInterface constructor
      @param args The command line arguments
      @param machine Machine instance
    """
    f_vals: Dict[str, Any] = {}
    f_vals["b_first"] = True

    #adding non-serializable obj when not running through celery
    if not tuning:
      f_vals["machine"] = machine
      f_vals["bar_lock"] = Lock()
      #multiprocess queue for jobs, shared on machine
      f_vals["job_queue"] = mpQueue()
      f_vals["job_queue_lock"] = Lock()
      f_vals["end_jobs"] = Value('i', 0)

    return f_vals

  def get_kwargs(self,
                 gpu_idx: int,
                 f_vals: Dict[str, Any],
                 tuning=False) -> Dict[str, Any]:
    """! Helper function to set up kwargs for worker instances
      @param gpu_idx Unique ID of the GPU
      @param f_vals Dict containing runtime information
    """
    envmt: Dict[str, Any] = f_vals["envmt"].copy()
    kwargs: Dict[str, Any] = {}

    kwargs = {
        'gpu_id': gpu_idx,
        'envmt': envmt,
        'label': self.args.label,
        'docker_name': self.args.docker_name,
        'session_id': self.args.session_id
    }

    #adding non-serializable obj when not running through celery
    if not tuning:
      kwargs["machine"] = f_vals["machine"]
      kwargs["job_queue"] = f_vals["job_queue"]
      kwargs["job_queue_lock"] = f_vals["job_queue_lock"]
      kwargs["num_procs"] = f_vals["num_procs"]
      kwargs["bar_lock"] = f_vals["bar_lock"]
      kwargs["end_jobs"] = f_vals["end_jobs"]
      kwargs["job_queue"] = f_vals["job_queue"]
      kwargs["job_queue_lock"] = f_vals["job_queue_lock"]

    return kwargs

  def get_job_list(self, session, find_state, claim_num):
    """Get list of jobs"""
    raise NotImplementedError("Not implemented")

  def get_jobs(self,
               session: DbSession,
               find_state: List[str],
               set_state: str,
               session_id: int,
               claim_num: int = None,
               no_update=False):
    """Interface function to get jobs based on session and find_state"""
    #job_rows: List[SimpleDict]
    ids: list
    row: SimpleDict

    self.logger.info('Fetching DB rows...')
    job_list = self.get_job_list(session, find_state, claim_num)

    if not self.check_jobs_found(job_list, find_state, session_id):
      return []

    if no_update:
      return job_list

    ids = [row.id for row in job_list]
    self.logger.info("%s jobs %s", find_state, ids)
    self.logger.info('Updating job state to %s', set_state)
    for job in job_list:
      job.state = set_state
      if self.dbt is not None:
        query: str = gen_update_query(job, ['state'],
                                      self.dbt.job_table.__tablename__)
      else:
        raise CustomError('DBTable must be set')
      session.execute(query)

    session.commit()

    return job_list

  def shutdown_workers(self):
    """Shutdown all active celery workers regardless of queue"""
    return stop_active_workers()

  def cancel_consumer(self, queue):
    """Cancel consumers for queue"""
    try:
      cmd = f"celery -A tuna.celery_app.celery_app control cancel_consumer {queue}"
      subp = subprocess.Popen(  #pylint: disable=consider-using-with
          cmd,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          shell=True,
          universal_newlines=True)

      #filter the workers by session id
      sess_str = "sess_" + queue.split('_')[-1]
      stdout, _ = subp.stdout, subp.stderr
      while True:
        line = stdout.readline()
        if not line:
          break
        #stop workers that were feeding from this queue
        if "->" in line and sess_str in line:
          hostname = line.split('->')[1].split()[0].split(':')[0]
          stop_named_worker(hostname)

    except Exception as exp:  #pylint: disable=broad-exception-caught
      self.logger.warning(
          'Error occurred trying to cancel consumer for queue: %s ', queue)
      self.logger.warning(exp)
      return False

    self.logger.info('Sucessfully cancelled consumer for queue: %s', queue)

    return True

  def celery_enqueue_call(self, context, q_name, task_id=False):
    """Wrapper function for celery enqueue func"""
    raise NotImplementedError('Not implemented')

  def enqueue_jobs(self, job_counter, job_batch_size, q_name):
    """Enqueue celery jobs"""
    self.logger.info('Starting enqueue')
    with DbSession() as session:
      while True:
        job_list = []
        #get all the jobs from mySQL
        job_list = self.get_jobs(
            session,
            self.fetch_state,
            self.set_state,  #pylint: disable=no-member
            self.args.session_id,  #pylint: disable=no-member
            job_batch_size)

        with job_counter_lock:
          job_counter.value = job_counter.value + len(job_list)

        for i in range(0, len(job_list), job_batch_size):
          batch_jobs = job_list[i:min(i + job_batch_size, len(job_list))]
          context_list = self.get_context_list(session, batch_jobs)
          for context in context_list:
            #calling celery task, enqueuing to celery queue
            self.celery_enqueue_call(context, q_name=q_name)

        self.logger.info('Job counter: %s', job_counter.value)
        if not job_list:
          self.logger.info('All tasks added to queue')
          break

  async def cleanup_redis_results(self, prefix):
    """Remove stale redis results by key"""
    backend_port, backend_host = get_backend_env()
    redis = await aioredis.from_url(f"redis://{backend_host}:{backend_port}/15")

    keys = []
    cursor = "0"
    if prefix:
      #a prefix is necessary when the need to different results in redis based on operation
      #withough a prefix the redis key defaults to: "celery-task-meta-<unique kombu hash>"
      #with a prefix the key will look like: "celery-task-meta-<prefix>-<unique kombu hash>"
      #the prefix can be applied when filtering the redis keys as bellow
      cursor, results = await redis.scan(cursor, match=f"*{prefix}*")
    else:
      #no prefix, match any key
      cursor, results = await redis.scan(cursor, match="*")
    keys.extend(results)
    self.logger.info('Found %s old results', len(results))
    for key in keys:
      try:
        await redis.delete(key)
      except aioredis.exceptions.ResponseError as red_err:
        self.logger.error(red_err)
        self.logger.info(key.decode('utf-8'))
        continue

    self.logger.info('Done removing old redis results for prefix: %s', prefix)

    return True

  async def consume(self, job_counter, prefix):
    """Retrieve celery results from redis db"""

    backend_port, backend_host = get_backend_env()
    redis = await aioredis.from_url(f"redis://{backend_host}:{backend_port}/15")

    while job_counter.value > 0:
      cursor = "0"
      keys = []
      while cursor != 0:
        if prefix:
          #a prefix is necessary when the need to different results in redis based on operation
          #withough a prefix the redis key defaults to: "celery-task-meta-<unique kombu hash>"
          #with a prefix the key will look like: "celery-task-meta-<prefix>-<unique kombu hash>"
          #the prefix can be applied when filtering the redis keys as bellow
          cursor, results = await redis.scan(cursor, match=f"*{prefix}*")
        else:
          #no prefix, match any key
          cursor, results = await redis.scan(cursor, match="*")
        keys.extend(results)
      self.logger.info('Found %s results', len(results))
      for key in keys:
        try:
          data = await redis.get(key)
          if data:
            _ = await self.parse_result(data.decode('utf-8'))
            await redis.delete(key)
            with job_counter_lock:
              job_counter.value = job_counter.value - 1
        except aioredis.exceptions.ResponseError as red_err:
          self.logger.error(red_err)
          self.logger.info(key.decode('utf-8'))

      await asyncio.sleep(1)
    self.logger.info('Job counter reached 0')
    await redis.close()

    return True

  def prep_tuning(self):
    """Prep env for tuning start"""
    cmd = None
    subp_list = []
    q_name = None
    if self.operation == Operation.COMPILE:
      q_name = get_q_name(self, op_compile=True)
      cmd = f"celery -A tuna.celery_app.celery_app worker -l info -E -n tuna_HOSTNAME_sess_{self.args.session_id} -Q {q_name}"  #pylint: disable=line-too-long
    else:
      q_name = get_q_name(self, op_eval=True)
      cmd = f"celery -A tuna.celery_app.celery_app worker -l info -E -c 1 -n tuna_HOSTNAME_sess_{self.args.session_id}_gpu_id_GPUID -Q {q_name}"  #pylint: disable=line-too-long

    self.logger.info('celery Q name: %s', q_name)
    if not self.args.enqueue_only:
      try:
        self.logger.info('Launching celery workers for queue %s', q_name)
        subp_list = launch_celery_worker(self.operation, cmd, self.args, True)
        self.logger.info('Done launching celery workers')
        if not subp_list:
          raise CustomError('Could not launch celery worker')
      except kombu.exceptions.OperationalError as k_err:
        self.logger.error('Redis error ocurred: %s', k_err)
        return False
    else:
      purge_queue([q_name])

    return q_name, subp_list

  #pylint: disable=too-many-locals
  def tune(self, job_batch_size=1000):
    """tuning loop to spin out celery tasks"""

    if self.args.shutdown_workers:
      self.logger.info('Shutting down all celery workers')
      stop_active_workers()
      return True

    try:
      q_name, subp_list = self.prep_tuning()
    except CustomError as verr:
      self.logger.error(verr)
      return False

    try:
      #if enqueue_only is False, we launch the celery workers
      if not self.args.enqueue_only:
        for subp in subp_list:
          subp.wait()
        return True
    except KeyboardInterrupt:
      for subp in subp_list:
        subp.kill()
      return False

    start = time.time()

    #set job count to 1 until first job fetch is finished
    job_counter = Value('i', 1)
    try:
      enqueue_proc = Process(target=self.enqueue_jobs,
                             args=[job_counter, job_batch_size, q_name])
      #Start enqueue proc
      enqueue_proc.start()

      #cleanup old results
      cleanup_proc = Process(target=self.async_wrap,
                             args=(self.cleanup_redis_results, self.prefix))
      cleanup_proc.start()
      cleanup_proc.join()

      #start async consume thread, blocking
      consume_proc = Process(target=self.async_wrap,
                             args=(self.consume, job_counter, self.prefix))
      self.logger.info('Starting consume thread')
      consume_proc.start()

      enqueue_proc.join()
      #enqueue finished first fetch, remove hold on job_counter
      with job_counter_lock:
        job_counter.value = job_counter.value - 1

      #check for new jobs
      while consume_proc.is_alive():
        enqueue_proc = Process(target=self.enqueue_jobs,
                               args=[job_counter, job_batch_size, q_name])
        enqueue_proc.start()
        enqueue_proc.join()
        time.sleep(10)

      consume_proc.join()

    except (KeyboardInterrupt, Exception) as exp:  #pylint: disable=broad-exception-caught
      self.logger.error('Error ocurred %s', exp)
      purge_queue([q_name])
      self.cancel_consumer(q_name)
      self.reset_job_state_on_ctrl_c()
      with job_counter_lock:
        job_counter.value = 0

    self.cancel_consumer(q_name)
    end = time.time()
    self.logger.info("Took {:0>8} to tune".format(  #pylint: disable=consider-using-f-string
        str(timedelta(seconds=end - start))))

    return True

  async def async_callback(self, async_func, *args):
    """Wrapper function to await on async function"""
    await async_func(*args)

  def async_wrap(self, async_func, *args):
    """Run async function"""
    try:
      asyncio.run(self.async_callback(async_func, *args))
    except KeyboardInterrupt:
      self.logger.warning('Keyboard interrupt caught, terminating')

  def reset_job_state_on_ctrl_c(self):
    """Reset job state for jobs in flight"""
    temp_obj = SimpleDict()
    temp_obj.session_id = self.args.session_id  #pylint: disable=invalid-name
    attribs = ['state']
    temp_obj.state = 1

    self.logger.info('Resetting job state in DB for in flight jobs')

    if self.operation == Operation.COMPILE:
      state = 16
    elif self.operation == Operation.EVAL:
      state = 12

    query = gen_update_query(temp_obj, attribs,
                             self.dbt.job_table.__tablename__,
                             [('session', self.args.session_id),
                              ('state', state)])
    with DbSession() as session:

      #pylint: disable=duplicate-code
      def callback() -> bool:
        session.execute(query)
        session.commit()
        return True

      #pylint: enable=duplicate-code

      assert session_retry(session, callback, lambda x: x(), self.logger)
      self.logger.info('Sucessfully reset job state')
      return True

    return False

  def has_tunable_operation(self):
    """Check if current operation is a tuning operation"""
    raise NotImplementedError("Not implemented")

  def get_job_attr(self):
    """Get job attr for row selection"""
    job_attr: List[str] = None
    try:
      job_attr = [column.name for column in inspect(self.dbt.job_table).c]
      job_attr.remove("insert_ts")
      job_attr.remove("update_ts")
    except NoInspectionAvailable as error:
      self.logger.warning("Ignoring error for init_session: %s", error)
    return job_attr

  def check_jobs_found(self, job_rows: List[SimpleDict], find_state: List[Any],
                       session_id: int) -> bool:
    """check for end of jobs"""
    if not job_rows:
      # we are done
      self.logger.warning('No %s jobs found, session %s', find_state,
                          session_id)
      return False
    return True

  @lru_cache(1)
  def get_context_items(self):
    """Helper function to get items for celery job context"""
    kwargs = None
    f_vals = self.get_f_vals(Machine(local_machine=True), range(0), tuning=True)
    kwargs = self.get_kwargs(0, f_vals, tuning=True)
    return kwargs

  def serialize_jobs(self, session, batch_jobs):
    """Return list of serialize jobs"""
    raise NotImplementedError("Not implemented")

  def build_context(self, serialized_jobs):
    """Build context list for enqueue job"""
    raise NotImplementedError("Not implemented")

  def get_context_list(self, session, batch_jobs):
    """Return list of jobs (context) for celery queue"""

    context_list: List[dict] = None
    serialized_jobs = self.serialize_jobs(session, batch_jobs)
    #build context for each celery task
    context_list = self.build_context(serialized_jobs)

    return context_list

  async def parse_result(self, data):
    """Function callback for celery async jobs to store results"""
    data = json.loads(data)

    with DbSession() as session:
      try:
        fin_json = data['result']['ret']
        context = data['result']['context']
      except KeyError as kerr:
        self.logger.error(kerr)
        return False

      self.logger.info('Parsing: %s', fin_json)
      if self.operation == Operation.COMPILE:
        self.process_compile_results(session, fin_json, context)
      elif self.operation == Operation.EVAL:
        self.process_eval_results(session, fin_json, context)
      else:
        raise CustomError('Unsupported tuning operation')

      return True

  def process_compile_results(self, session, fin_json, context):
    """Process result from fin_build worker"""
    raise NotImplementedError("Not implemented")

  def process_eval_results(self, session, fin_json, context):
    """Process fin_json result"""
    raise NotImplementedError("Not implemented")
