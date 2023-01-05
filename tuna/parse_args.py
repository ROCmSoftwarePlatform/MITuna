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
""" Module to centralize command line argument parsing """
import argparse
import sys
from enum import Enum
from typing import List
from tuna.config_type import ConfigType


class TunaArgs(Enum):
  """ Enumeration of all the common argument supported by setup_arg_parser """
  ARCH = 0
  NUM_CU = 1
  DIRECTION = 2
  VERSION = 3
  CONFIG_TYPE = 4
  SESSION_ID = 5
  MACHINES = 6
  REMOTE_MACHINE = 7


def setup_arg_parser(desc: str, arg_list: List[TunaArgs], parser=None):
  """ function to aggregate common command line args """
  if parser is not None:
    parser = argparse.ArgumentParser(description=desc,
                                     parents=parser,
                                     conflict_handler='resolve')
  else:
    parser = argparse.ArgumentParser(description=desc)
  if TunaArgs.ARCH in arg_list:
    parser.add_argument(
        '-a',
        '--arch',
        type=str,
        dest='arch',
        default=None,
        required=False,
        help='Architecture of machines',
        choices=['gfx900', 'gfx906', 'gfx908', 'gfx1030', 'gfx90a'])
  if TunaArgs.NUM_CU in arg_list:
    parser.add_argument('-n',
                        '--num_cu',
                        dest='num_cu',
                        type=int,
                        default=None,
                        required=False,
                        help='Number of CUs on GPU',
                        choices=[36, 56, 60, 64, 104, 110, 120])
  if TunaArgs.DIRECTION in arg_list:
    parser.add_argument(
        '-d',
        '--direction',
        type=str,
        dest='direction',
        default=None,
        help='Direction of tunning, None means all (fwd, bwd, wrw), \
                          fwd = 1, bwd = 2, wrw = 4.',
        choices=[None, '1', '2', '4'])
  if TunaArgs.CONFIG_TYPE in arg_list:
    parser.add_argument('-C',
                        '--config_type',
                        dest='config_type',
                        help='Specify configuration type',
                        default=ConfigType.convolution,
                        choices=ConfigType,
                        type=ConfigType)
  if TunaArgs.SESSION_ID in arg_list:
    parser.add_argument(
        '--session_id',
        action='store',
        type=int,
        dest='session_id',
        help=
        'Session ID to be used as tuning tracker. Allows to correlate DB results to tuning sessions'
    )
  if TunaArgs.MACHINES in arg_list:
    parser.add_argument('-m',
                        '--machines',
                        dest='machines',
                        type=str,
                        default=None,
                        required=False,
                        help='Specify machine ids to use, comma separated')
  if TunaArgs.REMOTE_MACHINE in arg_list:
    parser.add_argument('--remote_machine',
                        dest='remote_machine',
                        action='store_true',
                        default=False,
                        help='Run the process on a network machine')

  return parser


def clean_args(opt1='MIOPEN', opt2='miopen'):
  """clean arguments"""
  if opt1 in sys.argv:
    sys.argv.remove(opt1)
  if opt2 in sys.argv:
    sys.argv.remove(opt2)


def args_check(args, parser):
  """Common scripts args check function"""
  if args.machines is not None:
    args.machines = [int(x) for x in args.machines.split(',')
                    ] if ',' in args.machines else [int(args.machines)]

  args.local_machine = not args.remote_machine

  if args.init_session and not args.label:
    parser.error(
        "When setting up a new tunning session the following must be specified: "\
        "label.")
