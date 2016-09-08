# test_baffle_generate_simple.py
#
# Simplified version of the baffle test. All required classes, except
# those in OpenMC, have been copied here. The real version will get
# most of this information from the VERA input deck, but a simplified
# case with a smaller core is hardcoded below for debugging purposes. 

import openmc
from math import copysign


# Global constants for counters
SURFACE, CELL, MATERIAL, UNIVERSE = range(-1,-5,-1)
	
class Baffle(object):
	'''Inputs:
		mat:	instance of Material
		thick:	thickness of baffle (cm)
		gap:	thickness of gap (cm) between the outside assembly
				(including the assembly gap) and the baffle itself
		'''
	def __init__(self, mat, thick, gap):
		self.mat = mat
		self.thick = thick
		self.gap = gap
	def __str__(self):
		return "Baffle (" + self.thick + " cm thick)"


class Simplified_Vera_Core(object):
	'''A core with only the bare minimum attributes to run this test example'''
	def __init__(self, ppitch, npins):
		self.pitch = npins*ppitch + 1.0	# Assembly pitch; includes an arbitrary 1cm gap	
		self.size = 5
		self.baffle = None
		self.openmc_surfaces = {}#; self.openmc_cells = []
		self.openmc_surface_count = 0;	self.openmc_cell_count = 0
	
	def shape_map(self):
		smap = [[0, 1, 1, 1, 0],
				[1, 1, 1, 1, 1],
				[1, 1, 1, 1, 1],
				[1, 1, 1, 1, 1],
				[0, 1, 1, 1, 0]]
		return smap
	

	
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
		
		# Check if such a surface exists, and add it to the lists if so
		for surf in self.openmc_surfaces.values():
			if surf.type == 'x-plane':
				for i in range(nx):
					if round(surf.x0, rd) == round(x0s[i], rd):
						xlist[i] = surf
			elif surf.type == 'y-plane':
				for i in range(ny):
					if round(surf.y0, rd) == round(y0s[i], rd):
						ylist[i] = surf
			elif surf.type == 'z-plane':
				for i in range(nz):
					if round(surf.z0, rd) == round(z0s[i], rd):
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
		baf = vera_core.baffle		# instance of objects.Baffle
		pitch = vera_core.pitch		# assembly pitch
		
		# Useful distances
		d0 = pitch/2.0				# dist from center of asmbly to edge of asmbly
		d1 = d0 + baf.gap 			# dist from center of asmbly to inside of baffle
		d2 = d1 + baf.thick			# dist from center of asmbly to outside of baffle 
		width = vera_core.size * vera_core.pitch / 2.0	# dist from center of core to center of asmbly
		
		cmap = vera_core.shape_map()
		n = vera_core.size - 1
		
		# Unite all individual regions with the Master Region
		master_region = openmc.Union()
		
		
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
		Cells work as expected.		
		
		
		To model the gap, there will be a "buffer zone" of assembly-sized moderator cells
		around all edges of the core lattice. The complement of the baffle.region will
		be filled with the core lattice: fuel assemblies (and a little bit of a gap) will
		go on the inside, and just moderator on the outside until the pressure vessel is reached. 
		
		'''
		
		
		# Useful lambda functions
		# These will be used for both x and y
		x0 = lambda x: x + copysign(d0, x)			# To edge of this assembly	    (a)
		x1 = lambda x: x + copysign(d1, x)			# To inner edge of this baffle  (a+gap)
		x2 = lambda x: x + copysign(d2, x)			# To outer edge of this baffle  (a+gap+thick)
		x3 = lambda x: x - copysign(d0, x) 			# To other edge of this asmbly (-a)
		x4 = lambda x: x - copysign(d1, x)			# To outer edge of next baffle (-a-gap)
		x5 = lambda x: x - copysign(d2, x)			# To inner edge of next baffle (-a-gap-thick)
		xc = lambda x: x - copysign(d1 - baf.thick, x)# To     edge of next crossing baffle
		xb = lambda x: xc(x) - copysign(pitch, x) 	  # To     edge of this crossing baffle
		
		
		# Regular: assemblies on all sides
		
		# For each row (moving vertically):
		for j in range(1,n):
			# For each column (moving horizontally):
			for i in range(1,n):
				
				
				this = cmap[j][i]
				if this:
					# Positions of surfaces
					x = (i + 0.5)*pitch - width;	y = width - (j + 0.5)*pitch
					
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
						((xthis0, xthis1, xthis2, xthisc, xnext0, xnext2, xnext1, xnextc), 
						 (ythis0, ythis1, ythis2, ythisc, ynext0, ynext2, ynext1, ynextc)) \
							= self.__get_xyz_planes(\
							(x0(x), x1(x), x2(x), xb(x), 	x3(x), x4(x), x5(x), xc(x)), \
							(x0(y), x1(y), x2(y), xb(y), 	x3(y), x4(y), x5(y), xc(y)) )[0:2]
						
						'''Old Naming convention:
						
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
							top_region = (+xthis2 & -xnext0 & +ythis1 & -ythis2)
							master_region.nodes.append(top_region)
							
							side_region = (+xthis2 & -xthis1 & +ynext0 & -ythis1)
							master_region.nodes.append(side_region)
						
						# Northeast (Top right corner)
						elif (not north) and (not east) and (south) and (west):
							# Left and Right are inverted
							top_region = (+xnext0 & -xthis2 & +ythis1 & -ythis2)
							master_region.nodes.append(top_region)
							
							side_region = (+xthis1 & -xthis2 & +ynext0 & -ythis1)
							master_region.nodes.append(side_region)
												
						# Southwest (Bottom left corner)
						elif (not south) and (not west) and (north) and (east):
							# Top and Bottom are inverted
							top_region = (+xthis2 & -xnext0 & +ythis2 & -ythis1)
							master_region.nodes.append(top_region)
							
							side_region = (+xthis2 & -xthis1 & +ythis1 & -ynext0)
							master_region.nodes.append(side_region)
						
						# Southeast (Bottom right corner)
						elif (not south) and (not east) and (north) and (west):
							# Left and Right are inverted
							# Top and Bottom are inverted
							top_region = (+xnext0 & -xthis2 & +ythis2 & -ythis1)
							master_region.nodes.append(top_region)
							
							side_region = (+xthis1 & -xthis2 & +ythis1 & -ynext0)
							master_region.nodes.append(side_region)
							
						
						# North (top only)
						elif (not north) and (east) and (south) and (west):
							#if left2.x0 < right2.x0:
							#	top_region = (+left1 & -right2 & +top1 & -top2)
							#else:
							#	top_region = (+right1 & -left2 & +top1 & -top2)
							if xthis0.x0 < xnext0.x0:
								top_region = (+xthis0 & -xnext0 & +ythis1 & -ythis2)
							else:
								top_region = (+xnext0 & -xthis0 & +ythis1 & -ythis2)
							master_region.nodes.append(top_region)
							
		
						# South (bottom only)
						elif (not south) and (east) and (north) and (west):
							#new_top_cell = openmc.Cell(self.__counter(CELL), name = "baffle-s-bot")
							#new_top_cell.region = +left2 & -right2 & +top2 & -top1
							#baffle_cells.append(new_top_cell)
							if xthis0.x0 < xnext0.x0:
								top_region = (+xthis0 & -xnext0 & +ythis2 & -ythis1)
							else:
								top_region = (+xnext0 & -xthis0 & +ythis2 & -ythis1)
							master_region.nodes.append(top_region)
							
												
						# West (left only)
						elif (not west) and (east) and (north) and (south):
							if ythis0.y0 < ynext0.y0:
								side_region = (+xthis2 & -xthis0 & +ythis0 & -ynext0)
							else:
								side_region = (+xthis2 & -xthis0 & +ynext0 & -ythis0)
							master_region.nodes.append(side_region)
						
						# East (right only)
						elif (not east) and (south) and (north) and (west):
							if ythis0.y0 < ynext0.y0:
								side_region = (+xthis0 & -xthis2 & +ythis0 & -ynext0)
							else:
								side_region = (+xthis0 & -xthis2 & +ynext0 & -ythis0)
							master_region.nodes.append(side_region)

						
				else:
					# Do anything if not an assembly position?
					from warnings import warn
					warnstr = "Error at i=" + str(i) + ", j=" + str(j) + " (x=" + str(x) + ", y=" + str(y) + ");\n" +\
								"Unexpected geometry encountered. There may be a gap in the baffle." 
					warn(warnstr)
					#continue
		
		
		# EDGE CASES
		
		for i in range(1, n):
			
			# Top row
			if cmap[0][i]: 	# Assembly is present
				y = width - 0.5*pitch
				x = (i + 0.5)*pitch - width
				# Need to use -0 for copysign(), in the lambda functions
				if x == 0:	x = -0.0
				
				((xthis1, xthis2, 		xnext2, xnext1), 
				 (ythis1, ythis2, 		ynext2, ynextc)) \
					= self.__get_xyz_planes(\
					(x1(x), x2(x),  	x4(x), x5(x)), \
					(x1(y), x2(y),  	x4(y), xc(y)) )[0:2]
							
				west  = cmap[0][i-1]
				east  = cmap[0][i+1]
				south = cmap[0+1][i]
				
				# Make the top region that applies in every case
				if xthis2.x0 < xnext2.x0:
					top_region = (+xthis2 & -xnext1 & +ythis1 & -ythis2)
				else:
					top_region = (+xnext2 & -xthis1 & +ythis1 & -ythis2)
				master_region.nodes.append(top_region)
				
				# Left/right edges (vertical)
				if (not west) or (not east): 
					if xthis1.x0 < xthis2.x0:
						side_region = (+xthis1 & -xthis2 & +ynextc & -ythis2)
					else:
						side_region = (+xthis2 & -xthis1 & +ynextc & -ythis2)
					master_region.nodes.append(side_region)
					# And then the peninsula case
					if (not west) and (not east):
						if xnext1.x0 < xnext2.x0:
							side_region = (+xnext1 & -xnext2 & +ynext2 & -ythis2)
						else:
							side_region = (+xnext2 & -xnext1 & +ynext2 & -ythis2)
						master_region.nodes.append(side_region)
				
				
			# Bottom row
			if cmap[n][i]:	 	# Assembly is present
				y = -(width - 0.5*pitch)
				x =  (i + 0.5)*pitch - width
				# Force signed 0 
				if x == 0.0:	x = -0.0
				
				((xthis1, xthis2,  	xnext2, xnext1), 
				 (ythis1, ythis2,  	ynext0)) \
					= self.__get_xyz_planes(\
					(x1(x), x2(x), 	x4(x), x5(x)), \
					(x1(y), x2(y), 	x3(y)) 		 )[0:2]
				
				# Make the bottom region that applies in every case
				if xthis2.x0 < xnext2.x0:
					bot_region = (+xthis2 & -xnext1 & +ythis2 & -ythis1)
				else:
					bot_region = (+xnext2 & -xthis1 & +ythis2 & -ythis1)
				master_region.nodes.append(bot_region)
				
				west = cmap[n][i-1]
				east = cmap[n][i+1]
				north= cmap[n-1][i]
				
				# Left/right edges (vertical)
				if (not west) or (not east): 
					if xthis1.x0 < xthis2.x0:
						side_region = (+xthis1 & -xthis2 & +ythis2 & -ynext0)
					else:
						side_region = (+xthis2 & -xthis1 & +ythis2 & -ynext0)
					master_region.nodes.append(side_region)
					# Peninsula case
					if (not west) and (not east):
						if xnext1.x0 < xnext2.x0:
							side_region = (+xnext1 & -xnext2 & +ythis2 & -ynext0)
						else:
							side_region = (+xnext2 & -xnext1 & +ythis2 & -ynext0)
						master_region.nodes.append(side_region)
			
				
			# Left column
			if cmap[i][0]:	 		# Assembly is present
				x = -(width - 0.5*pitch)
				y =  width - (i + 0.5)*pitch
				# Force a signed zero
				if y == 0:  y = -0.0
				
				((xthis1, xthis2, 	xnext2), 
				 (ythis1, ythis2, 	ynext2, ynext1)) \
					= self.__get_xyz_planes(\
					(x1(x), x2(x),  	x4(x)), \
					(x1(y), x2(y),  	x4(y), x5(y)) )[0:2]
				
				# Add a left column
				if ythis1.y0 < ynext2.y0:
					side_region = (+xthis2 & -xthis1 & +ythis1 & -ynext2)

				else:
					side_region = (+xthis2 & -xthis1 & +ynext2 & -ythis1)
				master_region.nodes.append(side_region)
				
				east  = cmap[i][0+1]
				north = cmap[i-1][0]
				south = cmap[i+1][0]
				
				# Top/bottom edges (horizontal)
				if (not north) or (not south):
					if ythis1.y0 < ythis2.y0:
						top_region = (+xthis2 & -xnext2 & +ythis1 & -ythis2)
					else:
						top_region = (+xthis2 & -xnext2 & +ythis2 & -ythis1)
					master_region.nodes.append(top_region)
					# Then the special case where it's just a single assembly piece
					if (not north) and (not south):
						if ynext1.y0 < ynext2.y0:
							bot_region = (+xthis2 & -xnext2 & +ynext1 & -ynext2)
						else:
							bot_region = (+xthis2 & -xnext2 & +ynext2 & -ynext1)
						master_region.nodes.append(bot_region)
				
						
			# Right column
			if cmap[i][n]:	 	# Assembly is present
				x = width - 0.5*pitch
				y = width - (i + 0.5)*pitch
				if y == 0:	y = +0.0
				
				((xthis0, xthis1, xthis2, xthisc, xnext0, xnext2, xnext1, xnextc), 
				 (ythis0, ythis1, ythis2, ythisc, ynext0, ynext2, ynext1, ynextc)) \
					= self.__get_xyz_planes(\
					(x0(x), x1(x), x2(x), xb(x), 	x3(x), x4(x), x5(x), xc(x)), \
					(x0(y), x1(y), x2(y), xb(y), 	x3(y), x4(y), x5(y), xc(y)) )[0:2]
			
				# Add a right column
				if ythis1.y0 < ynext1.y0:
					side_region = (+xthis1 & -xthis2 & +ythis2 & -ynext1)
				else:
					side_region = (+xthis1 & -xthis2 & +ynext2 & -ythis1)
				master_region.nodes.append(side_region)
				
				west  = cmap[i][n-1]
				north = cmap[i-1][n]
				south = cmap[i+1][n]
				
				# Top/bottom edges (horizontal)
				if (not north) or (not south):
					if ythis1.y0 < ythis2.y0:
						top_region = (+xnext2 & -xthis2 & +ythis1 & -ythis2)
					else:
						top_region = (+xnext2 & -xthis2 & +ythis2 & -ythis1)
					master_region.nodes.append(top_region)
					# Then the special case where it's just a single assembly piece
					if (not north) and (not south):
						if ynext1.y0 < ynext2.y0:
							bot_region = (+xnext2 & -xthis2 & +ynext1 & -ynext2)
						else:
							bot_region = (+xnext2 & -xthis2 & +ynext2 & -ynext1)
						master_region.nodes.append(bot_region)
					
				
				#TODO: EDGE CASES HAVE BEEN VERIFIED UP TO WORK AS EXPECTED UP TO HERE
		
				# TODO: Add 4 corner cases
		
		
		
		# Set the baffle material here
		# TODO:
		
		return master_region


###################

	
def test_baffle(baffle_region, baffill, asmbly_lat, bounds):
	'''Test the get_openmc_baffle() function for geometric integrity.
	
	Inputs:
		baffle_cells:	list of instances of openmc.Cell describing the baffle make-up 
		asmbly_lat:		instance of openmc.RectLattice describing the core layout
		bounds:			tuple of instances of openmc.Surface that fall within asmbly_lat,
						but outside the baffle.
	
	Output:
		core_universe:	instance of openmc.Universe containing the baffle and the core lattice
	'''
	
	
	
	(min_x, max_x, min_y, max_y, min_z, max_z) = bounds
	
	core_universe = openmc.Universe()
	box = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	
	the_baffle = openmc.Cell(101, name = "the baffle")
	the_baffle.region = baffle_region
	#the_baffle.region = baffle_cells[0].region
	#for c in baffle_cells[1:len(baffle_cells)]:
	#	the_baffle.region = the_baffle.region | c.region
	#the_baffle.region = the_baffle.region & (+min_z & -max_z)
	the_baffle.fill = baffill
	
	print(the_baffle)
	
	not_the_baffle = openmc.Cell(102, name = "not the baffle")
	not_the_baffle.region = ~the_baffle.region & box
	not_the_baffle.fill = asmbly_lat
	
	core_universe.add_cells((the_baffle, not_the_baffle))
	
	return core_universe
	
	
def set_settings(pitch):
	# OpenMC simulation parameters
	min_batches = 20
	max_batches = 200
	inactive = 5
	particles = 2500
	
	# Instantiate a Settings object
	settings_file = openmc.Settings()
	settings_file.batches = min_batches
	settings_file.inactive = inactive
	settings_file.particles = particles
	settings_file.output = {'tallies': False}
	settings_file.trigger_active = True
	settings_file.trigger_max_batches = max_batches
	# Create an initial uniform spatial source distribution over fissionable zones
	#pitch = 10
	bounds = (-pitch/2.0,)*3 + (pitch/2.0,)*3
	uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:], only_fissionable=True)  # @UndefinedVariable
	settings_file.source = openmc.source.Source(space=uniform_dist)
	settings_file.export_to_xml()
	
	
	

def set_cubic_boundaries(pitch, n, bounds=('reflective',)*6):
	'''Inputs:
		pitch:		float; pitch between fuel pins 
		n:			int; number of fuel pins in an assembly (usually 1 or 17)
		bounds:		tuple/list of strings with len=6, containing the respective
					boundary types for min/max x, y, and z (default: all reflective)
	
	Outputs:
		a tuple of the openmc X/Y/ZPlanes for the min/max x, y, and z boundaries
	'''
	
	min_x = openmc.XPlane(x0=-n*pitch/2.0, boundary_type=bounds[0])
	max_x = openmc.XPlane(x0=+n*pitch/2.0, boundary_type=bounds[1])
	min_y = openmc.YPlane(y0=-n*pitch/2.0, boundary_type=bounds[2])
	max_y = openmc.YPlane(y0=+n*pitch/2.0, boundary_type=bounds[3])
	min_z = openmc.ZPlane(z0=-n*pitch/2.0, boundary_type=bounds[4])
	max_z = openmc.ZPlane(z0=+n*pitch/2.0, boundary_type=bounds[5])
	
	return (min_x, max_x, min_y, max_y, min_z, max_z)



def create_openmc_materials():
	
	# Essential materials
	mod = openmc.Material(name="mod")
	mod.add_nuclide("h-1", 1)
	mod.set_density("g/cc", 1.0)
	
	fuel = openmc.Material(name="u31")
	fuel.add_nuclide("u-238", (100-3.1)/100.0, 'wo')
	fuel.add_nuclide("u-235", (3.1)/100.0, 'wo')
	fuel.set_density("g/cc", 10.0)
	
	clad = openmc.Material(name="iron")
	clad.add_nuclide("fe-56", 1, 'wo')
	clad.set_density("g/cc", 7.0)
	
	
	materials = openmc.Materials((mod, fuel, clad))
	materials.default_xs = "71c"
	materials.export_to_xml()
	
	return materials
	

def create_9x9_lattice(materials, pitch):
	(mod, fuel, clad)  = materials
	
	# Make the pin surfaces
	ring0 = openmc.ZCylinder(R = 0.5)
	ring1 = openmc.ZCylinder(R = 0.75)
	#baf_in = openmc.ZCylinder(R = 5.0)
	#baf_out = openmc.ZCylinder(R = baf_in.coefficients['R'] + 1.0)
	#vessel = openmc.ZCylinder(R = 10)
	
	
	# Make the pin cells
	# Universe for the lattice
	cell0 = openmc.Cell()
	cell0.region = -ring0
	cell0.fill = fuel
	cell1 = openmc.Cell()
	cell1.region = -ring1 & +ring0
	cell1.fill = clad
	cell2 = openmc.Cell()
	cell2.region = +ring1
	cell2.fill = mod

	
	# Make the pin universes
	fpin = openmc.Universe(1)
	fpin.add_cells((cell0, cell1, cell2))
	
	puremodcell = openmc.Cell()
	puremodcell.fill = mod
	
	mpin = openmc.Universe(2)
	mpin.add_cell(puremodcell)


	
	lat = [[mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, fpin, fpin, fpin, mpin, mpin, mpin],
           [mpin, mpin, fpin, fpin, fpin, fpin, fpin, mpin, mpin],
           [mpin, mpin, fpin, fpin, mpin, fpin, fpin, mpin, mpin],
           [mpin, mpin, fpin, fpin, fpin, fpin, fpin, mpin, mpin],
           [mpin, mpin, mpin, fpin, fpin, fpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin]]
	
	
	lattice = openmc.RectLattice(32)
	lattice.universes = lat
	lattice.pitch = (pitch, pitch)
	lattice.lower_left = [-pitch * float(len(lat)) / 2.0] * 2
	
	# remove next line after error is found
	lattice.outer = fpin

	return lattice


def create_5x5_as_lattice(as1, apitch, mod_mat):
	
	
	modcell = openmc.Cell()
	modcell.fill = mod_mat
	mmm = openmc.Universe()
	mmm.add_cell(modcell)
	
	cmap = [[mmm, as1, as1, as1, mmm],
			[mmm, as1, as1, as1, as1],
			[as1, as1, as1, as1, as1],
			[mmm, as1, as1, as1, as1],
			[mmm, mmm, as1, mmm, mmm]]
	
	
	lat5 = openmc.RectLattice(35)
	lat5.universes = cmap
	lat5.pitch = (apitch, apitch)
	lat5.lower_left = [-apitch * 5 / 2.0] * 2
	lat5.outer = mmm
	
	return lat5



def plot_everything(pitch, n, width=750, height=750):
	# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'materials-xy'
	plot.origin = [0, 0, 0]
	plot.width = [n*pitch - .01, n*pitch - .01]
	plot.pixels = [width, height]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()
	
	
	
	
	
if __name__ == "__main__":
	mats = create_openmc_materials()
	(mod, fuel, clad) = mats
	# Assembly params
	pitch = 2.0; n = 9
	core = Simplified_Vera_Core(ppitch = pitch, npins = n)
	baf = Baffle(gap = 0.19, mat = clad, thick = 2.85)
	core.baffle = baf
	asmbly_lat = create_9x9_lattice(mats, pitch)
	asmbly_cell = openmc.Cell(fill=asmbly_lat)
	asmbly_uni = openmc.Universe(cells = ((asmbly_cell,)))
	
	core_lat = create_5x5_as_lattice(asmbly_uni, core.pitch, mod)
	
	
	edges = set_cubic_boundaries(core.pitch, 10)
	(min_x, max_x, min_y, max_y, min_z, max_z) = edges
	box = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	#baffle_verse = test_baffle(core.get_openmc_baffle(core), baf.mat, asmbly_lat, edges)
	baffle_verse = test_baffle(core.get_openmc_baffle(core), baf.mat, core_lat, edges)
	
	
	# Create Geometry and set root Universe
	root_cell = openmc.Cell(name='root cell')
	root_cell.region = box
	root_cell.fill = baffle_verse
	
	root_universe = openmc.Universe(universe_id=0, name='root universe')
	root_universe.add_cell(root_cell)
	geometry = openmc.Geometry()
	geometry.root_universe = root_universe
	# Export to "geometry.xml"
	geometry.export_to_xml()
	
	plot_everything(core.pitch, 8)
	set_settings(core.pitch)
	
	
	
	
	