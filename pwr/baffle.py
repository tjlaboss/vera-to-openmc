# Baffle
#
# Function and class for generating a PWR baffle

import openmc
import pwr.functions

class Baffle(object):
	"""Inputs:
		material:	instance of openmc.Material
		thick:	    thickness of baffle (cm)
		gap:	    thickness of gap (cm) between the outside assembly
					(including the assembly gap) and the baffle itself
		"""
	def __init__(self, material, thick, gap):
		self.material = material
		self.thick = thick
		self.gap = gap
	def __str__(self):
		return "Baffle (" + self.thick + " cm thick)"



def get_openmc_baffle(baf, cmap, apitch, openmc_surfaces, count):
	"""Create the cells and surfaces for the core baffle.
	
	Inputs:
		baf:                instance of Baffle
		cmap:               list of lists; square map of the core layout.
							 Locations without assemblies should be empty,
							 0, or otherwise False.
							 (Currently only works for square cores.)
		apitch:             float; assembly pitch (cm)
		openmc_surfaces:    list of known instances of openmc.Surface. Will be
							 modified as new surfaces are created.
		count:              instance of pwr.Counter

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
	core_size = len(cmap)
	n = core_size - 1
	
	# Useful distances
	d0 = apitch / 2.0  # dist (from center of asmbly) to edge of asmbly
	d1 = d0 + baf.gap  # dist to inside of baffle
	d2 = d1 + baf.thick  # dist to outside of baffle
	d3 = d0 - baf.gap  # dist to inside of next baffle
	width = core_size * apitch / 2.0  # dist from center of core to center of asmbly
	
	# Unite all individual regions with the Master Region
	master_region = openmc.Union()
	
	# For each row (moving vertically):
	for j in range(1, n):
		# For each column (moving horizontally):
		for i in range(1, n):
			if cmap[j][i]:
				# Positions of surfaces
				x = (i + 0.5) * apitch - width
				y = width - (j + 0.5) * apitch
				
				north = cmap[j - 1][i]
				south = cmap[j + 1][i]
				east = cmap[j][i + 1]
				west = cmap[j][i - 1]
				southeast = cmap[j + 1][i + 1]
				southwest = cmap[j + 1][i - 1]
				northeast = cmap[j - 1][i + 1]
				northwest = cmap[j - 1][i - 1]
				
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
					(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
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
					(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
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
					(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
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
					(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
						x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
					south_region = (+left & -right & +bot & -top)
					master_region.nodes.append(south_region)
		
		# Edge cases
		x = (j + 0.5) * apitch - width
		y = width - (j + 0.5) * apitch
		
		# West edge
		if cmap[j][0]:
			north = cmap[j - 1][0]
			south = cmap[j + 1][0]
			xx = -(width - 0.5 * apitch)
			x_left = xx - d2
			x_right = xx - d1
			y_bot = y - d2
			y_top = y + d2
			
			(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
				x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
			west_region = (+left & -right & +bot & -top)
			master_region.nodes.append(west_region)
			
			if not north:
				y_bot = y + d1
				x_right = xx + d3
				(right,), (bot,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
					x0s = (x_right,), y0s = (y_bot,))[0:2]
				north_region = (+left & -right & +bot & -top)
			master_region.nodes.append(north_region)
			
			if not south:
				y_bot = y - d2
				y_top = y - d1
				x_right = xx + d3
				(right,), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
					x0s = (x_right,), y0s = (y_bot, y_top))[0:2]
				south_region = (+left & -right & +bot & -top)
				master_region.nodes.append(south_region)
		
		# East edge
		if cmap[j][n]:
			north = cmap[j - 1][n]
			south = cmap[j + 1][n]
			xx = +(width - 0.5 * apitch)
			x_left = xx + d1
			x_right = xx + d2
			y_bot = y - d2
			y_top = y + d2
			(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
				x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
			east_region = (+left & -right & +bot & -top)
			master_region.nodes.append(east_region)
			
			if not north:
				y_bot = y + d1
				x_left = xx - d3
				(left,), (bot,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
					x0s = (x_left,), y0s = (y_bot,))[0:2]
				north_region = (+left & -right & +bot & -top)
			master_region.nodes.append(north_region)
			
			if not south:
				y_bot = y - d2
				y_top = y - d1
				x_left = xx - d3
				(left,), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
					x0s = (x_left,), y0s = (y_bot, y_top))[0:2]
				south_region = (+left & -right & +bot & -top)
				master_region.nodes.append(south_region)
		
		# North edge
		if cmap[0][j]:
			east = cmap[0][j + 1]
			west = cmap[0][j - 1]
			yy = +(width - 0.5 * apitch)
			x_left = x - d2
			x_right = x + d2
			y_bot = yy + d1
			y_top = yy + d2
			(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
				x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
			north_region = (+left & -right & +bot & -top)
			master_region.nodes.append(north_region)
			
			if not west:
				x_right = x - d1
				y_bot = yy - d3
				(right,), (bot,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
					x0s = (x_right,), y0s = (y_bot,))[0:2]
				west_region = (+left & -right & +bot & -top)
				master_region.nodes.append(west_region)
			
			if not east:
				x_left = x + d1
				x_right = x + d2
				y_bot = yy - d3
				(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
					x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
				east_region = (+left & -right & +bot & -top)
				master_region.nodes.append(east_region)
		
		# South edge
		if cmap[n][j]:
			east = cmap[n][j + 1]
			west = cmap[n][j - 1]
			yy = -(width - 0.5 * apitch)
			x_left = x - d2
			x_right = x + d2
			y_bot = yy - d2
			y_top = yy - d1
			(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
				x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
			south_region = (+left & -right & +bot & -top)
			master_region.nodes.append(south_region)
			
			if not west:
				x_right = x - d1
				y_top = yy + d3
				(right,), (top,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
					x0s = (x_right,), y0s = (y_top,))[0:2]
				west_region = (+left & -right & +bot & -top)
				master_region.nodes.append(west_region)
			
			if not east:
				x_left = x + d1
				x_right = x + d2
				y_top = yy + d3
				(left, right), (top,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
					x0s = (x_left, x_right), y0s = (y_top,))[0:2]
				east_region = (+left & -right & +bot & -top)
				master_region.nodes.append(east_region)
	# Done iterating.
	
	
	# Corner cases (UNTESTED)
	# Top left
	if cmap[0][0]:
		x = -(width - 0.5 * apitch)
		y = -x
		x_left = x - d2
		y_top = y + d2
		
		# West
		x_right = x - d1
		y_bot = y - d2
		(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
			x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
		west_region = (+left & -right & +bot & -top)
		master_region.nodes.append(west_region)
		
		# North
		x_right = x + d2
		y_bot = y + d1
		(right,), (bot,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
			x0s = (x_right,), y0s = (y_bot,))[0:2]
		north_region = (+left & -right & +bot & -top)
		master_region.nodes.append(north_region)
	
	# Top right
	if cmap[0][n]:
		x = +(width - 0.5 * apitch)
		y = +x
		x_right = x + d2
		y_top = y + d2
		
		# East
		x_left = x + d1
		y_bot = y - d2
		(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
			x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
		east_region = (+left & -right & +bot & -top)
		master_region.nodes.append(east_region)
		
		# North
		x_left = x - d2
		y_bot = y + d1
		(left,), (bot,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
			x0s = (x_left,), y0s = (y_bot,))[0:2]
		north_region = (+left & -right & +bot & -top)
		master_region.nodes.append(north_region)
	
	# Bottom right
	if cmap[n][n]:
		x = +(width - 0.5 * apitch)
		y = -x
		x_right = x + d2
		y_bot = y - d2
		
		# East
		x_left = x + d1
		y_top = y + d2
		(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
			x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
		east_region = (+left & -right & +bot & -top)
		master_region.nodes.append(east_region)
		
		# South
		x_left = x - d2
		y_top = y - d1
		(left,), (top,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
			x0s = (x_left,), y0s = (y_top,))[0:2]
		south_region = (+left & -right & +bot & -top)
		master_region.nodes.append(south_region)
	
	# Bottom left
	if cmap[n][0]:
		x = -(width - 0.5 * apitch)
		y = +x
		x_left = x - d2
		y_bot = y - d2
		
		# West
		x_right = x - d1
		y_top = y + d2
		(left, right), (bot, top) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
			x0s = (x_left, x_right), y0s = (y_bot, y_top))[0:2]
		west_region = (+left & -right & +bot & -top)
		master_region.nodes.append(west_region)
		
		# South
		x_right = x + d2
		y_top = y - d1
		(right,), (top,) =pwr.functions. get_xyz_planes(openmc_surfaces, count,
			x0s = (x_right,), y0s = (y_top,))[0:2]
		south_region = (+left & -right & +bot & -top)
		master_region.nodes.append(south_region)
	
	
	# Note: This seems to require the 'count.add_cell()' argument to avoid
	# overwriting existing cell numbers, sometimes.
	baffle_cell = openmc.Cell(count.add_cell(), name = "Baffle")
	baffle_cell.fill = baf.material
	baffle_cell.region = master_region
	
	return baffle_cell


if __name__ == '__main__':
	print("This is a test of the new Baffle module.")
	
	counter = pwr.Counter(0, 0, 0, 0)
	
	# The actual material is irrelevant for this test
	h1 = openmc.Material(counter.add_material())
	h1.add_nuclide("H1", 1.0)
	h1.set_density("g/cc", 1)
	
	core_baffle = Baffle(gap = 0.1, material = h1, thick = 1.0)
	smap = [[0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
			[0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
			[0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
			[0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
			[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
			[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
			[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
			[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
			[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
			[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
			[0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
			[0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
			[0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
			[0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0]]
	
	openmc_baffle = get_openmc_baffle(baf = core_baffle, cmap = smap, apitch = 17,
	                                  openmc_surfaces = [], count = counter)
	
	print(openmc_baffle)
	
	
	
	
	
	