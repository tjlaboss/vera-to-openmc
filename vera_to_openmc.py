# Vera to OpenMC
#
# Takes a VERA case and attempts to construct 
# the required files for an OpenMC input.

from read_xml import Case
from functions import fill_lattice, clean
from math import sqrt, copysign
import objects

try:
	import openmc
except ImportError:
	raise SystemExit("Error: Cannot import openmc. You will not be able to generate OpenMC objects.")

# Global constants for counters
SURFACE, CELL, MATERIAL, UNIVERSE = range(-1,-5,-1)


class MC_Case(Case):
	'''An extension of the Case class from read_xml,
	customized with some new attributes and methods to 
	generate objects for OpenMC.'''
	def __init__(self, source_file):
		super(MC_Case, self).__init__(source_file)
		
		self.openmc_surfaces = {}; self.openmc_materials = {}
		
		# ID Counters
		self.openmc_surface_count = 0; self.openmc_cell_count = 0 ;self.openmc_material_count = 0; self.openmc_universe_count = 0
		
		
		# Create the essential moderator material
		'''The outside of each cell is automatically filled with the special material "mod", which refers to
		the moderator (or coolant). The composition of "mod" is calculated by the codes using the local T/H
		conditions and the soluble boron concentration, and cannot be specified by a user on a mat card.
		
		FIXME: The material uses a simple form of water as a placeholder and does NOT represent the actual
		composition of the moderator!
		The expected composition of "mod" appears in the STATE block of the VERA deck.'''
		self.__counter(MATERIAL)
		self.mod = openmc.Material(self.__counter(MATERIAL), "mod")
		self.mod.set_density("g/cc", 1.0)
		self.mod.add_nuclide("h-1", 2.0/3, 'ao')
		self.mod.add_nuclide("o-16", 1.0/3, 'ao')
		self.openmc_materials["mod"] = self.mod
		
	
	def __counter(self, count):
		'''Get the next cell/surface/material/universe number, and update the counter.
		Input:
			count:		CELL, SURFACE, MATERIAL, or UNIVERSE
		Output:
			integer representing the next cell/surface/material/universe ID'''
		if count == SURFACE:
			self.openmc_surface_count += 1
			return self.openmc_surface_count
		elif count == CELL:
			self.openmc_cell_count += 1
			return self.openmc_cell_count
		elif count == MATERIAL:
			self.openmc_material_count += 1
			return self.openmc_material_count
		elif count == UNIVERSE:
			self.openmc_universe_count += 1
			return self.openmc_universe_count
		else:
			raise IndexError("Index " + str(count) + " is not SURFACE, CELL, MATERIAL, or UNIVERSE.")
	
	
	def __get_xyz_planes(self, x0s = (), y0s = (), z0s = ()):
		'''
		Inputs:
			x0s:		list or tuple of x0's to check for; default is empty tuple
			y0s:		same for y0's
			z0s:		same for z0's
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
		
		# Check if such a surface exists, and add it to the lists if so
		for surf in self.openmc_surfaces.values():
			if surf.type == 'x-plane':
				for i in range(nx):
					if surf.x0 == x0s[i]:
						xlist[i] = surf
			elif surf.type == 'y-plane':
				for i in range(ny):
					if surf.y0 == y0s[i]:
						ylist[i] = surf
			elif surf.type == 'z-plane':
				for i in range(nz):
					if surf.z0 == z0s[i]:
						zlist[i] = surf
		
		# If the surface doesn't exist, create it anew
		for i in range(nx):
			if not xlist[i]:
				xp = openmc.XPlane(self.__counter(SURFACE), x0 = x0s[i])
				self.openmc_surfaces[xp.type + '-' + str(xp.id)] = xp
				xlist[i] = xp 
		for i in range(ny):
			if not ylist[i]:
				yp = openmc.YPlane(self.__counter(SURFACE), y0 = y0s[i])
				self.openmc_surfaces[yp.type + '-' + str(yp.id)] = yp
				ylist[i] = yp
		for i in range(nz):
			if not zlist[i]:
				zp = openmc.ZPlane(self.__counter(SURFACE), z0 = z0s[i])
				self.openmc_surfaces[zp.type + '-' + str(zp.id)] = zp 
				zlist[i] = zp
		
		return xlist, ylist, zlist
		
	
		
	def get_openmc_material(self, material):
		'''Given a vera material (objects.Material) as extracted by self.__get_material(),
		return an instance of openmc.Material. If the OpenMC Material exists, look it
		up in the dictionary. Otherwise, create it anew.
		
		Inputs:
			material:			string; key of the material in self.materials
		
		Outputs:
			openmc_material:	instance of openmc.Material
		
		All of the material fractions sum to either +1.0 or -1.0. If positive fractions are used, they
		refer to weight fractions. If negative fractions are used, they refer to atomic	fractions.
		'''
		
		try:
			# Look it up as normal
			openmc_material = self.openmc_materials[material]
		except KeyError:
			# Then the material really doesn't exist yet in OpenMC form
			# Generate it and add it to the index 
			vera_mat = self.materials[material]
			openmc_material = openmc.Material(self.__counter(MATERIAL), material)
			openmc_material.set_density("g/cc", vera_mat.density)
			for i in vera_mat.isotopes:
				nuclide = i
				frac = vera_mat.isotopes[i]
				if frac < 0:
					openmc_material.add_nuclide(nuclide, abs(frac), 'ao')			
				else:
					openmc_material.add_nuclide(nuclide, frac, 'wo')
			self.openmc_materials[material] = openmc_material
		
		return openmc_material
	
	
	'''def try_openmc_material(self, m):
		Check if a material exists; if it doesn't, add it to the index
		
		Input:
			m:		string; key of a VERA material in self.materials
		Output:
			mat:	instance of openmc.Material
		
		try:
			# Look it up as normal
			mat = self.openmc_materials[m]
		except KeyError:
			# Then the material really doesn't exist yet in OpenMC form
			# Generate it and add it to the index 
			mat = self.get_openmc_material(self.materials[m])
			self.openmc_materials[m] = mat
		
		return mat'''
	
	
	
	
	def get_openmc_pincell(self, vera_cell):
		'''Inputs:
			vera_cell:			instance of objects.Cell from the vera deck
		
		Outputs:
			pincell_universe:	instance of openmc.Universe, containing:
				.cells:				list of instances of openmc.Cell, describing the
									geometry and composition of this pin cell's universe
				.universe_id:	integer; unique identifier of the Universe
				.name:			string; more descriptive name of the universe (pin cell)			
			'''
		
		openmc_cells = []
		
		# First, define the OpenMC surfaces (Z cylinders)
		for ring in range(vera_cell.num_rings):
			r = vera_cell.radii[ring]
			name = vera_cell.name + "-ring" + str(ring)
			# Check if the outer bounding surface exists
			surf_id = None
			for s in self.openmc_surfaces.values():
				if (s.type == "z-cylinder"):
					if (s.r == r) and (s.x0 == 0) and (s.y0 == 0):
						# Then the cylinder is the same
						surf_id = s.id
						break # from the "for s in" loop
			if not surf_id:
				# Generate new surface and get its surf_id
				s = openmc.ZCylinder(self.__counter(SURFACE), "transmission", 0, 0, r)
				#cell_surfs[surf_id] = s
				# Add the new surfaces to the registry
				self.openmc_surfaces[str(surf_id)] = s
				
			# Otherwise, the surface s already exists
			# Proceed to define the cell inside that surface:
			new_cell = openmc.Cell(self.__counter(CELL), name)
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
			try:
				# First, check if this is a local, duplicate material
				fill = self.openmc_materials[vera_cell.asname + m]
				# This normally will not exist, so:
			except KeyError:
				fill = self.get_openmc_material(m)
			
				
			# What I want to do instead is, somewhere else in the code, generate the corresponding
			# openmc material for each objects.Material instance. Then, just look it up in that dictionary.			
			new_cell.fill = fill
			openmc_cells.append(new_cell)
		
		# end of "for ring" loop
		
		# Then add the moderator outside the pincell
		#FIXME: Check this for Cell2 in 2a_dep
		mod_cell = openmc.Cell(self.__counter(MATERIAL), vera_cell.name + "-Mod")
		mod_cell.fill = self.mod
		mod_cell.region = +s
		openmc_cells.append(mod_cell)
		
		# Create a new universe in which the pin cell exists 
		pincell_universe = openmc.Universe(self.__counter(UNIVERSE), vera_cell.name + "-verse")
		pincell_universe.add_cells(openmc_cells)
		
		return pincell_universe
	
	
	
	def get_openmc_assemblies(self, vera_asmbly):
	#TODO: Rename to get_openmc_lattices(vera_asmbly)
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
		# lower_nozzle_comp, lower_nozzle_height, lower_nozzle_mass,
		# upper_nozzle_comp, upper_nozzle_height, upper_nozzle_mass,
		# ppitch, title, num_pins, label
		openmc_asmblies = []
		
		# Instantiate all the pin cells (openmc.Universes) that appear in the Assembly
		cell_verses = {}
		for vera_cell in vera_asmbly.cells.values():
			c = self.get_openmc_pincell(vera_cell)
			cell_verses[vera_cell.label] = c
		
		
		for latname in vera_asmbly.axial_labels:
			openmc_asmbly = openmc.RectLattice(self.__counter(UNIVERSE), latname)
			openmc_asmbly.pitch = (pitch, pitch)
			openmc_asmbly.lower_left = [-pitch * float(npins) / 2.0] * 2
			# And populate with universes from cell_verses
			asmap = vera_asmbly.cellmaps[latname].square_map()
				
			openmc_asmbly.universes = fill_lattice(asmap, lambda c: cell_verses[c], npins)
			openmc_asmblies.append(openmc_asmbly)
		
		return openmc_asmblies
	
	
	def get_openmc_spacergrids(self, vera_grids, grid_labels, grid_elevations, npins, pitch):
		'''Placeholder function for now.
		
		Inputs:
			vera_grids:			dictionary of instances of SpacerGrid
			grid_labels:		list of strings (which appear in vera_grids.keys)
								referring to the next spacer grid that exists.s
			grid_elevations:	list of floats (of len(grid_labels));
								heights (cm) of the grid midpoints
			npins:				integer; (npins)x(npins) fuel bundle 
		Outputs:
			None
		'''
		
		for i in range(len(grid_elevations)):
			z = grid_elevations[i]
			grid = vera_grids[grid_labels[i]]
			
			# Thickness of one edge of the spacer
			# The actual spacer wall between two cells will be twice this thickness
			'''Math: How we calculate the thickness 't' of the spacer around 1 cell.
			
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
			
			It turns out that the negative solution to the root is correct
			(positive produces thicknesses of greater than the pitch, which is
			physically impossible). As a check, the thickness should be approximately
			equal to one fourth [one wall] of one pin's spacer's area, divided by the pitch.
			To verify this, uncomment the print statement in the next block of code.'''
			
			A = grid.mass / self.materials[grid.material].density / grid.height
			t = 0.5*(pitch - sqrt(pitch**2 - A/npins**2))
			est = A/(4.0*pitch*npins**2)
			#print("t="+str(t) + " cm;\tshould be close to " + str(est))
			
			# Then do something to model the grid...
		
		return None
	
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
	
	
	def get_openmc_assembly(self, vera_asmbly):
		'''Creates an OpenMC fuel assembly, complete with lattices
		of fuel pins and spacer grids, that should be equivalent to what
		is constructed by VERA.
		
		Inputs:
			vera_asmbly:		instance of objects.Assembly
		
		Outputs:
			openmc_asmbly:		instance of openmc.Universe containing
								the lattices, spacers, and such
		'''
		
		ps = vera_asmbly.params
		pitch = vera_asmbly.pitch
		npins = vera_asmbly.npins
		
		# Start by getting the lattices and layers
		lattices = self.get_openmc_assemblies(vera_asmbly)
		#lattices = self.get_openmc_lattices(vera_asmbly)
		nlats = len(lattices)
		
		for layer in range(nlats):
			z = vera_asmbly.axial_elevations[layer]
			label = vera_asmbly.axial_labels[layer]
			lat = lattices[layer]
		
		
		
		return None
	
	
	def get_openmc_reactor_vessel(self, vera_core):
		'''Creates the pressure vessel representation in OpenMC
		
		Inputs:
			vera_core:		instance of objects.Core
		
		Outputs:
			openmc_core:	instance of openmc.Universe containing all the cells
							describing the reactor pressure vessel EXCEPT inside_cell
			inside_cell:	instance of openmc.Cell containing the innermost ring
							of the vessel, TO BE FILLED with assemblies
			inside_fill:	string; key of the openmc.Material to fill all spaces
							within inside_cell, outside of the assemblies
			outer_surfs:	instances of openmc.Surface (specifically, ZCylinder and ZPlane)
							describing the bounding	surfaces of the reactor vessel
		'''
		
		ps = vera_core.params
		core_cells = []
		
		# Create the top and bottom planes of the core and core plate
		plate_bot = openmc.ZPlane(self.__counter(SURFACE),
							z0 = -vera_core.bot_refl.thick, boundary_type = vera_core.bc["bot"])
		core_bot = openmc.ZPlane(self.__counter(SURFACE), z0 = 0.0)
		core_top = openmc.ZPlane(self.__counter(SURFACE), z0 = vera_core.height)
		plate_top = openmc.ZPlane(self.__counter(SURFACE),
							z0 = vera_core.height + vera_core.top_refl.thick, boundary_type = vera_core.bc["top"])
		
		# Create the concentric cylinders of the vessel
		for ring in range(len(vera_core.vessel_radii) - 1):
			r = vera_core.vessel_radii[ring]
			m = vera_core.vessel_mats[ring]
			
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
		s = openmc.ZCylinder(self.__counter(SURFACE), R = max(vera_core.vessel_radii), boundary_type = vera_core.bc["rad"])
		new_cell = openmc.Cell(self.__counter(CELL), "Vessel-Outer")
		new_cell.region = -s    & +plate_bot & -plate_top
		core_cells.append(new_cell)
		
		# Add the core plates
		top_plate_mat = self.get_openmc_material(vera_core.bot_refl.material)
		self.openmc_materials[top_plate_mat.name] = top_plate_mat
		top_plate_cell = openmc.Cell(self.__counter(CELL), "Top core plate")
		top_plate_cell.region = -vessel_surf & + core_top & -plate_top
		top_plate_cell.fill = top_plate_mat
		core_cells.append(top_plate_cell)
		
		bot_plate_mat = self.get_openmc_material(vera_core.bot_refl.material)
		self.openmc_materials[bot_plate_mat.name] = bot_plate_mat
		bot_plate_cell = openmc.Cell(self.__counter(CELL), "Bot core plate")
		bot_plate_cell.region = -vessel_surf & + core_bot & -plate_bot
		bot_plate_cell.fill = bot_plate_mat
		core_cells.append(bot_plate_cell)
		
		outer_surfs = (vessel_surf, plate_bot, plate_top) 
		
		openmc_core = openmc.Universe(self.__counter(UNIVERSE), "Reactor Vessel")
		openmc_core.add_cells(core_cells)
		
		return openmc_core, inside_cell, inside_fill, outer_surfs
	
	
	def get_openmc_baffle(self, vera_core):
		'''Generate the surfaces and cells required to model the baffle plates.
		
		**ASSUMPTION: All shape maps will have at most 2 edges
		(no single protruding assemblies will be present). This may not be valid;
		a few more lines of code in the if blocks can remedy this.
		
		Inputs:
			vera_core:		instance of objects.Core
		Outputs:
			baffle_cells:	list of instances of openmc.Cell,
							describing the baffle plates	
		'''
		baffle_cells = []
		
		baf = vera_core.baffle		# instance of objects.Baffle
		pitch = vera_core.pitch		# assembly pitch
		
		# Useful distances
		d1 = pitch/2.0 + baf.gap 	# dist from center of asmbly to inside of baffle
		d2 = d1 + baf.thick			# dist from center of asmbly to outside of baffle 
		width = vera_core.size * vera_core.pitch / 2.0	# dist from center of core to center of asmbly
		
		cmap = vera_core.square_maps("s", '')
		n = vera_core.size - 1
		
		'''
		# Corner cases
				if (i == 0) and (j == 0):
					#TODO: top left corner
					continue
				elif (i == 0) and (j == n):
					#TODO: bottom left corner
					continue
				elif (i == n) and (j == 0):
					#TODO: bottom right corner
					continue
				elif (i == n) and (j == n):
					#TODO: bottom left corner
					continue
				
				# Edge cases
				elif i == 0:
					#TODO: Left edge
					continue
				elif j == 0:
					#TODO: Top edge
					continue
				elif i == n:
					#TODO: Right edge
					continue
				elif j == n:
					#TODO: Bottom edge
					continue
		'''
		
		'''A note about the baffle Cells:
		
		Currently, I'm creating an individual cell for each little segment of the baffle plates.
		        __________
		       |__________|
		       | |             Like this, so that the segment shown
		       | |             here would be composed of 3 Cells.
		 ______|_|
		|________|
		
		It might be more efficient just to generate the regions of each of the cells,
		concatenate each i^th region onto a "master region" using union operators,
		and assign the master region to a single baffle Cell at the end of the loop.

		I plan to see if it makes sense to do this once I've verified that the independent
		Cells work as expected.		'''
		
		
		# Useful lambda functions
		# These will be used for both x and y
		x1 = lambda x: x + copysign(d1, x);				# To inner edge of this baffle
		x2 = lambda x: x + copysign(d2, x);				# To outer edge of this baffle
		x3 = lambda x: x2(x) - copysign(pitch, x);		# To outer edge of next baffle
		
		
		# Regular: assemblies on all sides
		
		# For each row (moving vertically):
		for j in range(1,n):
			# For each column (moving horizontally):
			for i in range(1,n):
				
				
				this = cmap[j][i]
				if this:
					# Positions of surfaces
					x = (i - 0.5)*pitch - width;	y = width - (j - 0.5)*pitch
					
					north = cmap[j-1][i]
					south = cmap[j+1][i]
					east  = cmap[j][i+1]
					west  = cmap[j][i-1]
					
					
					if (north and south and east and west):
						# Surrounded; don't make the surfaces
						continue
					else:
						# At least 1 baffle plate to add
						
						# Check if necessary surfs exist; if not, create them
						((left1, left2, right2), (top1, top2, bot2)) = self.__get_xyz_planes( \
												( x1(x), x2(x), x3(x)), (x1(y), x2(y), x3(y)) )[0:2]
						
						'''Naming convention:
						
						"left" and "top" refer to the positions in the NE quadrant, so that
							- left1 is far to the left (inner edge of plate)
							- left2 is the farthest to the left (outer edge of plate)
							- right2 is left2 + the pitch (would be leftmost edge of next plate)
						
						For the other quadrants, the plane names have been kept, but their positions
						are *mirrored*; so in the SW quadrant, "top" actually means "bottom", as shown:
						
								 NW: straight		|	NE: mirrored horiz
								------------------------------------------------
								 SW: mirrored vert	|	SE: mirrored horiz+vert						'''
						
						# Northwest (Top left corner)
						if (not north) and (not west) and (south) and (east):
							#region = +left2 & -left1 & +top1 & -top2
							new_top_cell = openmc.Cell(self.__counter(CELL), name="baffle-nw-top")
							new_top_cell.region = +left2 & -right2 & +top1 & -top2
							baffle_cells.append(new_top_cell)
							
							new_side_cell = openmc.Cell(self.__counter(CELL), name="baffle-nw-left")
							new_side_cell.region = +left2 & -left1 & +bot2 & -top1
							baffle_cells.append(new_side_cell)
						# Northeast (Top right corner)
						elif (not north) and (not east) and (south) and (west):
							new_top_cell = openmc.Cell(self.__counter(CELL), name = "baffle-ne-top")
							new_top_cell.region = +right2 & -left2 & +top1 & -top2
							baffle_cells.append(new_top_cell)

							new_side_cell = openmc.Cell(self.__counter(CELL), name = "baffle-ne-right")
							new_side_cell.region = +bot2 & -top1 & +left1 & -left2
							baffle_cells.append(new_side_cell)
						# Southwest (Bottom left corner)
						elif (not south) and (not west) and (north) and (east):
							new_top_cell = openmc.Cell(self.__counter(CELL), name = "baffle-ne-bot")
							new_top_cell.region = +left2 & -right2 & +top2 & -top1
							baffle_cells.append(new_top_cell)
							
							new_side_cell = openmc.Cell(self.__counter(CELL), name = "baffle-ne-left")
							new_side_cell.region = +left2 & -left1 & +top2 & -bot2
							baffle_cells.append(new_side_cell) 
						# Southeast (Bottom right corner)
						elif (not south) and (not east) and (north) and (west):
							new_top_cell = openmc.Cell(self.__counter(CELL), name = "baffle-se-bot")
							new_top_cell.region = +right2 & -left2 & +top2 & -top1
							baffle_cells.append(new_top_cell)

							new_side_cell = openmc.Cell(self.__counter(CELL), name = "baffle-se-right")
							new_side_cell.region = +top1 & -bot2 & +left1 & -left2
							baffle_cells.append(new_side_cell)
							
							
						# TODO: Regular edges (no corners)
						
						# North (top only)
						elif (not north) and (east) and (south) and (west):
							new_top_cell = openmc.Cell(self.__counter(CELL), name = "baffle-n-top")
							new_top_cell.region = +left2 & -right2 & +top1 & -top2
							baffle_cells.append(new_top_cell)
							
						# South (bottom only)
						elif (not south) and (east) and (north) and (west):
							new_top_cell = openmc.Cell(self.__counter(CELL), name = "baffle-s-bot")
							new_top_cell.region = +left2 & -right2 & +top2 & -top1
							baffle_cells.append(new_top_cell)
						
						# West (left only)
						elif (not west) and (east) and (north) and (south):
							new_side_cell = openmc.Cell(self.__counter(CELL), name = "baffle-w-left")
							if bot2.y0 > top1.y0:
								new_side_cell.region = +left2 & -left1 & +top1 & -bot2
							else:
								new_side_cell.region = +left2 & -left1 & +bot2 & -top1
							baffle_cells.append(new_side_cell)
						
						# East (right only)
						elif (not east) and (south) and (north) and (west):
							new_side_cell = openmc.Cell(self.__counter(CELL), name = "baffle-e-right")
							if bot2.y0 > top1.y0:
								new_side_cell.region = +left2 & -left1 & +top1 & -bot2
							else:
								new_side_cell.region = +left2 & -left1 & +bot2 & -top1
							baffle_cells.append(new_side_cell)
						
						
				else:
					# Do anything if not an assembly position?
					continue
		
		
		# EDGE CASES
		for i in range(1, n-1):
			
			# Top row
			if cmap[0][i]: 	# Assembly is present
				
				y = width - 0.5*pitch
				x = (i - 0.5)*pitch - width
				
				((left2, right2), (top1, top2, bot2)) = self.__get_xyz_planes( ( x2(x), x3(x) ), ( x1(y), x2(y), x3(y) ), () )[0:2]
				# Add a top row
				new_top_cell = openmc.Cell(self.__counter(CELL), "top edge")
				new_top_cell.region = +left2 & -right2 & +top1 & -top2
				baffle_cells.append(new_top_cell)
				
				west = cmap[0][i-1]
				east = cmap[0][i+1]
				south = cmap[1][i]
				
				# Left edge
				if (not west): 
					left1 = self.__get_xyz_planes( (x1(x),), (), () )[0][0]
					new_side_cell = openmc.Cell(self.__counter(CELL), "top edge (left)")
					new_side_cell.region = +left1 & -left2 & +top1 & -top2
					baffle_cells.append(new_side_cell)
				# Right edge
				if (not east): 
					right1 = self.__get_xyz_planes( (x1(x) + pitch,), (), () )[0][0]
					new_side_cell = openmc.Cell(self.__counter(CELL), "top edge (right)")
					new_side_cell.region = +right2 & -right1 & +top1 & -top2
					baffle_cells.append(new_side_cell)
			
				
			# Bottom row
			if cmap[n][i]:	 	# Assembly is present
				y = -(width - 0.5*pitch)
				x =  (i - 0.5)*pitch - width
				
				((left2, right2), (top1, top2, bot2)) = self.__get_xyz_planes( ( x2(x), x3(x) ), ( x1(y), x2(y), x3(y) ), () )[0:2]
				
				# Add a bottom row
				new_top_cell = openmc.Cell(self.__counter(CELL), "bottom edge")
				new_top_cell.region = +left2 & -right2 & +top2 & -top1
				baffle_cells.append(new_top_cell)
				
				west = cmap[n][i-1]
				east = cmap[n][i+1]
				north= cmap[n-1][i]
				
				# Left edge
				if (not west): 
					left1 = self.__get_xyz_planes( (x1(x),), (), () )[0][0]
					new_side_cell = openmc.Cell(self.__counter(CELL), "bottom edge (left)")
					new_side_cell.region = +left1 & -left2 & +top2 & -top1
					baffle_cells.append(new_side_cell)
				# Right edge
				if (not east): 
					right1 = self.__get_xyz_planes( (x1(x) + pitch,), (), () )[0][0]
					new_side_cell = openmc.Cell(self.__counter(CELL), "bottom edge (right)")
					new_side_cell.region = +right2 & -right1 & +top2 & -top1
					baffle_cells.append(new_side_cell)
			
				
			# Left column
			if cmap[i][0]:	 		# Assembly is present
				continue
			
			# Right column
			if cmap[i][n]:	 	# Assembly is present
				continue
				
				
				
		
		
		# Set ALL baffle cell materials in one fell swoop		
		for cell in baffle_cells:
			cell.fill = self.get_openmc_material(baf.mat)
			print(cell)
		
		return baffle_cells
			
	
	
	

if __name__ == "__main__":
	# Instantiate a test case with a simple VERA XML.gold
	filename = "p7.xml.gold"
	#filename = "2a_dep.xml.gold"
	#filename = "2o.xml.gold"
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
	
	#mc_test_mat = test_case.get_openmc_material(test_case.materials["pyrex"])
	#print mc_test_mat
	
	#print test_case.mod
	
	
	'''Note: Attempting to print an assembly in Python 2.7 doesn't work. Could be due to a bug in the
	__repr__() method? Printing here yields an AttributeError: 'NoneType' object has no attribute '_id',
	and printing the example assembly from the OpenMC Python API docs
	<http://openmc.readthedocs.io/en/latest/pythonapi/examples/pandas-dataframes.html>
	causes a TypeError: 'NoneType' object has no attribute '__getitem__'

	Works in Python 3.5.'''
	
	test_asmblys = test_case.get_openmc_assemblies(a)[0]
	#print(test_asmbly)
	
	#print('\n', a.name, test_asmblys.name, '\n')
	#for cmap in test_case.core.str_maps(space = "~"):
	#	print(cmap)
	
	core, icell, ifill, cyl = test_case.get_openmc_reactor_vessel(test_case.core)
	#print(test_case.core.square_maps("a", ''))
	print(test_case.core.str_maps("shape"))
	b = test_case.get_openmc_baffle(test_case.core)
	print(len(b))
	#print(core)
	
	test_case.get_openmc_spacergrids(a.spacergrids, clean(a.params["grid_map"]), clean(a.params["grid_elev"]), 17, a.pitch)

