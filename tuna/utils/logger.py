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
from tuna.metadata import TUNA_LOG_DIR


def setup_logger(logger_name='Tuna', add_streamhandler=False):
  """std setup for tuna logger"""
  log_level = os.environ.get('TUNA_LOGLEVEL', 'INFO').upper()
  logging.basicConfig(level=log_level)
  logger = logging.getLogger(logger_name)
  log_file = os.path.join(TUNA_LOG_DIR, logger_name + ".log")
  formatter = logging.Formatter(
      '%(asctime)s - %(name)s - %(levelname)s -  [%(filename)s:%(lineno)d] - %(message)s'
  )
  logger.propagate = False
  file_handler = logging.FileHandler(log_file, mode='a')
  file_handler.setFormatter(formatter)
  file_handler.setLevel(log_level.upper() if log_level else logging.INFO)
  logger.addHandler(file_handler)
  if add_streamhandler:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

  logger.setLevel(log_level.upper() if log_level else logging.DEBUG)
  return logger
