# Test 
#
# Learning how to read XML with Python modules
# This is my first time working with XML in Python. Bear with me.

import xml.etree.ElementTree as ET


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
				if child.attrib["name"].upper() in self.ignore:
					print "Ignoring block", child.attrib["name"]
				elif child.attrib["name"].upper() in self.usable:
					# Then handle them appropriately
					print "Todo: write this block of code"
				
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




# Instantiate a case with a simple VERA XML.gold
case2a = Case("2a_dep.xml.gold")
print "Testing:",  case2a
# 'root' should be the master ParameterList
print "Let's see what 'root' has:"
print "root.tag:\t", case2a.root.tag
print "root.attrib:\t", case2a.root.attrib
print "root.attrib[\"name\"]\t", case2a.root.attrib["name"]

name = "Placeholder name"
print "\nInspecting the children"
for child in case2a.root:
	# Expect to see the case_id, which is the name of this deck
	if False:
		print "You broke the universe."
	elif child.tag == "ParameterList":
		print child.attrib["name"]
		


# useful stuff later on
''''
'mat_fracs.strip('}').strip('{').split(',')  # extracts material fractions from the provided string array
'''



