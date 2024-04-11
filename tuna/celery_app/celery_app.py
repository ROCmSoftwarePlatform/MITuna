#!/usr/bin/env python3
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
"""Module to define celery app"""
import os
import subprocess
from celery import Celery
from celery.utils.log import get_task_logger

TUNA_CELERY_BROKER = 'mituna_redis'
TUNA_REDIS_PORT = '6379'

if 'TUNA_CELERY_BROKER' in os.environ:
  TUNA_CELERY_BROKER = os.environ['TUNA_CELERY_BROKER']
if 'TUNA_REDIS_PORT' in os.environ:
  TUNA_REDIS_PORT = os.environ['TUNA_REDIS_PORT']

app = Celery('celery_app',
             broker_url=f"redis://{TUNA_CELERY_BROKER}:{TUNA_REDIS_PORT}//",
             result_backend=f"redis://{TUNA_CELERY_BROKER}:{TUNA_REDIS_PORT}/",
             include=['tuna.miopen.celery_tuning.celery_tasks'])

app.conf.update(result_expires=3600,)
app.autodiscover_tasks()
app.conf.result_backend_transport_options = {'retry_policy': {'timeout': 5.0}}


def stop_active_workers():
  """Shutdown active workers"""
  if app.control.inspect().active() is not None:
    app.control.shutdown()

  return True


def purge_queue(q_names, logger):
  """Purge jobs in queue"""
  for q_name in q_names:
    try:
      logger.info('Purging Q %s', q_name)
      cmd = f"celery -A tuna.celery_app.celery_app purge -f -Q {q_name}".split(
          ' ')
      _ = subprocess.Popen(cmd)
    except Exception as ex:
      logger.info(ex)
      return False

  return True


if __name__ == '__main__':
  app.start()
