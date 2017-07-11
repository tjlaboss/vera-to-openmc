# Meshes
#
# Module for tally meshes

import openmc
import numpy as np

_len_err_str = "The length of `nzs` must match the length of `dzs`."


class MeshError(Exception):
	""" Class for errors involving mesh structure. """
	pass


class Mesh_Group(object):
	"""Container for multiple uniform meshes to cover a 3D assembly.
	Must have the same (x, y) pitch, but may have multiple layers
	with different z-pitches (dz).
	
	Meshes must be stacked sequentially.
	
	Note that "Another Mesh instance" and "Another Tally instance"
	warnings are expected for each level if you are using this
	class for post-processing a StatePoint.
	
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
	
	def __init__(self, pitch, nx, ny, lower_left = (0.0, 0.0, 0.0), id0 = 1):
		if isinstance(pitch, (int, float)):
			self._dx, self._dy = pitch, pitch
		elif len(pitch) in (2, 3):
			self._dx, self._dy = pitch[0:2]
		else:
			raise IndexError("`pitch` must be of length 1, 2, or 3")
		self._nx = nx
		self._ny = ny
		self._meshes = []
		self._mesh_filters = []
		self._tallies = []
		self.x0, self.y0, self.z0 = lower_left
		self._z = self.z0
		self._id0 = id0
		self._next_id = id0
		self._nzs = None
		self._dzs = None
	
	@property
	def meshes(self):
		return self._meshes
	
	@property
	def tallies(self):
		return self._tallies
	
	@property
	def id0(self):
		return self._id0
	
	@property
	def height(self):
		return self._z
	
	@property
	def nx(self):
		return self._nx
	
	@property
	def ny(self):
		return self._ny
	
	@property
	def nzs(self):
		return self._nzs
	
	@property
	def dzs(self):
		return self._dzs
	
	@property
	def n(self):
		if (self._dzs is not None) and (self._nzs is not None):
			return len(self._nzs)
		else:
			return 0
	
	@property
	def mesh_filters(self):
		return self._mesh_filters
	
	@nzs.setter
	def nzs(self, nzs_in):
		if self._dzs is not None:
			if len(nzs_in) != len(self._dzs):
				raise IndexError(_len_err_str)
		self._nzs = nzs_in
	
	@dzs.setter
	def dzs(self, dzs_in):
		if self._nzs.any():
			if len(dzs_in) != len(self._nzs):
				raise IndexError(_len_err_str)
		self._dzs = dzs_in
	
	def _get_next_id(self):
		nid = self._next_id
		self._next_id += 1
		return nid
	
	def __assert_nzs_dzs(self):
		assert self._nzs.any(), "Mesh_group.nzs has not been set. Cannot get profile."
		assert self._dzs.any(), "Mesh_group.dzs has not been set. Cannot get profile."
	
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
			nz = int(round(z1/dz))
			if not np.isclose(nz, z1/dz):
				# Then there's no way to slice this up right
				delta_z = z1 - self._z
				errstr = "Cannot cut {delta_z} cm into slices of {dz} cm.".format(**locals())
				raise MeshError(errstr)
		
		new_id = self._get_next_id()
		new_mesh = openmc.Mesh(new_id)
		new_mesh.type = "regular"
		new_mesh.lower_left = (self.x0, self.y0, self._z)
		new_mesh.dimension = (self._nx, self._ny, nz)
		new_mesh.width = (self._dx, self._dy, dz)
		
		new_filter = openmc.MeshFilter(new_mesh, new_id)
		new_tally = openmc.Tally(new_id)
		new_tally.filters = [new_filter]
		new_tally.scores = ["fission"]
		
		self._meshes.append(new_mesh)
		self._mesh_filters.append(new_filter)
		self._tallies.append(new_tally)
		self._z = z1
	
	def build_group(self):
		"""Use the `nzs` and `dzs` attributes to autobuild the mesh group"""
		self.__assert_nzs_dzs()
		for i in range(self.n):
			self.add_mesh(nz = self._nzs[i], dz = self._dzs[i])
	
	# Post-processing methods
	def get_axial_power(self, state, eps = 0):
		"""Get the axial power profile, suitable for plotting
		
		Parameters:
		-----------
		state:      openmc.StatePoint with this Mesh_Group's tally results
		eps:        tolerance for a tally to be considered 0 or NaN
					[Default: 0]
		
		Returns:
		--------
		xlist:      array of x-values (power), normalized to 1
		zlist:      array of z-values (height), in cm
		"""
		self.__assert_nzs_dzs()
		zlist = np.zeros(sum(self.nzs))
		xlist = np.zeros(sum(self.nzs))
		z = 0
		k = 0
		for i in range(self.n):
			nz = self._nzs[i]
			dz = self._dzs[i]
			talvalsi = state.get_tally(id = i + 1).get_values()
			talvalsi.shape = (self._nx, self._ny, nz)
			for j in range(nz):
				z += dz
				zlist[k] = z
				xlist[k] = talvalsi[:, :, j].sum()/dz
				k += 1
		
		xlist[xlist <= eps] = np.NaN
		xlist /= np.nanmean(xlist)
		return xlist, zlist
	
	
	def get_radial_power_by_tally(self, state, tally_id, index = None):
		"""Get the radial power of a specific tally with a known ID
		
		Parameters:
		-----------
		state:          openmc.StatePoint with this Mesh_Group's tally results
		tally_id:       int; id of the desired openmc.Tally
		index:          int; index of the z-layer within the Tally's mesh.
						If the index is None, the sum of all the Tally's
						layers will be returned.
						[Default: None]
		
		Returns:
		--------
		xyarray:        numpy.array of the radial power profile
		"""
		tally = state.tallies[tally_id]
		talvals = tally.get_values()
		nz = len(talvals)//(self._nx*self._ny)
		talvals.shape = (self._nx, self._ny, nz)
		if index:
			xyarray = talvals[:, :, index]
		else:
			xyarray = np.zeros((self._nx, self._ny))
			for i in range(nz):
				xyarray += talvals[:, :, i]
		return xyarray
		
	
	def get_tally_id_by_index(self, index):
		"""Given the index of a mesh cut in the group, find the Tally
		that occurs at that index. If the mesh cut is between two tallies,
		this method will return the lower one.
		
		Parameters:
		-----------
		index:      int; index of the mesh cut
		
		Returns:
		--------
		id:         int; id of openmc.Tally covering that index
		"""
		total = 0
		for i, j in enumerate(self._nzs):
			total += j
			if total >= index:
				tally = self.tallies[i]
				return tally.id
		
	def get_index_by_z(self, zval):
		"""Given a z-value within the group, find the index
		of the mesh cut at or above it.
		
		Parameters:
		-----------
		zval:       float; z-value (cm) of the desired mesh cut
		
		Returns:
		--------
		i:          int; index in the total group at, or
					immediately above, zval
		"""
		self.__assert_nzs_dzs()
		errstr = "The requested z-value is above the maximum: {} cm".format(self._z)
		assert zval <= self._z, errstr
		z = self.z0
		for i in range(self.n):
			nz = self._nzs[i]
			dz = self._dzs[i]
			for j in range(nz):
				z += dz
				if z >= zval:
					return i
			
	
	def get_radial_power(self, state, zval = None, tally_id = None,
	                     index = None, tally_total = False, eps = 0):
		"""Get the radial power profile
		
		You must specify `zval`, `index`, or `tally_total`.
		
		Parameters
		----------
		state:          openmc.StatePoint with this Mesh_Group's tally results
		zval:           float; z-value (cm) to find the closest layer's relative power
						If it is exactly on a cut, the lower level will be returned.
						[Default: None]
		tally_id:       int; the id of the openmc.Tally to index into
						[Default: None]
		index:          int; the index of the layer within the Tally's Mesh
						If `tally_id` is None, the index will refer to the layer
						within the entire group.
						[Default: None]
		tally_total:    Boolean; whether to sum the entire Tally instead of
						select a layer. If `tally_id` is None, all Tally instances
						in the group will be summed.
		eps:            tolerance for a tally to be considered 0 or NaN
						[Default: 0]
		
		Returns:
		--------
		xyarray:        numpy.array containing the
		"""
		self.__assert_nzs_dzs()
		if (zval is not None) and (index is None):
			index = self.get_index_by_z(zval)
		
		max_i = sum(self._nzs)
		errstr = "Index {} out of {} does not exist".format(index, max_i)
		assert index <= max_i, errstr
		
		if tally_id:
			if (index is None) and (not tally_total):
				errstr = "An index is required for tally {}\
				 unless the total is desired".format(tally_id)
				raise MeshError(errstr)
			else:
				xyarray = self.get_radial_power_by_tally(state, tally_id, index)
		else:
			if (zval is None) and (index is None):
				if tally_total:
					# The entire profile is requested!
					for i in range(self.n):
						xyarray = np.zeros((self._nx, self._ny))
						xyarray += self.get_radial_power_by_tally(state, tally_id = self.id0 + i)
				else:
					errstr = "You have not specified a z-value, index, \
					or tally id to find the power at."
					raise MeshError(errstr)
			else:
				tid = self.get_tally_id_by_index(index)
				tally = state.tallies[tid]
				for i in range(self.n):
					if sum(self.nzs[:i+1]) >= index:
						break
				if i:
					tally_index = index - sum(self.nzs[:i+1])
				else:
					tally_index = index
				talvals = tally.get_values()
				nz = len(talvals)//(self._nx*self._ny)
				talvals.shape = (self._nx, self._ny, nz)
				xyarray = talvals[:, :, tally_index]
		
		# Replace things below the tolerance with NaNs before normalizing
		xyarray[xyarray <= eps] = np.NaN
		xyarray /= np.nanmean(xyarray)
		return xyarray


def get_mesh_group_from_lattice(lattice, z0 = None):
	"""Populate a Mesh_Group() instance with a lattice's
	size, pitch, and lower left.
	
	Parameters:
	-----------
	lattice:        instance of openmc.RectLattice to use as a base
	z0:             float; z-height (cm) to use as the start of the
					mesh group, if different the lattice's lower_left
					[Default: None]
	
	Returns:
	--------
	new_group:      instance of Mesh_Group
	"""
	p = lattice.pitch
	nx = lattice.shape[0]
	ny = lattice.shape[1]
	if z0 is None:
		ll = deepcopy(lattice.lower_left)
	else:
		ll = (lattice.lower_left[0], lattice.lower_left[1], z0)
	new_group = Mesh_Group(p, nx, ny, ll)
	return new_group


# Test
if __name__ == "__main__":
	
	test_group = Mesh_Group(1.26, 17, 17, lower_left = (-17/1.26, -17/1.26, 11.951))
	test_group.nzs = [1, 7, 1, 6, 1, 6, 1, 6, 1, 6, 1, 6, 1, 5]
	test_group.dzs = [3.866, 8.2111429, 3.81, 8.065, 3.81, 8.065, 3.81, 8.065, 3.81, 8.065, 3.81, 8.065, 3.81, 7.9212]
	test_group.build_group()
	print(test_group.meshes)
