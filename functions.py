# functions.py
#
# Module containing useful functions for read_xml.py and its modules

import numpy


def clean(vera_list, dtype = str):
	"""Lists in VERA decks are formatted as such:
	
		type="Array(string)" value="{U31,he,zirc4}"
	
	Usage: clean(value, str)
	Returns list"""
	
	clean_list = list(map(dtype, vera_list.strip('}').strip('{').split(',')))
	return clean_list


def calc_u234_u236_enrichments(w235):
	"""If the user does not specify the enrichments of U234 and U236 in the VERA
	input deck, they are automatically added to the fuel with the following formulas: 
	
		- Eq. 3.3.2:	w234 = 0.007731 * w235^1.0837
	
		- Eq. 3.3.3:	w236 = 0.0046 * w235
	 	
	This function replicates that calculation.
	
	Inputs:
		w235:		float; weight fraction of U235
	
	Outputs:
		w234, w236:	float; weight fractions of U234 and U236, respectively	"""
	
	w234 = 0.007731 * w235 ** 1.0837
	w236 = 0.0046   * w235
	
	return w234, w236


def fill_lattice(keys, lam, n = 0, dtype = object):
	"""Given a map of a lattice (such as a core map), fill it in with objects.
	
	Inputs:
		keys:			square map (nxn numpy.array) showing the location of objects
						within the lattice
		lam:			lambda function describing the operation on each key,
						such as a dictionary lookup
		n:          	integer; length of one side of the square map. [If not provided,
						will take the len() of one side of 'keys'.]
		dtype:          object class expected by the numpy.array
						[Default: object]
						
	Outputs:
		lattice:		nxn numpy.array of objects from 'dictionary' referred to by 'keys'
	"""
	
	if not n:
		n = len(keys)
	
	lattice = numpy.empty((n, n), dtype)
	for j in range(n):
		for i in range(n):
			c = keys[j][i]
			lattice[j, i] = lam(c)
	
	return lattice


def replace_lattice(new_keys, original, lam = None, n = 0, dtype = object, blank = "-"):
	"""Same as fill_lattice, but instead of performing a function on the key,
	substitutes the key from 'new_keys' into 'original' unless the key=='blank'."""
	
	if not n:
		n = len(original)
	if not lam:
		lam = lambda i, j: new_keys[i][j]
		
	lattice = numpy.empty((n, n), dtype)
	for i in range(n):
		for j in range(n):
			k = new_keys[i][j]
			if k == blank:
				lattice[j, i] = original[i][j]
			else:
				lattice[j, i] = lam(i, j)
	
	return lattice


def shape(raw_list, shape_map, blank = "-"):
	"""Turn an oddly-shaped list into one suitable for a square map.
	Warning: this does not check to verify if they are of compatible lengths.
	
	Inputs:
		raw_list:	the list that needs to be shaped
		shape_map:	instance of objects.CoreMap describing the arbitrary shape
					that raw_list follows.
		blank:		string to be inserted in assm_map
		
	Output:
		nice_list:	list of len=len(shape_map)^2
	"""
	count = 0
	n = len(shape_map)
	nice_list = [None,]*n**2
	for j in range(n):
		for i in range(n):
			k = j*n + i		# index within nice_list
			if shape_map[j][i]:
				nice_list[k] = raw_list[count]
				count += 1
			else:
				nice_list[k] = blank
	return nice_list
	


def set_nuclide_xs(material, xstring):
	"""Set the cross section for each nuclide of a material.
	
	This function has more or less been deprecated and may be removed
	in future releases without notice.
	
	Inputs:
		material:		instance of openmc.Material
		xstring:		string; identifier of the cross section to use
	Outputs:
		None: modifies the Material directly"""
	for n in material.nuclides:
		n[0].xs = xstring


def select_nearest_temperature(temp, dictionary):
	avail_temps = tuple(map(float, dictionary.keys()))
	n = len(avail_temps)
	diff = [None, ] * n
	for t in range(n):
		diff[t] = abs(temp - avail_temps[t])
	for t in range(n):
		if diff[t] == min(diff):
			tkey = str(int(avail_temps[t]))
			break
	return dictionary[tkey]
