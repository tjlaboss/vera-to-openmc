# Convert Pincell
#
#TODO: Write description

import sys
import vera_to_openmc
from convert_common import *

def convert_pincell(case, aname = "", pname = ""):
	"""Create and run a simple pincell.

	True pincell cases (those starting with a '1') only have 1 assembly consisting of 1 pin cell.
	In that case, just take the first (and only) entry in case.assemblies and assembly.cells.

	This function may also be used to run individual pin cells that are parts of larger cases.
	In this event, the user must specify the assembly name 'aname' in which the pincell lies,
	and the pincell name 'pname' referring to the cell itself.

	Inputs:
		case_file:		string of the location on the filesystem of the XML.GOLD input
		aname:			string; unique key of the Assembly in which the cell lies.
		pname:			string; unique key of the Cell in the Assembly
	"""
	assembly1 = list(case.assemblies.values())[0]
	veracell1 = list(assembly1.cells.values())[0]
	
	if aname and pname:
		try:
			assembly1 = case.assemblies[aname.lower()]
			veracell1 = assembly1.cells[pname.lower()]
		except KeyError as e:
			print("Key", e, "not found; autodetecting.")
			print("Using Assembly:", assembly1.name, "and Cell:", veracell1.name)
	
	openmc_cell1 = case.get_openmc_pincell(veracell1)
	
	plot_xy_lattice(assembly1.pitch)
	bounds = set_cubic_boundaries(assembly1.pitch, ("reflective",) * 6)
	
	return case, openmc_cell1, assembly1.pitch, 1, bounds, [0.0, 1.0]


def get_pincell_case():
	"""TODO: Write this
	
	For a given case file, see if it's a single pincell case.
	If not, guide the user in selecting the exact pin cell out of the VERA case.
	
	"""
	
	case_file = None
	aname = None
	pname = None
	return case_file, aname, pname