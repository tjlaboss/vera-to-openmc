# Meshes
#
# Module for tally meshes

import openmc
import math


class Mesh_Group(object):
	"""Container for multiple uniform meshes to cover a 3D assembly.
	Must have the same (x, y) pitch, but may have multiple layers
	with different z-pitches (dz).
	
	Meshes must be stacked sequentially.
	
	Parameters:
	-----------
	pitch:          float, or tuple of (xpitch, ypitch); cm
	nx:             int; number of cuts in the x-direction
	ny:             int; number of cuts in the y-direction
	lower_left:     tuple of (x0, y0, z0); the lower left coordinate (cm)
					of all the meshes
					[Default: (0, 0, 0)]
	id0:            int; the ID number of the lowest mesh. Each additional
					mesh increases by 1.
					[Default: 1]
	"""
	
	def __init__(self, pitch, nx, ny, lower_left = (0, 0, 0), id0 = 1):
		if isinstance(pitch, (int, float)):
			self.xpitch, ypitch = pitch, pitch
		elif len(pitch) in (2, 3):
			self.xpitch, ypitch = pitch[0:2]
		else:
			raise IndexError("`pitch` must be of length 1, 2, or 3")
		self._nx = nx
		self._ny = ny
		self._meshes = []
		self._mesh_filters = []
		self._mesh_edges = None
		self.x0, self.y0, self.z0 = lower_left
		self._z = self.z0
		self._id0 = id0
	
	@property
	def meshes(self):
		return self._meshes
	
	@property
	def id0(self):
		return self._id0
	
	@property
	def nx(self):
		return self._nx
	
	@property
	def ny(self):
		return self._ny
	
	@property
	# Unused?
	def mesh_edges(self):
		return self._mesh_edges
	
	@property
	def mesh_filters(self):
		return self._mesh_filters
	
	
	def add_mesh(self, z1 = None, nz = None, dz = None):
		"""Add a mesh to the group. You must supply two of the
		three parameters. If all three are supplied,
		`dz` will be ignored.
		
		Parameters:
		-----------
			z1:         float (cm); top of this mesh
			dz:         float (cm); height of a mesh cut
			nz:         int; number of mesh cuts
		"""
		# z1 may be 0
		if z1 is not None:
			assert z1 > self._z, "z1 must be larger than " + str(self._z)
			ztrue = True
		else:
			ztrue = False
		if nz and ztrue:
			dz = (z1 - self._z)/nz
		elif nz and dz:
			z1 = self._z + nz*dz
		elif dz and ztrue:
			nz = int(round(nz))
			if not math.isclose(nz, z1/dz):
				# Then there's no way to slice this up right
				delta_z = z1 - self._z
				errstr = "Cannot cut {delta_z} cm into slices of {dz} cm.".format(**locals())
				raise IndexError(errstr)
			
		new_mesh = openmc.Mesh(self.id0)
		new_mesh.type = "regular"
		new_mesh.lower_left = (self.x0, self.y0, self._z)
		new_mesh.width = (self._nx, self._ny, nz)
		new_filter = openmc.MeshFilter(new_mesh)
		
		self._meshes.append(new_mesh)
		self._mesh_filters.append(new_filter)
		self._id0 += 1
		self._z = z1


# Test
if __name__ == "__main__":
	test_group = Mesh_Group(1.26, 17, 17)
	test_group.add_mesh(10, 10)
	test_group.add_mesh(50, 2)
	test_group.add_mesh(100, 10)
	print(test_group.meshes)
	print(test_group.mesh_filters)


