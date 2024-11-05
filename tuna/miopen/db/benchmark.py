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
""" Module for defining benchmark and model enums """

from enum import Enum as pyenum
from sqlalchemy import Column, UniqueConstraint
from sqlalchemy import Enum, Float
from tuna.dbBase.base_class import BASE


#pylint: disable=too-few-public-methods
class FrameworkEnum(pyenum):
  """Represents framework enums"""
  PYTORCH = 'Pytorch'
  TENSORFLOW = 'Tensorflow'
  MIGRAPH = 'MIGraph'
  CAFFE2 = 'CAFEE2'

  def __str__(self):
    return self.value


class Framework(BASE):
  """Represents framework table"""
  __tablename__ = "framework"
  __table_args__ = (UniqueConstraint("framework", name="uq_idx"),)
  framework = Column(Enum(FrameworkEnum), nullable=False)
  version = Column(Float, nullable=False)


class ModelEnum(pyenum):
  """Represents model enums.
  Naming scheme: Upper case first letter
                 If not first letter, all lower case
                 Refrain from adding version, there is a field for that.
  """
  RESNET50 = 'Resnet50'
  RESNEXT101 = 'Resnext101'
  VGG16 = 'Vgg16'
  VGG19 = 'Vgg19'
  ALEXNET = 'Alexnet'
  GOOGLENET = 'Googlenet'
  INCEPTION3 = 'Inception3'
  INCEPTION4 = 'Inception4'
  MASKRCNN = 'Mask-r-cnn'
  SHUFFLENET = 'Shufflenet'
  SSD = 'Ssd'
  MOBILENET = 'Mobilenet'
  RESNET101 = 'Resnet101'
  RESNET152 = 'Resnet152'
  VGG11 = 'Vgg11'
  DENSENET = 'Densenet'
  DENSENET201 = 'Densenet201'
  ATOA_SMALL = 'Atoa_small'
  ATOA_MEDIUM = 'Atoa_medium'
  PEAK = 'Peak'
  DENSENET121 = 'Densenet121'
  DENSENET161 = 'Densenet161'
  DENSENET169 = 'Densenet169'
  MNASNET0_5 = 'Mnasnet0_5'
  MNASNET0_75 = 'Mnasnet0_75'
  MNASNET1_5 = 'Mnasnet1_0'
  MNASNET1_3 = 'Mnasnet1_3'
  RESNET18 = 'Resnet18'
  RESNET34 = 'Resnet34'
  VGG13 = 'Vgg13'
  RESNEXT101_32x8d = 'Resnext101_32x8d'
  RESNET50_32X4D = 'Resnext50_32x4d'
  SHUFFLENET_V2_X0_5 = 'Shufflenet_v2_x0_5'
  SHUFFLENET_V2_X1_0 = 'Shufflenet_v2_x1_0'
  SHUFFLENET_V2_X1_5 = 'Shufflenet_v2_x1_5'
  SHUFFLENET_V2_X2_0 = 'Shufflenet_v2_x2_0'
  SQUEEZENET1_0 = 'Squeezenet1_0'
  SQUEEZENET1_1 = 'Squeezenet1_1'
  WIDE_RESNET101_2 = 'Wide_resnet101_2'
  WIDE_RESNET50_2 = 'Wide_resnet50_2'
  CVT = "Cvt"
  MASKCNN = "Maskcnn"
  MASKRNN = "Maskrnn"
  RETINANET = 'Retinanet'

  def __str__(self):
    return self.value


class Model(BASE):
  """Represents model table"""
  __tablename__ = "model"
  __table_args__ = (UniqueConstraint("model", "version", name="uq_idx"),)
  model = Column(Enum(ModelEnum), nullable=False)
  version = Column(Float, nullable=False)
