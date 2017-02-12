"""
    This file is part of Picopore.

    Picopore is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Picopore is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Picopore.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import print_function
import os
import numpy as np

def log(message, end='\n'):
	print(message, end=end)

def recursiveFindFast5(input):
	files = []
	for path in input:
		if os.path.isdir(path):
			files.extend(recursiveFindFast5(os.listdir(path)))
		elif os.path.isfile(path) and path.endswith(".fast5"):
			files.append(path)
	return files

def isGroup(object):
	return type(object).__name__ == "Group"
	
def getUIntDtype(num):
	if num < 2**8:
		name='uint8'
	elif num < 2**16:
		name='uint16'
	elif num < 2**32:
		name='uint32'
	else:
		name='uint64'
	return np.dtype(name)

def getIntDtype(num):
	if abs(num) < 2**7:
		name='int8'
	elif abs(num) < 2**15:
		name='int16'
	elif abs(num) < 2**31:
		name='int32'
	else:
		name='int64'
	return np.dtype(name)
	
def getDtype(data):
	if type(data).__name__ in ['list', 'ndarray']:
		if type(data[0]).__name__ in ['int', 'int4', 'int8', 'int16', 'int32', 'int64']:
			if min(data) > 0:
				return getUIntDtype(max(data))
			else:
				return getIntDtype(max(data))
		elif type(data[0]).__name__ == 'str':
			return '|S{}'.format(max([len(i) for i in data]) + 1)
	if type(data).__name__ in ['int', 'int4', 'int8', 'int16', 'int32', 'int64']:
		if data > 0:
			return getUIntDtype(data)
		else:
			return getIntDtype(data)
	elif type(data).__name__ == 'str':
		return '|S{}'.format(len(data))
	else:
		# TODO: float?
		return None

def recursiveFindDatasets(group, keyword):
	eventPaths = []
	if isGroup(group):
		for subgroup in group.values():
			eventPaths.extend(recursiveFindDatasets(subgroup, keyword))
	elif group.name.endswith(keyword):
		eventPaths.append(group.name)
	return eventPaths

def findDatasets(f, group_id, keyword="Events", entry_point="Analyses"):
	eventPaths = []
	try:
		analyses = f.get(entry_point)
		for group in analyses.values():
			if group_id == "all" or group.endswith(group_id):
				eventPaths.extend(recursiveFindDatasets(group, keyword))
	except AttributeError:
		# no analyses, dont worry
		pass
	return eventPaths
	
def rewriteDataset(f, path, compression="gzip", compression_opts=1, dataset=None):
	attrs = f.get(path).attrs
	dataset = f.get(path).value if dataset is None else dataset
	del f[path]
	f.create_dataset(path, data=dataset, dtype=dataset.dtype, compression=compression, compression_opts=compression_opts)
	for name, value in attrs.items():
		f[path].attrs[name] = value
		
def recursiveCollapseGroups(f, basegroup, path, group):
	for subname, object in group.items():
		subpath = "{}.{}".format(path, subname)
		if isGroup(object):
			recursiveCollapseGroups(f, basegroup, subpath, object)
		else:
			f.move(object.name, "{}/{}".format(basegroup, subpath))
	for k, v in group.attrs.items():
		f[basegroup].attrs.create("{}.{}".format(path, k), v, dtype=getDtype(v))
	del f[group.name]

def uncollapseGroups(f, basegroup):
	for name, object in basegroup.items():
		f.move("{}/{}".format(basegroup.name, name), name.replace(".", "/")) # TODO: does this include basegroup?
	for k, v in basegroup.attrs.items():
		k = k.split(".")
		groupname = "/".join(k[:-1])
		attrname = k[-1]
		try:
			f.create_group(groupname)
		except ValueError as e:
			if e.message == "Unable to create group (Name already exists)":
				pass
			else:
				raise e
		f[groupname].attrs.create(attrname, v, dtype=getDtype(v))
	del f[basegroup.name]
