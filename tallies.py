# Tallies
#
# Find the power distribution for benchmark cases

import openmc
import pwr


def get_lattice_tally(lattice, scores, tallies_file=None):
	"""Get
	
	Input:
		lattice:            instance of openmc.RectLattice to tally over
		scores:             list of strings; the reactions to tally
		tallies_file:       instance of openmc.Tallies to add to
							[Default: None]
		
	Output:
		tallies_file:       instance of openmc.
	"""
	if tallies_file is None:
		tallies_file = openmc.Tallies()
	else:
		assert isinstance(tallies_file, openmc.Tallies), \
			"tallies_file must be an instance of openmc.Tallies(), or None."
	
	mesh = openmc.Mesh()
	mesh.type = 'regular'
	mesh.dimension = lattice.shape
	mesh.lower_left = lattice.lower_left
	mesh.width = lattice.pitch
	
	mesh_filter = openmc.MeshFilter(mesh)
	mesh_tally = openmc.Tally(name="fission tally")
	mesh_tally.filters = [mesh_filter]
	mesh_tally.scores = scores
	
	tallies_file.extend([mesh_tally])
	return tallies_file


def get_assembly_tally(assembly, nzs, dzs, z0=None, tallies_file=None):
	"""Get the tallies for a pwr assembly
	
	Parameters
	----------
	:param assembly:        instance of pwr.Assembly to mesh over
	:param nzs:             list of ints; number of mesh cuts to make per layer
	:param dzs:             list of floats; thickness of mesh cuts
	:param z0:              float; where to start the Assembly meshes
							[Default: bottom of assembly.zactive]
	:param tallies_file:    instance of openmc.Tallies to add new tallies to
							[Default: None -- will create a new instance]
	
	Returns
	--------
	:return tallies_file:   instance of openmc.Tallies with the new mesh tallies
	"""
	n = len(nzs)
	assert n == len(dzs), "Mismatch between the number of z values and z cuts"
	if z0 is None:
		z0 = assembly.z_active[0]
	if tallies_file is None:
		tallies_file = openmc.Tallies()
	else:
		pass
	assert isinstance(tallies_file, openmc.Tallies), \
		"tallies_file must be an instance of openmc.Tallies(), or None."
	
	lx = -assembly.pitch*assembly.npins/2
	lowleft = (lx, lx, z0)
	meshes = pwr.meshes.MeshGroup(assembly.npins*assembly.pitch, 1, 1, lowleft)
	for i in range(n):
		nz = nzs[i]
		dz = dzs[i]
		meshes.add_mesh(nz=nz, dz=dz)
	tallies_file.extend(meshes.tallies)
	return tallies_file
