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
"""logger file"""
import logging
import os
from typing import Union
from logstash_async.handler import AsynchronousLogstashHandler
from logstash_async.handler import LogstashFormatter
from tuna.utils.metadata import TUNA_LOG_DIR


def get_logstash_config():
  """retrieve env vars for logstash"""
  logstash_status = os.getenv('TUNA_LOGSTASH_STATUS', 'false').lower() == 'true'
  logstash_host = os.getenv('TUNA_LOGSTASH_HOST', 'localhost')
  logstash_port = int(os.getenv('TUNA_LOGSTASH_PORT', "5000"))
  logstash_path = os.getenv('TUNA_LOGSTASH_PATH', None)
  return logstash_status, logstash_host, logstash_port, logstash_path


def add_logstash_handler(logger: logging.Logger, host: str, port: int,
                         path: str):
  """add logstash handker for logs streams"""
  logstash_handler = AsynchronousLogstashHandler(host=host,
                                                 port=port,
                                                 database_path=path)
  logstash_formatter = LogstashFormatter()
  logstash_handler.setFormatter(logstash_formatter)
  logstash_handler.setLevel(logging.INFO)
  logger.addHandler(logstash_handler)


def setup_logger(logger_name: str = 'Tuna',
                 add_streamhandler: bool = True,
                 add_filehandler: bool = False) -> logging.Logger:
  """std setup for tuna logger"""
  log_level: str = os.environ.get('TUNA_LOGLEVEL', 'INFO').upper()
  logging.basicConfig(level=log_level)
  logger: Union[logging.Logger,
                logging.RootLogger] = logging.getLogger(logger_name)
  log_file: str = os.path.join(TUNA_LOG_DIR, logger_name + ".log")
  formatter: logging.Formatter = logging.Formatter(
      '%(asctime)s - %(name)s - %(levelname)s -  [%(filename)s:%(lineno)d] - %(message)s'
  )
  logger.propagate = False

  if add_filehandler:
    file_handler: logging.FileHandler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level.upper() if log_level else logging.INFO)
    logger.addHandler(file_handler)

  if add_streamhandler:
    stream_handler: logging.StreamHandler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    if not logger.hasHandlers():
      logger.addHandler(stream_handler)

  logstash_status, logstash_host, logstash_port, logstash_path = get_logstash_config(
  )

  if logstash_status:
    add_logstash_handler(logger, logstash_host, logstash_port, logstash_path)
    logger.info("Logstash is enabled. Sending logs to %s:%d", logstash_host,
                logstash_port)

  logger.setLevel(log_level.upper() if log_level else logging.DEBUG)
  return logger


def set_usr_logger(logger_name: str) -> logging.Logger:
  """utility function to create worker interface logger object"""
  log_level: str = os.environ.get('TUNA_WORKER_INTERFACE_LOGLEVEL', "INFO")
  lgr: Union[logging.Logger,
             logging.RootLogger] = logging.getLogger(logger_name)
  log_file: str = os.path.join(TUNA_LOG_DIR, logger_name + ".log")
  fmt: logging.Formatter = logging.Formatter(
      '%(lineno)d - %(asctime)s - %(name)s - %(message)s')
  file_handler: logging.FileHandler = logging.FileHandler(log_file, mode='a')
  file_handler.setFormatter(fmt)
  file_handler.setLevel(log_level.upper() if log_level else logging.INFO)
  stream_handler: logging.StreamHandler = logging.StreamHandler()
  stream_handler.setFormatter(fmt)
  stream_handler.setLevel(logging.INFO)
  lgr.addHandler(file_handler)
  lgr.addHandler(stream_handler)

  logstash_status, logstash_host, logstash_port, logstash_path = get_logstash_config(
  )

  if logstash_status:
    add_logstash_handler(lgr, logstash_host, logstash_port, logstash_path)
    lgr.info("Logstash is enabled. Sending logs to %s:%d", logstash_host,
             logstash_port)

  lgr.setLevel(log_level.upper() if log_level else logging.DEBUG)
  return lgr
