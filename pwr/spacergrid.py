# Spacer Grid
# 
# Module containing the classes and methods for modeling of PWR spacer grids,
# for use in the Assembly class (assembly.py)

from pwr.functions import duplicate, get_plane
import openmc
from math import sqrt

class SpacerGrid(object):
	'''Object to hold properties of an assembly's spacer grids
	
	Parameters:
		key: 		string; unique name of this spacer grid
		height:		float; height (cm) of the spacer around the pins
		mass:		float; mass in g of the entire spacer grid's material
		material:	instance of class openmc.Material
		pitch:		float; pin pitch (cm) 
		npins:		number of pins across an assembly
	Attributes:
		(key, height, mass, material - as above)
		thickness:	float; thickness (cm) of the grid around each pin, 
					or half the total thickness between pins
		'''
	
	def __init__(self, key, height, mass, material, pitch, npins):
		self.key = key	
		self.height = height	
		self.mass = mass		
		self.material = material
		self.thickness = self.calculate_thickness(pitch, npins)
	
	def calculate_thickness(self, pitch, npins):
		'''Calculate the thickness of the spacer surrounding each pincell.
		Inputs:
			pitch:		float; pin pitch (cm)
			npins:		int; number of pins across Assembly (npinsxnpins)
		'''
		
		''' Method:
		
		Volume = mass / density;		Combined Area = Volume / height
			Therefore, [ A = m/rho/h ],		and the area around a single pincell:
												a = m/rho/h / npins^2
			
			The area of the spacer material around one cell can also be found:
				a = p^2 - (p - 2*t)^2,		where 't' is the thickness and 'p' is the pitch
			->  a = p^2 - [p^2 - 4*t*p + 4*t^2]
			->  a = 4*t*p - 4*t^2
				
			Equate the two expressions for a:
				m/rho/h / npins^2 = 4*t*p - 4*t^2
			Then solve for 't' using the quadratic equation:
			
			              [             (          m/rho/h   ) ]
				t = 0.5 * [ p  +/- sqrt ( p^2 -   ---------- ) ]
				          [             (          npins^2   ) ]
        '''
		
		A = self.mass / self.material.density / self.height
		t = 0.5*(pitch - sqrt(pitch**2 - A/npins**2))
		return t
		
	def __str__(self):
		name = self.key + ': ' + str(self.thickness) + " cm"
		return name


def add_spacer_to(pincell, pitch, t, material, counter, surflist):# = []):
	'''Given a pincell to be placed in a lattice, add
	the spacer grid to the individual cell.
	
	Inputs:
		pincell:	instance of openmc.Universe describing the pincell
					and its concentric rings of instances of openmc.Cell
		pitch:		float; pin pitch in cm
		t:			float; thickness in cm of one edge of the spacer between
					two pincells (HALF the total thickness)
		material:	instance of openmc.Material from which the spacer is made
		counter:	instance of Counter to keep track of universe numbers
		surflist:	list of existing OpenMC surfaces. [Default: empty list]
					This is optional, but strongly recommended if you are adding
					spacers to more than one pin cell.
	
	Output:
		new_pin:	instance of openmc.Universe describing the pincell
					surrounded by the spacer
	'''
	assert isinstance(pincell, openmc.Universe), str(pincell) + "must be an openmc.Universe (not a Cell)"
	assert isinstance(material, openmc.Material), str(material) + "is not an instance of openmc.Material" 
	
	orig_list = list(pincell.cells.values())
	
	# Create necessary planes
	p = pitch / 2.0
	print("top out", p, "top in", p-t, "bot in", -p+t, "bot out", -p)
	print("left out", -p, "left in", -p+t, "right in", p-t, "right out", p)
	'''
	top_out = get_plane(surflist, counter, 'y',  p)
	top_in  = get_plane(surflist, counter, 'y',  p - t)
	bot_in  = get_plane(surflist, counter, 'y', -p + t)
	bot_out = get_plane(surflist, counter, 'y', -p)
	left_out  = get_plane(surflist, counter, 'x', -p)		# He feels left out
	left_in   = get_plane(surflist, counter, 'x', -p + t)
	right_in  = get_plane(surflist, counter, 'x',  p - t)
	right_out = get_plane(surflist, counter, 'x',  p)
	'''
	top_out = get_plane(surflist, counter, 'y',  p)
	top_in  = get_plane(surflist, counter, 'y',  p - t)
	bot_in  = get_plane(surflist, counter, 'y', -p + t)
	bot_out = get_plane(surflist, counter, 'y', -p)
	left_out  = get_plane(surflist, counter, 'x', -p)		# He feels left out
	left_in   = get_plane(surflist, counter, 'x', -p + t)
	right_in  = get_plane(surflist, counter, 'x',  p - t)
	right_out = get_plane(surflist, counter, 'x',  p)
	
	# Get the outermost (mod) Cell of the pincell
	mod_cell = duplicate(orig_list[-1], counter)
	mod_cell.name += " (gridded)"
	
	# Make a cell encompassing the 4 sides of the spacer
	spacer = openmc.Cell(counter.add_cell(), name = pincell.name + " spacer")
	spacer.region = (+left_out	& +top_in 	& -top_out	&	-right_out) | \
					(+right_in	& -right_out& +bot_in	& 	-top_in)	| \
					(+left_out	& -left_in	& +bot_in	&	-top_in)	| \
					(+bot_out 	& -bot_in	& +left_out	&	-right_out )  
					#& mod_cell.region	# top; bottom; right; left; #outside cylinder	 
	spacer.fill = material
	
	# Then fix the moderator cell to be within the bounds of the spacer
	#mod_cell.region = mod_cell.region & \
	#				(+bot_in	& +left_in	& -top_in	& -right_in )
	mod_cell.region &= (+bot_in	& +left_in	& -top_in	& -right_in )
	
	new_pin = openmc.Universe(counter.add_universe(), name = pincell.name + " gridded")
	# Add all of the original cells except the old mod cell
	for i in range(len(orig_list) - 1):
		new_pin.add_cell(orig_list[i])
	new_pin.add_cell(mod_cell) 	# the new mod cell
	new_pin.add_cell(spacer)
	
	return new_pin


def add_grid_to(lattice, pitch, npins, spacer, counter, surflist):# = []):
	'''Add a spacer to every pincell in the lattice.
	FIXME: Determine 'pitch' and 'npins' from the attributes of 'lattice'

	Inputs:
		lattice:		instance of openmc.RectLattice
		pitch:			float; its pitch (cm)
		npins:			int; number of pins across
		spacer:		instance of SpacerGrid
		counter:		instance of Counter
		surflist:		list of instances of openmc.Surface to check against.
						Optional, but strongly recommended.
	Output:
		gridded:		instance of openmc.RectLattice with the grid applied
						to every cell'''
	
	assert isinstance(lattice, openmc.RectLattice), "'lattice' must be a RectLattice."
	assert isinstance(spacer, SpacerGrid), "'spacer' must be an instance of SpacerGrid."
	n = int(npins)
	new_universes = [[None,]*n,]*n
	
	for j in range(n):
		row = new_universes[j]
		for i in range(n):
			old_cell = lattice.universes[j][i]
			key = str(old_cell.id)
			
			#debug
			if lattice.name == "PLUG":
				if key not in old_cell.griddict:
					print("Cell", key, "is not in old_cell.griddict...generating")
				
			
			if key in old_cell.griddict:
				new_cell = old_cell.griddict[key]
			else:
				new_cell = add_spacer_to(old_cell, pitch, spacer.thickness, spacer.material,
										  counter, surflist)
				old_cell.griddict[key] = new_cell
				print("Just added pincell", key, ":", new_cell.id)
			row[i] = new_cell
		new_universes[j] = row
	
	if lattice.name:
		new_name = lattice.name + "-gridded"
	else:
		new_name = str(lattice.id) + "-gridded"
	gridded = openmc.RectLattice(counter.add_universe(), name = new_name)
	gridded.pitch = (pitch, pitch)
	gridded.lower_left = [-pitch * npins / 2.0] * 2
	gridded.universes = new_universes
	return gridded
	


