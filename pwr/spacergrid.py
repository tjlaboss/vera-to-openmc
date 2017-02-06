# Spacer Grid
# 
# Module containing the classes and methods for modeling of PWR spacer grids,
# for use in the Assembly class (assembly.py)

from pwr.functions import duplicate, get_surface
import openmc
import numpy
from math import sqrt


class SpacerGrid(object):
	"""Object to hold properties of an assembly's spacer grids
	
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
	"""
	
	def __init__(self, key, height, mass, material, pitch, npins):
		self.key = key
		self.height = height
		self.mass = mass
		self.material = material
		self.thickness = self.calculate_thickness(pitch, npins)
	
	def calculate_thickness(self, pitch, npins):
		"""Calculate the thickness of the spacer surrounding each pincell.
		Inputs:
			pitch:		float; pin pitch (cm)
			npins:		int; number of pins across Assembly (npinsxnpins)
		"""
		
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


def add_spacer_to(pincell, pitch, t, material, counter, xplanes, yplanes):
	"""Given a pincell to be placed in a lattice, add
	the spacer grid to the individual cell.
	
	Inputs:
		pincell:	instance of openmc.Universe describing the pincell
					and its concentric rings of instances of openmc.Cell
		pitch:		float; pin pitch in cm
		t:			float; thickness in cm of one edge of the spacer between
					two pincells (HALF the total thickness)
		material:	instance of openmc.Material from which the spacer is made
		counter:	instance of Counter to keep track of universe numbers
		xplanes:	dictionary of existing instances of openmc.XPlane, of the format
					{str(x0):xplane}    [Default: empty dictionary]
					This is optional, but strongly recommended if you are adding
					spacers to more than one pin cell.
		yplanes:    dictionary of existing instances of openmc.YPlane, of the format
					{str(y0):yplane}    [Default: empty dictionary]
					This is optional, but strongly recommended if you are adding
					spacers to more than one pin cell.
	
	Output:
		new_pin:	instance of openmc.Universe describing the pincell
					surrounded by the spacer
	"""
	assert isinstance(pincell, openmc.Universe), str(pincell) + "must be an openmc.Universe (not a Cell)"
	assert isinstance(material, openmc.Material), str(material) + "is not an instance of openmc.Material"
	
	orig_list = list(pincell.cells.values())
	suffix = " (gridded)"
	
	# Create necessary planes
	p = pitch / 2.0
	top_out   = get_surface(counter, yplanes, 'y', p)
	top_in    = get_surface(counter, yplanes, 'y',  p - t)
	bot_in    = get_surface(counter, yplanes, 'y', -p + t)
	bot_out   = get_surface(counter, yplanes, 'y', -p)
	left_out  = get_surface(counter, xplanes, 'x', -p)		# He feels left out
	left_in   = get_surface(counter, xplanes, 'x', -p + t)
	right_in  = get_surface(counter, xplanes, 'x',  p - t)
	right_out = get_surface(counter, xplanes, 'x',  p)
	
	# Get the outermost (mod) Cell of the pincell
	mod_cell = duplicate(orig_list[-1], counter)
	mod_cell.name += suffix
	
	# Make a cell encompassing the 4 sides of the spacer
	spacer = openmc.Cell(counter.add_cell(), name = pincell.name + " spacer")
	spacer.region = (+left_out	& +top_in 	& -top_out	&	-right_out) | \
					(+right_in	& -right_out& +bot_in	& 	-top_in)	| \
					(+left_out	& -left_in	& +bot_in	&	-top_in)	| \
					(+bot_out 	& -bot_in	& +left_out	&	-right_out )
	spacer.fill = material
	# Then fix the moderator cell to be within the bounds of the spacer
	mod_cell.region &= (+bot_in	& +left_in	& -top_in	& -right_in )
	
	new_pin = openmc.Universe(counter.add_universe(), name = pincell.name + " gridded")
	# Add all of the original cells except the old mod cell
	for i in range(len(orig_list) - 1):
		new_cell = duplicate(orig_list[i], counter)
		new_cell.name += suffix
		new_pin.add_cell(new_cell)
	new_pin.add_cell(mod_cell) 	# the new mod cell
	new_pin.add_cell(spacer)
	
	return new_pin


def add_grid_to(lattice, spacer, counter, xplanes = {}, yplanes = {}):
	"""Add a spacer to every pincell in the lattice.

	Inputs:
		lattice:		instance of openmc.RectLattice
		spacer:			instance of SpacerGrid
		counter:		instance of Counter
		xplanes:        dictionary of instances of openmc.XPlane, of the format
						{str(x0):xplane}. Optional, but strongly recommended.
		yplanes:        dictionary of instances of openmc.YPlane, of the format
						{str(y0):yplane}. Optional, but strongly recommended.
	Output:
		gridded:		instance of openmc.RectLattice with the grid applied
						to every cell"""
	
	assert isinstance(lattice, openmc.RectLattice), "'lattice' must be a RectLattice."
	assert lattice.pitch[0] == lattice.pitch[1], "lattice must have a square pitch at this time.\n" + \
			"If you need a non-square rectangular pitch, please contact the developers."
	assert isinstance(spacer, SpacerGrid), "'spacer' must be an instance of SpacerGrid."
	pitch = lattice.pitch[0]
	n = len(lattice.universes)
	new_universes = numpy.empty((n,n), dtype = openmc.Universe)
	
	for j in range(n):
		for i in range(n):
			old_cell = lattice.universes[j][i]
			gkey = spacer.key
			if gkey in old_cell.griddict:
				new_cell = old_cell.griddict[gkey]
			else:
				new_cell = add_spacer_to(old_cell, pitch, spacer.thickness, spacer.material,
										  counter, xplanes, yplanes)
				old_cell.griddict[gkey] = new_cell
			new_universes[j][i] = new_cell
	
	if lattice.name:
		new_name = lattice.name + "-grid:" + spacer.key
	else:
		new_name = str(lattice.id) + "-grid:" + spacer.key
	gridded = openmc.RectLattice(counter.add_universe(), name = new_name)
	gridded.pitch = (pitch, pitch)
	gridded.lower_left = [-pitch * n / 2.0] * 2
	gridded.universes = new_universes
	return gridded
	


