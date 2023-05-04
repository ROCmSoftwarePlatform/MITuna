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
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Query
from sqlalchemy.sql import Select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

sys.path.append("../tuna")
sys.path.append("tuna")

this_path = os.path.dirname(__file__)

from unittest.mock import MagicMock

from tuna.miopen.subcmd.export_db import arg_export_db, get_filename
from tuna.miopen.subcmd.export_db import get_base_query, get_fdb_query
from tuna.utils.db_utility import get_id_solvers, DB_Type
from tuna.miopen.db.tables import MIOpenDBTables
from tuna.miopen.parse_miopen_args import get_export_db_parser


@pytest.fixture
def remove_tuna_directory():
  yield
  if os.path.exists("tuna_1.0.0"):
    os.rmdir("tuna_1.0.0")


def test_get_file(remove_tuna_directory):
  arch = "gfx900"
  num_cu = 64
  filename = None
  ocl = True
  db_type = DB_Type.FIND_DB

  expeted_filename = "tuna_1.0.0/gfx900_64.OpenCL.fdb.txt"
  actual_filename = get_filename(arch, num_cu, filename, ocl, db_type)

  assert actual_filename == expeted_filename, f"expected {expeted_filename}, but got {actual_filename}"
  assert os.path.exists("tuna_1.0.0"), "directory 'tuna_10.0.0' not created"


@pytest.fixture
def mock_db_tables():
  db_tables = MIOpenDBTables()
  db_tables.find_db_table = MagicMock()
  db_tables.golden_table = MagicMock()
  db_tables.config_table = MagicMock()
  db_tables.config_tags_table = MagicMock()
  db_tables.solver_table = MagicMock()
  db_tables.kernel_cache = MagicMock()
  db_tables.session = MagicMock()
  return db_tables


@pytest.fixture
def mock_args():
  args = argparse.Namespace()
  args.golden_v = None
  args.arch = "arch"
  args.num_cu = 64
  args.opencl = 1
  args.config_tag = None
  args.filename = None
  return args


def test_get_base_query(mock_db_tables, mock_args, caplog):
  caplog.set_level(logging.INFO)
  logger = logging.getLogger("test_logger")
  query = get_base_query(mock_db_tables, mock_args, logger)
  assert query is not None, "Query object is None"
  assert isinstance(
      query,
      Query), f"epected query to be an instance of Query, Got {type(query)}"
  logs = [
      record.message for record in caplog.records if record.levelname == 'INFO'
  ]
  assert len(logs) > 0, "No logs must contains at least one record"


"""
def test_get_fdb_query(mock_db_tables, mock_args, caplog):
    caplog.set_level(logging.INFO)
    logger = logging.getLogger("test_logger")
    query = get_fdb_query(mock_db_tables, mock_args, logger)
    assert query is not None, "Query object is None"
    assert isinstance(query, Query), f"epected query to be an instance of Query, Got {type(query)}"
"""
