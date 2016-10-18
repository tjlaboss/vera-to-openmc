# tests.py
#
# Use the functions below to test various features of the vera converter

import sys; sys.path.append('..')
import openmc
import vera_to_openmc
import functions
from isotopes import XS


def generate_materials(modtemp, fueltemp):
	'''Generate Uranium fuel (enriched to 3.1%), helium, zircalloy 4, and borated water.
	Inputs:
		modtemp:		moderator and cladding temperature in K
		fueltemp:		fuel temperature in K
	Outputs:
		materials:		list of instances of openmc.Material'''
	
	# helium
	he = openmc.Material(2, "helium")
	he.add_nuclide('he-4', 1, 'wo')
	he.set_density(0.1786E-3, "g/cc")
	he.temperature = modtemp
	
	# zircalloy4
	zirc = openmc.Material(3, "zircalloy-4")
	zirc.add_nuclide('cr-50', 4.17411E-05, 'wo')
	zirc.add_nuclide('cr-52', 8.36988E-04, 'wo')
	zirc.add_nuclide('cr-53', 9.67458E-05, 'wo')
	zirc.add_nuclide('cr-54', 2.45364E-05, 'wo')
	
	zirc.add_nuclide('fe-54', 1.18556E-04, 'wo')
	zirc.add_nuclide('fe-56', 1.92992E-03, 'wo')
	zirc.add_nuclide('fe-57', 4.53675E-05,	'wo')
	zirc.add_nuclide('fe-58', 6.14347E-06, 'wo')
	
	zirc.add_nuclide('zr-90', 4.98086E-01, 'wo')
	zirc.add_nuclide('zr-91', 1.09830E-01, 'wo')
	zirc.add_nuclide('zr-92', 1.69723E-01, 'wo')
	zirc.add_nuclide('zr-94', 1.75744E-01, 'wo')
	zirc.add_nuclide('zr-96', 2.89168E-02, 'wo')
	
	zirc.add_nuclide('sn-112', 1.32586E-04, 'wo')
	zirc.add_nuclide('sn-114', 9.18243E-05, 'wo')
	zirc.add_nuclide('sn-115', 4.77190E-05, 'wo')
	zirc.add_nuclide('sn-116', 2.05842E-03, 'wo')
	zirc.add_nuclide('sn-117', 1.09665E-03, 'wo')
	zirc.add_nuclide('sn-118', 3.48799E-03, 'wo')
	zirc.add_nuclide('sn-119', 1.24758E-03, 'wo')
	zirc.add_nuclide('sn-120', 4.77153E-03, 'wo')
	zirc.add_nuclide('sn-122', 6.89408E-04, 'wo')
	zirc.add_nuclide('sn-124', 8.76293E-04, 'wo')
	
	zirc.add_nuclide('hf-174', 1.55926E-07, 'wo')
	zirc.add_nuclide('hf-176', 5.18504E-06, 'wo')
	zirc.add_nuclide('hf-177', 1.84393E-05, 'wo')
	zirc.add_nuclide('hf-178', 2.71973E-05, 'wo')
	zirc.add_nuclide('hf-179', 1.36552E-05, 'wo')
	zirc.add_nuclide('hf-180', 3.53673E-05, 'wo')
	
	zirc.temperature = modtemp
	zirc.set_density(6.56, "g/cc")
	
	
	
	
	
	