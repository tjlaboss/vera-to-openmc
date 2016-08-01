# functions.py
#
# Module containing useful functions for read_xml.py and its modules


def clean(vera_list, type):
	'''Lists in VERA decks are formatted as such: 
	
		type="Array(string)" value="{U31,he,zirc4}"
	
	Usage: clean(value, str)
	Returns list'''
	
	clean_list = list(map(type, vera_list.strip('}').strip('{').split(',')))
	return clean_list
