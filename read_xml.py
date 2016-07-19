# Test 
#
# Learning how to read XML with Python modules
# This is my first time working with XML in Python. Bear with me.

import xml.etree.ElementTree as ET
from docutils.utils.math.latex2mathml import mfrac


'''The VERAin XML files have the following structure:

<ParameterList>
	<Parameter name="" ... />
	<ParameterList>
		<Parameter name="" ... />
	</ParameterList>
	...
</ParameterList>

One big ParameterList of ParameterLists containing Parameters and ParameterLists (themselves containing other Parameters and ParameterLists)
The goal here is to extract all of the information needed to construct OpenCG or OpenMC objects. Haven't figured that out yet.
'''

class Case(object):
	'''Each VERA input deck represents a unique case.
	This is a class of such a case.'''
	
	def __init__(self, source_file):
		'''Initialize with a few key values from the XML'''
		
		# Location in the filesystem of the VERA XML.gold
		self.source_file = source_file
		
		# Read the XML file from disk
		self.tree = ET.parse(self.source_file)
		self.root = self.tree.getroot()
		
		# Initialize the case_id in case we can't find it in the XML
		self.case_id = "Unnamed VERA Case"
		
		# Blocks to use and ignore
		# TODO: Verify that these lists are 100% correct.
		self.usable = ("CORE", "INSERT", "STATES", "CONTROL", "DETECTOR", "ASSEMBLIES") # Relevant to OpenMC
		self.ignore = ("SHIFT", "MPACT", "INSILICO")			# Blocks specific to other codes 
		
		# Initialize some parameters with empty lists
		self.materials = {}
		self.states = []
		# and more to come... 
		
		
		# Get and categorize a few important params
		# All entries should be either "Parameter" or "ParameterList"
		for child in self.root:
			if child.tag == "Parameter":
				# Get the name of the case
				if child.attrib["name"] == "case_id":
					self.case_id = child.attrib["value"]
				# case_id is the only parameter I expect to see at this level
				# If there are more, they'll go here. Notify the user.
				else:
					print "child.tag is", child.tag + "; name is",  child.attrib["name"]
					print "The script does not know how to handle this; ignoring.\n"
			
			elif child.tag == "ParameterList":
				# Proper use of recursion could probably save me a lot of effort here.
				name = child.attrib["name"].upper()	# for brevity
				if name in self.ignore:
					print "Ignoring block", name
				elif name in self.usable:
					# Then handle them appropriately
					if name == "CORE":
						'''The [CORE] block describes the nuclear reactor core configuration. This block describes the core
						layout, including the placement of nuclear fuel assemblies, control rods, detectors, inserts, and
						other core parameters that do not change during a cycle depletion.
						The geometric objects inside the core are defined in separate input blocks; the [CORE] block
						simply describes how all of these objects are placed together.'''
						# The CORE block will contain the deck's global materials
						# and some other stuff
						for core_child in child:
							cname = core_child.attrib["name"].lower()	# for brevity
							if core_child.tag == "ParameterList" and cname == "materials":
								# Create a material object for each listed material
								for mat in core_child:
									
									# Initialize the 4 material properties
									mname = ""; mdense = 0.0; mfracs = []; miso_names = []
										
									for property in mat:
										p = property.attrib["name"]
										v = property.attrib["value"]
										if p == "key_name":
											mname = v
										elif p == "density":
											mdens = float(v)
										elif p == "mat_fracs":
											# Convert a string to a list of floating point numbers
											mfracs = map(float, v.strip('}').strip('{').split(','))
										elif p == "mat_names":
											# Convert a string to a list of strings
											miso_names = v.strip('}').strip('{').split(',')
										else:
											print "Warning: unused property", p
									
									# Check if isotopic fractions each have an associated element
									if len(mfracs) != len(miso_names):
										warning = "Unequal number of isotopes and associated fractions in material", mname
										raise IndexError(warning)
									
									# Instantiate a new material and add it to the dictionary
									a_material = Material(mname, mdens, mfracs, miso_names)
									self.materials[mname] = a_material
																
							elif core_child.tag == "ParameterList":
								print "Unknown parameter list: " + cname + ". Ignoring."
								
							elif core_child.tag == "Parameter":
								# TODO: This is where the program gets boundary conditions and various other core properties.
								# Things to watch for: apitch, assm_map, bc_bot, bc_rad, bc_top, core_size, height,
								# 	rated_flow, rated_power, and shape
								continue
								
									
							else:
								print "Entry", core_child.tag, "is neither a Parameter nor ParameterList. Ignoring."
						
					elif name == "ASSEMBLIES":
						'''Cell cards are used to describe pin cells. A pin cell is defined as a configuration of concentric
						cylinders (or rings) centered in a square region of coolant. Cell configurations can be used to
						model fuel rods or guide tubes. Parameters include cell ID, a list of radii for each ring
						in the cell, and a list of materials that compose each ring.'''
						# TODO: Get cells, materials, and all that stuff from the Assemblies block
						# TODO: Check for duplicate materials. (Probably at the end of __init__)
					elif name == "STATES":
						do_states_stuff = True
					elif name == "CONTROL":
						do_controlt_stuff = True
					elif name == "DETECTOR":
						do_detector_stuff = True
					elif name == "INSERT":
						do_insert_stuff = True
					
					# tmp
					else:
						print name
				
				else:
					print "Unexpected block encountered:\t", child.attrib["name"]
					print "This may be a flaw within the XML file, or a shortcoming of this script."
					print "Ignoring for now."
			
			else:
				print "child.tag =", child.tag, "-- Ignoring."
				print "Expected either Parameter or ParameterList. There is probably something wrong with the XMl."
		 
		# note; end of the for loop
		
	def __str__(self):
		'''Return the name of the VERA input case if I try to print this object'''
		return self.case_id

	def describe(self):
		'''Print out some useful information about this object.'''
		print "\ncase_id:", self.case_id
		

		if self.materials:
			print "Materials:"
			for mat in self.materials.values():
				print ' - ', str(mat)
		else:
			print "No materials found."

		if self.states:
			print "States:"
			for stat in self.states:
				print stat
		else:
			print "No states found."



class Material(object):
	'''Basics of a material card'''
	def __init__(self, key_name, density, mat_fracs, mat_names):
		self.key_name = key_name
		self.density = density
		self.mat_fracs = mat_fracs
		self.mat_names = mat_names

	def __str__(self):
		'''Use this to print a brief description of each material'''
		description = self.key_name + '\t@ ' + str(self.density) + ' g/cc\t(' + str(len(self.mat_names)) + ' isotopes)'
		return description



# Instantiate a case with a simple VERA XML.gold
case2a = Case("2a_dep.xml.gold")
print "Testing:",  case2a
'''
# 'root' should be the master ParameterList
print "Let's see what 'root' has:"
print "root.tag:\t", case2a.root.tag
print "root.attrib:\t", case2a.root.attrib
print "root.attrib[\"name\"]\t", case2a.root.attrib["name"]
'''

print "\nInspecting the children"
for child in case2a.root:
	# Expect to see the case_id, which is the name of this deck
	if False:
		print "You broke the universe."
	elif child.tag == "ParameterList":
		print child.attrib["name"]
		

#case2a.describe()



# useful stuff later on
''''
'mat_fracs.strip('}').strip('{').split(',')  # extracts material fractions from the provided string array
'''



