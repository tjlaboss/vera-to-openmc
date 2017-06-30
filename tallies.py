# Tallies
#
# Find the power distribution for benchmark cases

import openmc
import vera_to_openmc
from copy import deepcopy


def get_lattice_mesh(lattice, scores = ("fission"), tallies_file = None):
	"""Get
	
	Input:
		lattice:            instance of openmc.RectLattice to tally over
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
	mesh_tally = openmc.Tally()
	mesh_tally.filters = [mesh_filter]
	mesh_tally.scores = scores
	
	tallies_file.extend(mesh_tally)
	return tallies_file
