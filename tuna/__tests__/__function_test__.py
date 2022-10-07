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
""" test the function class """
from tuna.utils.function import Function
import matplotlib.pyplot as plt
import numpy
import pdb

f = Function(name='f', track_stats=True)
f.define(4, 5)
f.define(2, 90)
f.define(0, 33)
f.define(9, 18)
f.define(-1, -13)
f.define(-2, 19)

g = Function(name='g', track_stats=False)
g.define(9, 16)
g.define(4, 3)
g.define(-2, 15)
g.define(2, 16)
g.define(0, 30)
g.define(-1, -16)

print(f)
print(g)
print('relations')
print('f>g', f > g)
print('f>=g', f >= g)
print('f<g', f < g)
print('f<=g', f <= g)

if f.track_stats:
  assert f.max == numpy.max(list(f.f.values()))
  assert f.min == numpy.min(list(f.f.values()))
  assert f.argmax == list(f.f.keys())[numpy.argmax(list(f.f.values()))]
  assert f.argmin == list(f.f.keys())[numpy.argmin(list(f.f.values()))]
  assert f.sum == numpy.sum(list(f.f.values()))
  assert f.sumsq == numpy.sum([y**2 for y in list(f.f.values())])
  assert numpy.isclose(f.avg, numpy.mean(list(f.f.values())))
  assert numpy.isclose(f.std, numpy.std(list(f.f.values())))

print(f.to_str(max_length=3))

gdash = g.to_sorted()
print(list(gdash))

h = gdash.to_sorted(along='y',
                    nondecreasing=False,
                    set_name='h',
                    set_track_stats=True)
print(h)

if h.track_stats:
  assert h.max == numpy.max(list(h.f.values()))
  assert h.min == numpy.min(list(h.f.values()))
  assert h.argmax == list(h.f.keys())[numpy.argmax(list(h.f.values()))]
  assert h.argmin == list(h.f.keys())[numpy.argmin(list(h.f.values()))]
  assert h.sum == numpy.sum(list(h.f.values()))
  assert h.sumsq == numpy.sum([y**2 for y in list(h.f.values())])
  assert numpy.isclose(h.avg, numpy.mean(list(h.f.values())))
  assert numpy.isclose(h.std, numpy.std(list(h.f.values())))

print(h.domain)
print(h.image)
print(h.xvals)
print(h.yvals)

print(h.domain == gdash.domain)
print(h.image == gdash.image)
print(h.domain == Function('temp').domain)
print(h.image == f.image)

ax = plt.subplot()
h.plot(ax, title='Sample', xlabel='X Values', ylabel='Y Values')
plt.savefig('__delete_this_fig__.png')
