# Vera to OpenMC
#
# Takes a VERA case and attempts to construct 
# the required files for an OpenMC input.

from math import sqrt, copysign
from copy import copy
from read_xml import Case
from functions import fill_lattice, clean
import pwr
from pwr import SURFACE, CELL, MATERIAL, UNIVERSE	# Global constants for counters

try:
	import openmc
except ImportError:
	raise SystemExit("Error: Cannot import openmc. You will not be able to generate OpenMC objects.")



class MC_Case(Case):
	'''An extension of the Case class from read_xml,
	customized with some new attributes and methods to 
	generate objects for OpenMC.'''
	def __init__(self, source_file):
		super(MC_Case, self).__init__(source_file)
		
		self.openmc_surfaces = []
		self.openmc_materials = {}
		self.openmc_pincells = {}
		self.openmc_assemblies = {}
		
		# ID Counter
		# Starting at 9 makes all IDs double digits
		self.counter = pwr.Counter(9, 9, 9, 9)
		
		
		# Create the essential moderator material
		'''The outside of each cell is automatically filled with the special material "mod", which refers to
		the moderator (or coolant). The composition of "mod" is calculated by the codes using the local T/H
		conditions and the soluble boron concentration, and cannot be specified by a user on a mat card.'''
		self.mod = self.get_openmc_material("mod")
		self.mod.add_s_alpha_beta("c_H_in_H2O")
		
		# Create an infinite cell/universe of moderator
		self.mod_cell = openmc.Cell(1, name = "Infinite Mod Cell", fill = self.mod)
		self.mod_verse = openmc.Universe(1, name = "Infinite Mod Universe", cells = (self.mod_cell,))
		
	
	def __counter(self, TYPE):
		'''Get the next cell/surface/material/universe number, and update the counter.
		Input:
			count:		CELL, SURFACE, MATERIAL, or UNIVERSE
		Output:
			integer representing the next cell/surface/material/universe ID'''
		
		# Quick fix
		return self.counter.count(TYPE)
	
	
		
	def __get_xyz_planes(self, x0s = (), y0s = (), z0s = (), rd = 5):
		'''
		Inputs:
			x0s:		list or tuple of x0's to check for; default is empty tuple
			y0s:		same for y0's
			z0s:		same for z0's
			rd:			integer; number of digits to round to when comparing surface
						equality. Default is 5
		Outputs:
			xlist:		list of instances of openmc.XPlane, of length len(x0s)
			ylist:		ditto, for openmc.YPlane, y0s
			zlist:		ditto, for openmc.ZPlane, z0s
		'''
		nx = len(x0s)
		ny = len(y0s)
		nz = len(z0s)
		xlist = [None,]*nx
		ylist = [None,]*ny
		zlist = [None,]*ny
		
		for i in range(nx):
			xlist[i] = pwr.get_plane(self.openmc_surfaces, self.counter, 'x', x0s[i], eps = rd)
		for i in range(ny):
			ylist[i] = pwr.get_plane(self.openmc_surfaces, self.counter, 'y', y0s[i], eps = rd)
		for i in range(nz):
			zlist[i] = pwr.get_plane(self.openmc_surfaces, self.counter, 'z', z0s[i], eps = rd)
		
		return xlist, ylist, zlist
	
	
	def get_openmc_baffle(self):
		"""Create the cells and surfaces for the core baffle.
		
		Outputs:
			baffle_cells:	instance of openmc.Cell describing the baffle plates	
		"""
		
		"""
		This method iterates through the square map of the core and traces out the 
		boundary of the baffle. Overlaps are OK due to the use of unions.
		
		WARNING: In OpenMC 0.8.0 and earlier, there is a maximum region length. A typical PWR
		core baffle will produce regions in excess of the default maximum region length. You
		will need to change this for yourself in the Fortran source code (constants.f90). 
		"""
		baf = self.core.baffle		# instance of objects.Baffle
		pitch = self.core.pitch		# assembly pitch
		
		# Useful distances
		d0 = pitch/2.0					# dist (from center of asmbly) to edge of asmbly
		d1 = d0 + baf.gap 				# dist to inside of baffle
		d2 = d1 + baf.thick				# dist to outside of baffle 
		d3 = d0 - baf.gap 				# dist to inside of next baffle
		width = self.core.size * self.core.pitch / 2.0	# dist from center of core to center of asmbly
		
		cmap = self.core.square_maps("s")
		n = self.core.size - 1
		
		# Unite all individual regions with the Master Region
		master_region = openmc.Union()
		
		
		# For each row (moving vertically):
		for j in range(1,n):
			# For each column (moving horizontally):
			for i in range(1,n):
				if cmap[j][i]:
					# Positions of surfaces
					x = (i + 0.5)*pitch - width
					y = width - (j + 0.5)*pitch
					
					north = cmap[j-1][i]
					south = cmap[j+1][i]
					east  = cmap[j][i+1]
					west  = cmap[j][i-1]
					southeast = cmap[j+1][i+1]
					southwest = cmap[j+1][i-1]
					northeast = cmap[j-1][i+1]
					northwest = cmap[j-1][i-1]
					
					
					# Left side
					if not west:
						x_left = x - d2
						x_right = x - d1
						if north:
							y_top = y + d3
						else:
							y_top = y + d2
						if south:
							if southwest:
								y_bot = y - d3
							else:
								y_bot = y - d2
						else:
							y_bot = y - d2
						(left, right), (bot, top) = self.__get_xyz_planes( \
							x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
						west_region = (+left & -right & +bot & -top)
						master_region.nodes.append(west_region)
					
					# Right side
					if not east:
						x_left = x + d1
						x_right = x + d2
						if north:
							y_top = y + d3
						else:
							y_top = y + d2
						if south:
							if southeast:
								y_bot = y - d3
							else:
								y_bot = y - d2
						else:
							y_bot = y - d2
						(left, right), (bot, top) = self.__get_xyz_planes( \
							x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
						east_region = (+left & -right & +bot & -top)
						master_region.nodes.append(east_region)
					
					# Top side
					if not north:
						y_bot = y + d1
						y_top = y + d2
						if west:
							if northwest:
								x_left = x - d3
							else:
								x_left = x - d2
						else:
							x_left = x - d2
						if east:
							x_right = x + d3
						else:
							x_right = x + d2
						(left, right), (bot, top) = self.__get_xyz_planes( \
							x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
						north_region = (+left & -right & +bot & -top)
						master_region.nodes.append(north_region)
					
					# Bottom side
					if not south:
						y_bot = y - d2
						y_top = y - d1
						if west:
							if southwest:
								x_left = x - d3
							else:
								x_left = x - d2
						else:
							x_left = x - d2
						if east:
							x_right = x + d3
						else:
							x_right = x + d2
						(left, right), (bot, top) = self.__get_xyz_planes( \
							x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
						south_region = (+left & -right & +bot & -top)
						master_region.nodes.append(south_region)
		
			# Edge cases
			x = (j + 0.5)*pitch - width
			y = width - (j + 0.5)*pitch
			
			
			# West edge
			if cmap[j][0]:
				north = cmap[j-1][0]
				south = cmap[j+1][0] 
				xx = -(width - 0.5*pitch)
				x_left = xx - d2
				x_right = xx - d1
				y_bot = y - d2
				y_top = y + d2
				
				(left, right), (bot, top) = self.__get_xyz_planes( \
					x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
				west_region = (+left & -right & +bot & -top)
				master_region.nodes.append(west_region)
				
				if not north:
					y_bot = y + d1
					x_right = xx + d3
					(right,), (bot,) = self.__get_xyz_planes( \
						x0s = (x_right,), y0s = (y_bot,))[0:2]
					north_region = (+left & -right & +bot & -top)
				master_region.nodes.append(north_region)
				
				if not south:
					y_bot = y - d2
					y_top = y - d1
					x_right = xx + d3
					(right,), (bot, top) = self.__get_xyz_planes( \
						x0s = (x_right,), y0s = (y_bot, y_top))[0:2]
					south_region = (+left & -right & +bot & -top)
					master_region.nodes.append(south_region)
					
			
			# East edge
			if cmap[j][n]:
				north = cmap[j-1][n]
				south = cmap[j+1][n]
				xx = +(width - 0.5*pitch)
				x_left = xx + d1
				x_right = xx + d2
				y_bot = y - d2
				y_top = y + d2
				(left, right), (bot, top) = self.__get_xyz_planes( \
					x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
				east_region = (+left & -right & +bot & -top)
				master_region.nodes.append(east_region)
				
				if not north:
					y_bot = y + d1
					x_left = xx - d3
					(left,), (bot,) = self.__get_xyz_planes( \
						x0s = (x_left,), y0s = (y_bot,))[0:2]
					north_region = (+left & -right & +bot & -top)
				master_region.nodes.append(north_region)
				
				if not south:
					y_bot = y - d2
					y_top = y - d1
					x_left = xx - d3
					(left,), (bot, top) = self.__get_xyz_planes( \
						x0s = (x_left,), y0s = (y_bot, y_top))[0:2]
					south_region = (+left & -right & +bot & -top)
					master_region.nodes.append(south_region)
			
			# North edge
			if cmap[0][j]:
				east  = cmap[0][j+1]
				west  = cmap[0][j-1]
				yy = +(width - 0.5*pitch)
				x_left = x - d2
				x_right = x + d2
				y_bot = yy + d1
				y_top = yy + d2
				(left, right), (bot, top) = self.__get_xyz_planes( \
					x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
				north_region = (+left & -right & +bot & -top)
				master_region.nodes.append(north_region)
				
				if not west:
					x_right = x - d1
					y_bot = yy - d3
					(right,), (bot,) = self.__get_xyz_planes( \
						x0s = (x_right,), y0s = (y_bot,))[0:2]
					west_region = (+left & -right & +bot & -top)
					master_region.nodes.append(west_region)
					
				if not east:
					x_left = x + d1
					x_right = x + d2
					y_bot = yy - d3
					(left, right), (bot, top) = self.__get_xyz_planes( \
						x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
					east_region = (+left & -right & +bot & -top)
					master_region.nodes.append(east_region)
					
			
			# South edge
			if cmap[n][j]:
				east  = cmap[n][j+1]
				west  = cmap[n][j-1]
				yy = -(width - 0.5*pitch)
				x_left = x - d2
				x_right = x + d2
				y_bot = yy - d2
				y_top = yy - d1
				(left, right), (bot, top) = self.__get_xyz_planes( \
					x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
				south_region = (+left & -right & +bot & -top)
				master_region.nodes.append(south_region)
				
				if not west:
					x_right = x - d1
					y_top = yy + d3
					(right,), (top,) = self.__get_xyz_planes( \
						x0s = (x_right,), y0s = (y_top,))[0:2]
					west_region = (+left & -right & +bot & -top)
					master_region.nodes.append(west_region)
					
				if not east:
					x_left = x + d1
					x_right = x + d2
					y_top = yy + d3
					(left, right), (top,) = self.__get_xyz_planes( \
						x0s = (x_left, x_right), y0s = (y_top,))[0:2]
					east_region = (+left & -right & +bot & -top)
					master_region.nodes.append(east_region)
		# Done iterating.
		
		
		# Corner cases (UNTESTED)
		# Top left
		if cmap[0][0]:
			x = -(width - 0.5*pitch)
			y = -x
			x_left = x - d2
			y_top =  y + d2
			
			# West
			x_right = x - d1
			y_bot = y - d2 
			(left, right), (bot, top) = self.__get_xyz_planes( \
				x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
			west_region =  (+left & -right & +bot & -top)
			master_region.nodes.append(west_region)
			
			# North
			x_right = x + d2
			y_bot = y + d1
			(right,), (bot,) = self.__get_xyz_planes( \
				x0s = (x_right,), y0s = (y_bot,))[0:2]
			north_region =  (+left & -right & +bot & -top)
			master_region.nodes.append(north_region)
			
		# Top right
		if cmap[0][n]:
			x = +(width - 0.5*pitch)
			y = +x
			x_right = x + d2
			y_top =  y + d2
			
			# East
			x_left = x + d1
			y_bot = y - d2 
			(left, right), (bot, top) = self.__get_xyz_planes( \
				x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
			east_region =  (+left & -right & +bot & -top)
			master_region.nodes.append(east_region)
			
			# North
			x_left = x - d2
			y_bot = y + d1
			(left,), (bot,) = self.__get_xyz_planes( \
				x0s = (x_left,), y0s = (y_bot,))[0:2]
			north_region =  (+left & -right & +bot & -top)
			master_region.nodes.append(north_region)
		
		# Bottom right
		if cmap[n][n]:
			x = +(width - 0.5*pitch)
			y = -x
			x_right = x + d2
			y_bot =  y - d2
			
			# East
			x_left = x + d1
			y_top = y + d2 
			(left, right), (bot, top) = self.__get_xyz_planes( \
				x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
			east_region =  (+left & -right & +bot & -top)
			master_region.nodes.append(east_region)
			
			# South
			x_left = x - d2
			y_top = y - d1
			(left,), (top,) = self.__get_xyz_planes( \
				x0s = (x_left,), y0s = (y_top,))[0:2]
			south_region =  (+left & -right & +bot & -top)
			master_region.nodes.append(south_region)
		
		# Bottom left
		if cmap[n][0]:
			x = -(width - 0.5*pitch)
			y = +x
			x_left = x - d2
			y_bot =  y - d2
			
			# West
			x_right = x - d1
			y_top = y + d2 
			(left, right), (bot, top) = self.__get_xyz_planes( \
				x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
			west_region =  (+left & -right & +bot & -top)
			master_region.nodes.append(west_region)
			
			# South
			x_right = x + d2
			y_top = y - d1
			(right,), (top,) = self.__get_xyz_planes( \
				x0s = (x_right,), y0s = (y_top,))[0:2]
			south_region =  (+left & -right & +bot & -top)
			master_region.nodes.append(south_region)
		
		
		# Set the baffle material, cell, etc.
		baffle_cell = openmc.Cell(self.__counter(CELL), "Baffle", self.get_openmc_material(baf.mat), master_region)
		
		return baffle_cell
		
	
	
	

	
	
		
	def get_openmc_material(self, material, asname = "", inname = ""):
		'''Given a vera material (objects.Material) as extracted by self.__get_material(),
		return an instance of openmc.Material. If the OpenMC Material exists, look it
		up in the dictionary. Otherwise, create it anew.
		
		Inputs:
			material:			string; key of the material in self.materials
			asname:				string; name of the Assembly in which a pin cell is present.
								VERA pin cells may have different materials sharing the same name.
								[Default: empty string]
			inname:				string; name of the Insert which has been placed inside the cell, if any.
								[Default: empty string]
		
		Outputs:
			openmc_material:	instance of openmc.Material
		
		All of the material fractions sum to either +1.0 or -1.0. If positive fractions are used, they
		refer to weight fractions. If negative fractions are used, they refer to atomic	fractions.
		'''
		
		# Handle the permutations/combinations of suffixes.
		# This order should be preserved.
		all_suffixes = [asname + inname, asname, inname]
		for suffix in all_suffixes:
			if material + suffix in self.materials:
				material += suffix
				break
		
		
		if material in self.openmc_materials:
			# Look it up as normal
			openmc_material = self.openmc_materials[material]
		else:
			# Then the material doesn't exist yet in OpenMC form
			# Generate it and add it to the index 
			vera_mat = self.materials[material]
			openmc_material = openmc.Material(self.__counter(MATERIAL), material)
			openmc_material.set_density("g/cc", vera_mat.density)
			openmc_material.temperature = vera_mat.temperature
			for nuclide in sorted(vera_mat.isotopes):
				frac = vera_mat.isotopes[nuclide]
				if nuclide[-2:] == "00":
					# Natural abundance-expand except for Carbon
					ename = nuclide[:-2]
					if ename == "C":
						# Correct for OpenMC syntax
						openmc_material.add_nuclide("C0", frac, 'wo')
					else:
						# Element.expand() breaks an element into its constituent nuclides
						elem = openmc.Element(ename)
						for n, w in elem.expand():
							openmc_material.add_nuclide(n, frac*w, 'wo')
				else:
					openmc_material.add_nuclide(nuclide, frac, 'wo')
				# Shouldn't be needed: the parsed XML should already be in weight frac
				#if frac < 0:
				#	openmc_material.add_nuclide(nuclide, abs(frac), 'ao')			
					
			self.openmc_materials[material] = openmc_material
		
		return openmc_material
	
	

	
	def get_openmc_pincell(self, vera_cell):
		'''Converts a VERA cell to an OpenMC universe. If this pincell universe
		already exists, return it; otherwise, construct it anew, and add it
		to self.openmc_pincells.
		
		Inputs:
			vera_cell:			instance of objects.Cell from the vera deck
		
		Outputs:
			pincell_universe:	instance of openmc.Universe, containing:
				.cells:				list of instances of openmc.Cell, describing the
									geometry and composition of this pin cell's universe
				.universe_id:	integer; unique identifier of the Universe
				.name:			string; more descriptive name of the universe (pin cell)			
			'''
		
		# First, check if this cell has already been created
		if vera_cell.key in self.openmc_pincells:
			return self.openmc_pincells[vera_cell.key]
		else:
			openmc_cells = []
			# Before proceeding, define the OpenMC surfaces (Z cylinders)
			for ring in range(vera_cell.num_rings):
				r = vera_cell.radii[ring]
				name = vera_cell.name + "-ring" + str(ring)
				# Check if the outer bounding surface exists
				surf_id = None
				for s in self.openmc_surfaces:
					if (s.type == "z-cylinder"):
						if (s.r == r) and (s.x0 == 0) and (s.y0 == 0):
							# Then the cylinder is the same
							surf_id = s.id
							break # from the "for s in" loop
				if not surf_id:
					# Generate new surface and get its surf_id
					s = openmc.ZCylinder(self.__counter(SURFACE), "transmission", 0, 0, r)
					# Add the new surfaces to the registry
					self.openmc_surfaces.append(s)
					
				# Otherwise, the surface s already exists
				# Proceed to define the cell inside that surface:
				new_cell = openmc.Cell(self.counter.add_cell(), name)
				
				if ring == 0:
					# Inner ring
					new_cell.region = -s
					last_s = s
				else:
					# Then this OpenMC cell is outside the previous (last_s), inside the current
					new_cell.region = -s & +last_s 
					last_s = s
				
				# Fill the cell in with a material
				m = vera_cell.mats[ring]
				fill = self.get_openmc_material(m, vera_cell.asname, vera_cell.inname)
					
				# What I want to do instead is, somewhere else in the code, generate the corresponding
				# openmc material for each objects.Material instance. Then, just look it up in that dictionary.
				new_cell.fill = fill
				openmc_cells.append(new_cell)
			# end of "for ring" loop
			
			# Then add the moderator outside the pincell
			mod_cell = openmc.Cell(self.__counter(CELL), vera_cell.name + "-Mod")
			mod_cell.fill = self.mod
			mod_cell.region = +last_s
			openmc_cells.append(mod_cell)
			
			# Create a new universe in which the pin cell exists 
			pincell_universe = openmc.Universe(self.__counter(UNIVERSE), vera_cell.name + "-verse")
			pincell_universe.add_cells(openmc_cells)
			
			# Initialize a useful dictionary to keep track of versions of
			# this cell which have spacer grids added
			pincell_universe.griddict = {}
			
			self.openmc_pincells[vera_cell.key] = pincell_universe
			
			return pincell_universe
	
	
	
	def get_openmc_lattices(self, vera_asmbly):
		'''Creates the  assembly geometry and lattices of pin cells
		required to define an assembly in OpenMC.
		
		Inputs:
			vera_asmbly:		instance of objects.Assembly
		
		Outputs:
			openmc_asmblies:	list of instance of openmc.RectLattice
		'''
		
		
		ps = vera_asmbly.params
		pitch = vera_asmbly.pitch
		npins = vera_asmbly.npins
		# Look for optional parameters available from vera_asmbly.params
		# Possible params include:
		# axial_elevations, axial_labels, grid_elev, grid_map,
		# ppitch, title, num_pins, label
		openmc_lattices = []
		
		# Instantiate all the pin cells (openmc.Universes) that appear in the Assembly
		cell_verses = {}
		for vera_cell in vera_asmbly.cells.values():
			c = self.get_openmc_pincell(vera_cell)
			cell_verses[vera_cell.key] = c
		
		for latname in vera_asmbly.axial_labels:
			lattice = openmc.RectLattice(self.__counter(UNIVERSE), latname)
			lattice.pitch = (pitch, pitch)
			lattice.lower_left = [-pitch * float(npins) / 2.0] * 2
			# And populate with universes from cell_verses
			asmap = vera_asmbly.key_maps[latname]
			
			lattice.universes = fill_lattice(asmap, lambda c: cell_verses[c], npins)
			lattice.outer = self.mod_verse	# To account for the assembly gap
			# Initialize a dictionary of versions of this lattice which have spacer grids added
			lattice.griddict = {}
			openmc_lattices.append(lattice)
		
		return openmc_lattices
	
	
	
	
		
	
	
	def get_openmc_assembly(self, vera_asmbly):
		"""Creates an OpenMC fuel assembly, complete with lattices
		of fuel pins and spacer grids, that should be equivalent to what
		is constructed by VERA.
		
		Inputs:
			vera_asmbly:		instance of objects.Assembly
		
		Outputs:
			pwr_asmbly:			instance of pwr.Assembly containing the lattices, spacers, and such. 
								pwr_asmbly.universe is the instance of openmc.Universe modeling
								the fuel assembly.
		"""
		key = vera_asmbly.name
		if key in self.openmc_assemblies:
			return self.openmc_assemblies[key]
		else:
			
			ps = vera_asmbly.params
			pitch = vera_asmbly.pitch
			npins = vera_asmbly.npins
			
			# Initiate and describe the Assembly
			pwr_asmbly = pwr.Assembly(vera_asmbly.label, vera_asmbly.name, self.__counter(UNIVERSE), pitch, npins)
			pwr_asmbly.lattices = self.get_openmc_lattices(vera_asmbly)
			pwr_asmbly.lattice_elevs = vera_asmbly.axial_elevations
			pwr_asmbly.mod = self.mod
			pwr_asmbly.counter = self.counter
			
			# FIXME: Handle spacer grids
			if vera_asmbly.spacergrids:
				pwr_spacergrids = {}
				# Translate from VERA to pwr 
				for gkey in vera_asmbly.spacergrids:
					g = vera_asmbly.spacergrids[gkey]
					mat = self.get_openmc_material(g.material)
					grid = pwr.SpacerGrid(gkey, g.height, g.mass, mat, pitch, npins)
					pwr_spacergrids[gkey] = grid
				
				pwr_asmbly.spacers = clean(ps["grid_map"], lambda key: pwr_spacergrids[key] )
				pwr_asmbly.spacer_mids = clean(ps["grid_elev"], float)
			
			# Handle nozzles
			if "lower_nozzle_comp" in ps:
				nozzle_mat = self.get_openmc_material(ps["lower_nozzle_comp"])
				mass = float(ps["lower_nozzle_mass"])
				height = float(ps["lower_nozzle_height"])
				lnoz = pwr.Nozzle(height, mass, nozzle_mat, self.mod, npins, pitch,
									counter = self.counter, name = "Lower Nozzle")
				lnozmat = lnoz.get_nozzle_material()
				self.openmc_materials[lnozmat.name] = lnozmat
				pwr_asmbly.lower_nozzle = lnoz
			if "upper_nozzle_comp" in ps:
				nozzle_mat = self.get_openmc_material(ps["upper_nozzle_comp"])
				mass = float(ps["upper_nozzle_mass"])
				height = float(ps["upper_nozzle_height"])
				unoz = pwr.Nozzle(height, mass, nozzle_mat, self.mod, npins, pitch,
									counter = self.counter, name = "Upper Nozzle")
				unozmat = unoz.get_nozzle_material()
				self.openmc_materials[unozmat.name] = unozmat
				pwr_asmbly.upper_nozzle = unoz
			
			'''	Worth noting about the nozzles:
		
				== Analysis of the BEAVRS Benchmark Using MPACT ==
			A major difference between the model and the benchmark specification is the treatment of 
			the axial reflector region. The benchmark specifies the upper and lower nozzle to be modeled 
			with a considerable amount of stainless steel. The authors discerned that 
			the benchmark is specifying up to 10 times the amount of steel that is in the nozzle and
			core plate region. Instead of using this amount of steel, a Westinghouse optimized fuel
			assembly (OFA) design found in Technical Report ML033530020 is used for the upper and
			lower reflector regions.
											--CASL-U-2015-0183-000	'''
			
			
			# Where the magic happens
			pwr_asmbly.build()
			self.openmc_assemblies[key] = pwr_asmbly
			
				
			return pwr_asmbly
	
	
	def get_openmc_reactor_vessel(self):
		'''Creates the pressure vessel representation in OpenMC
		
		Inputs:
			vera_core:		instance of objects.Core
		
		Outputs:
			openmc_vessel:	instance of openmc.Universe containing all the cells
							describing the reactor pressure vessel EXCEPT inside_cell
			inside_cell:	instance of openmc.Cell containing the innermost ring
							of the vessel, TO BE FILLED with assemblies
			inside_fill:	string; key of the openmc.Material to fill all spaces
							within inside_cell, outside of the assemblies
			outer_surfs:	instances of openmc.Surface (specifically, ZCylinder and ZPlane)
							describing the bounding	surfaces of the reactor vessel
		'''
		
		ps = self.core.params
		core_cells = []
		
		# Create the top and bottom planes of the core and core plate
		plate_bot = openmc.ZPlane(self.__counter(SURFACE),
							z0 = -self.core.bot_refl.thick, boundary_type = self.core.bc["bot"])
		core_bot = openmc.ZPlane(self.__counter(SURFACE), z0 = 0.0)
		core_top = openmc.ZPlane(self.__counter(SURFACE), z0 = self.core.height)
		plate_top = openmc.ZPlane(self.__counter(SURFACE),
							z0 = self.core.height + self.core.top_refl.thick, boundary_type = self.core.bc["top"])
		
		# Create the concentric cylinders of the vessel
		for ring in range(len(self.core.vessel_radii) - 1):
			r = self.core.vessel_radii[ring]
			m = self.core.vessel_mats[ring]
			
			s = openmc.ZCylinder(self.__counter(SURFACE), R = r)
			
			cell_name = "Vessel_" + str(ring)
			new_cell = openmc.Cell(self.__counter(CELL), cell_name)
			
			if ring == 0:
				# For the center ring,
				new_cell.region = -s    & +core_bot & -core_top
				inside_cell = new_cell
				inside_fill = m
				last_s = s
				vessel_surf = s
			else:
				new_cell.region = -s & +last_s	& +plate_bot & -plate_top
				new_cell.fill = self.get_openmc_material(m)
				last_s = s
				core_cells.append(new_cell)
		
		# And finally, the outermost ring
		s = openmc.ZCylinder(self.__counter(SURFACE), R = max(self.core.vessel_radii), boundary_type = self.core.bc["rad"])
		new_cell = openmc.Cell(self.__counter(CELL), "Vessel-Outer")
		new_cell.region = -s    & +plate_bot & -plate_top
		core_cells.append(new_cell)
		
		# Add the core plates
		top_plate_mat = self.get_openmc_material(self.core.bot_refl.material)
		self.openmc_materials[top_plate_mat.name] = top_plate_mat
		top_plate_cell = openmc.Cell(self.__counter(CELL), "Top core plate")
		top_plate_cell.region = -vessel_surf & + core_top & -plate_top
		top_plate_cell.fill = top_plate_mat
		core_cells.append(top_plate_cell)
		
		bot_plate_mat = self.get_openmc_material(self.core.bot_refl.material)
		self.openmc_materials[bot_plate_mat.name] = bot_plate_mat
		bot_plate_cell = openmc.Cell(self.__counter(CELL), "Bot core plate")
		bot_plate_cell.region = -vessel_surf & + core_bot & -plate_bot
		bot_plate_cell.fill = bot_plate_mat
		core_cells.append(bot_plate_cell)
		
		outer_surfs = (vessel_surf, plate_bot, plate_top) 
		
		openmc_vessel = openmc.Universe(self.__counter(UNIVERSE), "Reactor Vessel")
		openmc_vessel.add_cells(core_cells)
		
		return openmc_vessel, inside_cell, inside_fill, outer_surfs
			
	
	def add_insert(self, base_lattice, insert):
		'''Insert a burnable poision, thimble plug, or other arbitrary object to a lattice.
		
		Inputs:
			base_lattice:		instance of openmc.RectLattice
			insert:				instance of objects.Insert with the same
								number of pins as base_lattice
		
		Outputs:
			new_lattice:		instance of openmc.RectLattice with some cells replaced
		'''	
		n = insert.npins
		x = base_lattice.size[0]
		y = base_lattice.size[1]
		assert(n == x and n == y), \
			"'base_lattice' must be exactly " + str(n) + "x" + str(n) + " pins."
		
		
		
		
		return None
	
	
	
	
	
	
	
	
	def get_openmc_core_lattice(self, blank = "-"):
		'''Create the reactor core lattice. 
		
		This is an extremely important function that hasn't really been written yet.
		What it needs to do is iterate through the shape map.
			If an assembly belongs in that location:
				check for inserts, controls, and detectors
				refer to the assembly map
				get_openmc_assembly(asmbly, inserts, controls, detectors)
					get_openmc_lattices() based on that
				we then have an instance of pwr.Assembly
				place that in the core map
			Else:
				fill with mod
		Then zip this lattice up in a universe and return it.
		Later, that will be placed inside the baffle, and the reactor vessel.
		
		Input:
			blank:			string which represents a location in a core map with no insertion.
							[Default: "-"]
		Output:
			openmc_core:	instance of openmc.RectLattice; the lattice contains [read: will contain]
							instances of pwr.Assembly
		'''
		shape, asmap = self.core.square_maps(space = "")
		n = len(shape)
		halfwidth = self.core.pitch * n / 2.0
		
		openmc_core = openmc.RectLattice(self.__counter(UNIVERSE), "Core Lattice")
		openmc_core.pitch = (self.core.pitch, self.core.pitch)
		openmc_core.lower_left = [-halfwidth * n / 2.0] * 2
		openmc_core.outer = self.mod_verse
		
		ins_map = self.core.insert_map.square_map()
		det_map = self.core.detector_map.square_map()
		crd_map = self.core.control_map.square_map()
		crd_bank_map = self.core.control_bank.square_map()
		
		lattice = [[None,]*n]*n
		
		print("Generating core (this may take a while)...")
		for j in range(n):
			new_row = [None,]*n
			for i in range(n):
				# Check if there is supposed to be an assembly in this position
				if shape[j][i]:
					askey = asmap[j][i].lower()
					vera_asmbly = self.assemblies[askey]
					
					ins_key = ins_map[j][i]
					det_key = det_map[j][i]
					crd_key = crd_map[j][i]
					crd_bank_key = crd_bank_map[j][i]
					
					if (ins_key or crd_key or det_key) != blank:
						vera_asmbly = copy(vera_asmbly)
						# Handle each type of insertion differently.
						if ins_key != blank:
							vera_ins = self.inserts[ins_key]
							vera_asmbly.add_insert(vera_ins)
							vera_asmbly.name += "+" + vera_ins.name
						if crd_key != blank:
							vera_crd = self.controls[crd_key]
							steps = self.state.rodbank[crd_bank_key]
							depth = steps*vera_crd.step_size
							vera_asmbly.add_insert(vera_crd, depth)
							vera_asmbly.name += "+" + vera_crd.name
						if det_key != blank:
							# Is it any different than a regular insert?
							vera_det = self.detectors[det_key]
							vera_asmbly.add_insert(vera_det)
							vera_asmbly.name += "+" + vera_det.name
					
					openmc_assembly = self.get_openmc_assembly(vera_asmbly)
					
					new_row[i] = openmc_assembly.universe
				else:
					# Then install the moderator universe instead
					#new_row[i] = 0 # REPLACE WITH: that universe
					new_row[i] = self.mod_verse
			lattice[j] = new_row
		
		
		openmc_core.universes = lattice
		
		return openmc_core
	
	
	
	

if __name__ == "__main__":
	# Instantiate a test case with a representative VERA XML.gold
	#filename = "gold/p7.xml.gold"
	#filename = "gold/2a_dep.xml.gold"
	filename = "gold/2e.xml.gold"
	test_case = MC_Case(filename)
	#print "Testing:",  test_case
	
	
	print("\nInspecting the children")
	for child in test_case.root:
		if child.tag == "ParameterList":
			print(child.attrib["name"])
			
	print
	
	#print test_case.describe()
	all_pins = []
	for a in test_case.assemblies.values():
		for cm in a.cellmaps.values():
			continue
			# comment out 'continue' to look at the cell maps
			print(a, ':\t', cm)
			print(cm.str_map())
			print("-"*18)
		#print a.params
		for c in a.cells.values():
			new_pin = test_case.get_openmc_pincell(c)
			all_pins.append(new_pin)
			if new_pin.name == "Cell_1-verse":
				mypin = new_pin
	
	#print cm.square_map()
	

	test_asmblys = test_case.get_openmc_lattices(a)[0]
	#print(test_asmbly)
	
	core, icell, ifill, cyl = test_case.get_openmc_reactor_vessel()
	#print(test_case.core.square_maps("a", ''))
	print(test_case.core.str_maps("shape"))
	b = test_case.get_openmc_baffle()
	print(str(b))
	#print(core)
	
	test_case.get_openmc_spacergrids(a.spacergrids, clean(a.params["grid_map"]), clean(a.params["grid_elev"]), 17, a.pitch)
	
	last_cell = list(mypin.cells.values())[-1]
	print(last_cell)
	print()
	#print(last_cell.region.surface())
	
	
	core_lattice = test_case.get_openmc_core()
	
	
	
	
