# tests.py
#
# Use the functions below to test various features of the vera converter

import sys; sys.path.append('..')
import openmc
import vera_to_openmc
import functions
import isotopes


def generate_materials(modtemp, fueltemp):
	'''Generate Uranium fuel (enriched to 3.1%), helium, zircalloy 4, and borated water.
	Inputs:
		modtemp:		moderator and cladding temperature in K
		fueltemp:		fuel temperature in K
	Outputs:
		materials:		list of instances of openmc.Material'''
	
	# helium
	he = openmc.Material(2, "helium")
	he.add_nuclide('He4', 1, 'wo')
	he.set_density("g/cc", 0.1786E-3)
	he.temperature = modtemp
	
	# zircalloy4
	zirc = openmc.Material(4, "zircalloy-4")
	zirc.add_nuclide('Cr50', 4.17411E-05, 'wo')
	zirc.add_nuclide('Cr52', 8.36988E-04, 'wo')
	zirc.add_nuclide('Cr53', 9.67458E-05, 'wo')
	zirc.add_nuclide('Cr54', 2.45364E-05, 'wo')
	
	zirc.add_nuclide('Fe54', 1.18556E-04, 'wo')
	zirc.add_nuclide('Fe56', 1.92992E-03, 'wo')
	zirc.add_nuclide('Fe57', 4.53675E-05, 'wo')
	zirc.add_nuclide('Fe58', 6.14347E-06, 'wo')
	
	zirc.add_nuclide('Zr90', 4.98086E-01, 'wo')
	zirc.add_nuclide('Zr91', 1.09830E-01, 'wo')
	zirc.add_nuclide('Zr92', 1.69723E-01, 'wo')
	zirc.add_nuclide('Zr94', 1.75744E-01, 'wo')
	zirc.add_nuclide('Zr96', 2.89168E-02, 'wo')
	
	zirc.add_nuclide('Sn112', 1.32586E-04, 'wo')
	zirc.add_nuclide('Sn114', 9.18243E-05, 'wo')
	zirc.add_nuclide('Sn115', 4.77190E-05, 'wo')
	zirc.add_nuclide('Sn116', 2.05842E-03, 'wo')
	zirc.add_nuclide('Sn117', 1.09665E-03, 'wo')
	zirc.add_nuclide('Sn118', 3.48799E-03, 'wo')
	zirc.add_nuclide('Sn119', 1.24758E-03, 'wo')
	zirc.add_nuclide('Sn120', 4.77153E-03, 'wo')
	zirc.add_nuclide('Sn122', 6.89408E-04, 'wo')
	zirc.add_nuclide('Sn124', 8.76293E-04, 'wo')
	
	zirc.add_nuclide('Hf174', 1.55926E-07, 'wo')
	zirc.add_nuclide('Hf176', 5.18504E-06, 'wo')
	zirc.add_nuclide('Hf177', 1.84393E-05, 'wo')
	zirc.add_nuclide('Hf178', 2.71973E-05, 'wo')
	zirc.add_nuclide('Hf179', 1.36552E-05, 'wo')
	zirc.add_nuclide('Hf180', 3.53673E-05, 'wo')
	
	zirc.temperature = modtemp
	zirc.set_density("g/cc", 6.56)
	
	# Uranium fuel - 3.1% enriched
	# Fuel is UO2 pellets
	un = 1
	u235 = 3.1/100
	u234 = 0.026347/100
	u236 = 0.0046*u235 
	u238 = 1 - (u235 + u234 + u236)
	u_gross = 0
	u_gross += u235*isotopes.MASS["U235"]
	u_gross += u234*isotopes.MASS["U234"]
	u_gross += u236*isotopes.MASS["U236"]
	u_gross += u238*isotopes.MASS["U238"]
	
	on = 2
	o_gross = isotopes.MASS["O16"]
	
	u_wt = u_gross*un/(un*u_gross+on*o_gross)
	o_wt = o_gross*on/(un*u_gross+on*o_gross)
	
	fuel = openmc.Material(3, "UO2 - 3.1%")
	fuel.add_nuclide('U235', u235*u_wt, 'wo')
	fuel.add_nuclide('U234', u234*u_wt, 'wo')
	fuel.add_nuclide('U236', u236*u_wt, 'wo')
	fuel.add_nuclide('U238', u238*u_wt, 'wo')
	fuel.add_nuclide('O16',  o_wt, 'wo')
	fuel.set_density("g/cc", 10.257*0.945)
	fuel.temperature = fueltemp
	
	
	# Borated Moderator
	# H2O + boron
	ppm = 1300 
	b_wt = ppm * 1E-6
	b10 = 1.84309E-01 * b_wt
	b11 = 8.15691E-01 * b_wt
	
	
	h2o_wt = 1 - b_wt
	h_gross = isotopes.MASS["H1"]
	h2o_gross = 2*h_gross + 1*o_gross
	h_wt = h2o_wt * 2*h_gross/h2o_gross
	o_wt = h2o_wt * 1*o_gross/h2o_gross
	
	mod = openmc.Material(1, "mod")
	mod.add_nuclide("B10", b10, 'wo')
	mod.add_nuclide("B11", b11, 'wo')
	mod.add_nuclide("H1", h_wt, 'wo')
	mod.add_nuclide("O16", o_wt, 'wo')
	mod.set_density("g/cc", 0.661)
	mod.temperature = 326.85
	
	return mod, he, fuel, zirc
	
	

materials = generate_materials(600, 600)
print(materials)
	
	
	
	
	
	
	