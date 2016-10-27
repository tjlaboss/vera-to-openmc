# functions.py
#
# Module containing useful functions for read_xml.py and its modules

def clean(vera_list, type = str):
	'''Lists in VERA decks are formatted as such: 
	
		type="Array(string)" value="{U31,he,zirc4}"
	
	Usage: clean(value, str)
	Returns list'''
	
	clean_list = list(map(type, vera_list.strip('}').strip('{').split(',')))
	return clean_list


def calc_u234_u236_enrichments(w235):
	'''If the user does not specify the enrichments of U234 and U236 in the VERA
	input deck, they are automatically added to the fuel with the following formulas: 
	
		- Eq. 3.3.2:	w234 = 0.007731 * w235^1.0837
	
		- Eq. 3.3.3:	w236 = 0.0046 * w235
	 	
	This function replicates that calculation.
	
	Inputs:
		w235:		float; weight fraction of U235
	
	Outputs:
		w234, w236:	float; weight fractions of U234 and U236, respectively	'''
	
	w234 = 0.007731 * w235**1.0837
	w236 = 0.0046   * w235
	
	return w234, w236


def fill_lattice(keys, lam, n=0):
	'''Given a map of a lattice (such as a core map), fill it in with objects.
	
	Inputs:
		keys:			square map (nxn list of lists) showing the location of objects
						within the lattice
		lam:			lambda function describing the operation on each key,
						such as a dictionary lookup
		n (optional):	integer; length of one side of the square map. If not provided,
						will take the len() of one side of 'keys'.
						
	Outputs:
		lattice:		nxn list of objects from 'dictionary' referred to by 'keys'		
	'''
	
	if not n:
		n = len(keys)
	
	lattice = [[None,]*n]*n
	for i in range(n):
		new_row = [None,]*n
		for j in range(n):
			c = keys[i][j]
			new_row[j] = lam(c)
		lattice[i] = new_row
	
	return lattice


def replace_lattice(new_keys, original, lam = None, n=0, blank = "-"):
	'''Same as fill_lattice, but instead of performing a function on the key,
	substitutes the key from 'new_keys' into 'original' unless the key=='blank'. '''
	if not n:
		n = len(original)
	if not lam:
		lam = lambda i,j: new_keys[i][j]
	
	lattice = [[None,]*n]*n
	for i in range(n):
		new_row = [None,]*n
		for j in range(n):
			k = new_keys[i][j]
			if k == blank:
				new_row[j] = original[i][j]
			else:
				new_row[j] = lam(i,j)
		lattice[i] = new_row
	
	return lattice


"""
def replace_cell(pin_key, dictionary, orig_val, blank = "-"):
	'''VERA represents areas with no insertion as "-".
	This function is necessary to perform replacements only where
	the key in the map is not this character.'''
	if pin_key != blank:
		return dictionary[pin_key]
	else:
		return orig_val
"""


def set_nuclide_xs(material, xstring):
	'''Set the cross section for each nuclide of a material.
	Inputs:
		material:		instance of openmc.Material
		xstring:		string; identifier of the cross section to use
	Outputs:
		None: modifies the Material directly'''
	for n in material.nuclides:
		n[0].xs = xstring


def select_nearest_temperature(temp, dictionary):
	avail_temps = tuple(map(float, dictionary.keys()))
	n = len(avail_temps)
	diff = [None,]*n
	for t in range(n):	diff[t] = abs(temp - avail_temps[t])
	for t in range(n):
		if diff[t] == min(diff):
			tkey = str(int(avail_temps[t]))
			break
	return dictionary[tkey]
	

