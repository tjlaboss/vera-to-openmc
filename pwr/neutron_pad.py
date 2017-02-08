# Neutron Pad
#
# Class and functions for PWR neutron pads

import openmc
import math


# Simple functions for the necessary angles/coefficients
def phi(th, radians = True):
	"""Angle on the XY plane at which the normal vector to a plane will be
	
	Inputs:
		:param th:          float; angle (degrees) of the plane itself on the XY plane
		:param radians:     Boolean; whether to return the answer in radians. If false,
							the answer will be returned in degrees.
							[Default: True]
	Output:
		:return angle:      float; angle (in radians, or degrees if radians == False)
	"""
	angle = th * math.pi/180 - math.pi/2
	if radians:
		return angle
	else:
		return angle * 180 / math.pi


def a(th):
	"""Coefficient 'A' for a plane equation

		Inputs:
			:param th:          float; angle (degrees) of the plane itself on the XY plane
		Output:
			:return A:          float
		"""
	return math.sin(phi(th))
	
	
def b(th):
	"""Coefficient 'B' for a plane equation

		Inputs:
			:param th:          float; angle (degrees) of the plane itself on the XY plane
		Output:
			:return B:          float
		"""
	B = math.cos(phi(th))
	return B


class Neutron_Pads(object):
	"""Neutron pads as found in the reactor vessel of a PWR.
	
	Inputs:
		:param region:      instance of openmc.Intersection defining the region in which the
							neutron pads will exist. This should be an intersection of two
							ZCylinders (inner and outer radius). If 3D, the region should also
							intersect with two ZPlanes (bottom and top).
		:param pad_mat:     instance of openmc.Material that the neutron pad is made of
		:param mod_mat:     instance of openmc.Material that the space between the
							neutron pads is filled with (usually moderator)
		:param npads:       int; number of pads: one per steam generator (evenly placed)
							[Default: 4]
		:param arc_length:  float (degrees); arc length of a single neutron pad
		                    [Default: 32]
		:param angle:       float (degrees); angle from the x-axis at which the first pad starts
							[Default: 45]
		:param counter:     instance of pwr.Counter for surface and cell numbers.
							[optional--if not supplied, auto surface/cell ids will be assigned]
	
	Other parameters:
		:param material:    pad_mat; instance of openmc.Material
		:param mod:         mod_mat; instance of openmc.Material
		:param cells:       list of instances of openmc.Cell making up the neutron pad
							layer of the reactor vessel.
							[Empty until Neutron_Pads.get_cells() is executed.]
		:param planes:      list of instances of openmc.Plane created during the generation
		                    of the neutron pad
		                    [Empty until Neutron_Pads.get_cells() is executed.]
        :param generated:   Boolean; whether or not get_cells() has been executed yet.
	"""
	def __init__(self, region, pad_mat, mod_mat,
                npads = 4, arc_length = 32, angle = 45, counter = None):
		assert arc_length * npads <= 360, "The combined arclength must be less than 360 degrees."
		self.region = region
		self.material = pad_mat
		self.mod = mod_mat
		self.npads = npads
		self.arc_length = arc_length
		self.angle = angle
		self.counter = counter
		
		self.cells = []
		self.planes = []
		self.generated = False
	
	def __str__(self):
		rep = "Neutron pads:"
		rep += "\n\t" + str(self.npads) + " pads"
		rep += "\n\tArc length: " + str(self.arc_length) + " degrees"
		rep += "\n\tStarting angle: " + str(self.angle) + " degrees"
		if self.generated:
			rep += "\n\tThese neutron pads have been generated."
		else:
			rep += "\n\tThe neutron pads have NOT been generated."
		return rep
	
	def get_cells(self):
		"""Get the cells and planes necessary for modeling these neutron pads in openmc.
		If the required cells and surfaces exist, return them. If not, instantiate them.
		
		Output:
			:return cells:    list of the instances of openmc.Cell making up the pads
		"""
		if not self.generated:
			theta = 360 / self.npads
			p2 = None   # Placeholder for the last surface used
			for i in range(self.npads):
				name = "Neutron pad " + str(i + 1)
				th0 = self.angle + i * theta - self.arc_length / 2.0
				th1 = th0 + self.arc_length
				# Define the surfaces bounding the i^th pad
				if self.counter:
					if p2:
						p0 = p2
					else:
						p0 = openmc.Plane(self.counter.add_surface(), A = a(th0), B = b(th0))
						self.planes.append(p0)
					p1 = openmc.Plane(self.counter.add_surface(), A = a(th1), B = b(th1))
				else:
					if p2:
						p0 = p2
					else:
						p0 = openmc.Plane(A = a(th0), B = b(th0))
						self.planes.append(p0)
					p1 = openmc.Plane(A = a(th1), B = b(th1))
				self.planes.append(p1)
				
				# Create the cell for the i^th pad itself
				if self.counter:
					new_pad = openmc.Cell(self.counter.add_cell(), name)
				else:
					new_pad = openmc.Cell(name = name)
				new_pad.region = self.region & +p1 & -p0
				new_pad.fill = self.material
				self.cells.append(new_pad)
				# Create the cell between this and the next pad
				th2 = th0 + theta
				if self.counter:
					p2 = openmc.Plane(self.counter.add_surface(), A = a(th2), B = b(th2))
					new_space = openmc.Cell(self.counter.add_cell())
				else:
					p2 = openmc.Plane(A = a(th2), B = b(th2))
					new_space = openmc.Cell()
				new_space.region = self.region & +p2 & -p1
				new_space.fill = self.mod
				self.cells.append(new_space)
			# And we're done
			self.generated = True
		
		return self.cells

