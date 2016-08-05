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



def convert_at_to_wt(mat):
	'''Convert atomic fraction to weight fraction for a material's isotopes
	
	Input:
		mat:	instance of objects.Material where mat.isotopes is < 0 (atomic frac)
	
	Output:
		mat:	same instance, but mat.isotopes is now in wt fraction
	'''

	import isotopes as topes
	total_at = sum(mat.isotopes.values())
	total_wt = 0.0
	iso_wts = {}

	if total_at >= 0:
		# already in weight fraction
		return mat
	else:
		for iso in mat.isotopes:
			total_wt += mat.isotopes[iso] * topes.MASS[iso]
		for iso in mat.isotopes:
			iso_wts[iso] = abs( mat.isotopes[iso] * topes.MASS[iso] / total_wt )
	
	mat.isotopes = iso_wts
	return mat




def mixture(materials, vfracs):
	'''Create a new material as a mixture of other materials
	
	Inputs:
		materials:		list/tuple of instances of objects.Material 
		vfracs:			list/tuple of the volume fractions of each Material
	
	Outputs:
		mixture:		instance of objects.Material that resulted
	'''
	
	mix_isotopes = {}
	
	for i in range(len(materials)):
		mat = materials[i]
		convert_at_to_wt(mat)
		wtf = vfracs[i]*mat.density 	# weight fraction of entire material
		for iso in mat.isotopes:
			new_wt = wtf*mat.isotopes[iso]
			if iso in mix_isotopes:
				mix_isotopes[iso] += new_wt
			else:
				mix_isotopes[iso] = new_wt
				
	
	mixture = None
	
	return None
	

	
	

