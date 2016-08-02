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




