# Convert Pincell
#
# More user-friendly program to convert individual pincell cases

from convert import *

def convert_pincell(cell):
	"""Create and run a simple pincell.
	
	This text is out of date and should not be relied upon.

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
	
	
	plot_xy_lattice(cell.pitch)
	bounds = set_cubic_boundaries(cell.pitch, ("reflective",) * 6)
	
	return cell, cell.pitch, 1, bounds, [0.0, 1.0]


def get_pincell_case():
	"""TODO: Write this
	
	For a given case file, see if it's a single pincell case.
	If not, guide the user in selecting the exact pin cell out of the VERA case.
	
	This function will be adapted to cover all 4 problems
	(pincell, lattice, assembly, and fullcore).
	
	"""
	args = sys.argv
	errstr1 = "convert_pincell accepts at most 3 arguments at this time (case_file, aname, pname).\n"
	assert len(args) <= 4, errstr1
	case_file = ""; pname = ""; aname = ""
	
	if len(args) >= 2:
		case_file = args[1]
	if not case_file:
		case_file = input("Enter the location of the VERA xml input: ")
	
	# Process the Case and determine what kind it is (pincell, lattice, assembly, or fullcore)
	case = vera_to_openmc.MC_Case(case_file)
	# Select an assembly
	if len(case.assemblies) == 1:
		assembly0 = list(case.assemblies.values())[0]
	else:
		if len(args) >= 3:
			aname = args[2]
		else:
			print("The following assemblies were found:")
			for a in case.assemblies:
				print("\t-", a)
			aname = ""

		# Manually name an assembly
		while aname not in case.assemblies:
			aname = input("Select an assembly: ")
			aname = aname.lower()
			if aname not in case.assemblies:
				print(aname, "is not available in this Case.")
		assembly0 = case.assemblies[aname]
	# Select a pin cell
	if len(assembly0.cells == 1):
		veracell0 = list(assembly0.cells.values())[0]
	else:
		if len(args) >= 4:
			pname = args[3]
		else:
			print("The following pin cells were found:")
			for p in assembly0.cells:
				print("\t-", p)
			pname = ""
		
		# Manually name a cell
		while pname not in assembly0.cells:
			pname = input("Select a pincell: ")
			pname = pname.lower()
			if pname not in assembly0.cells:
				print(pname, "is not available in this Assembly.")
		veracell0 = assembly0.cells[pname]
	
	
	return case, veracell0