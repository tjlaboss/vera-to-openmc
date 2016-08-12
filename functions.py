# functions.py
#
# Module containing useful functions for read_xml.py and its modules

def clean(vera_list, type):
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

	
	

