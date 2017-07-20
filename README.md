# vera-to-openmc
Read VERAin's xml.gold files and export them in the XML format of OpenMC.

Requires:

https://github.com/tjlaboss/pwr - Toolbox to simplify PWR modeling with the Python API of OpenMC
https://github.com/CASL/VERAin  - VERA common input processor (produces xml from VERA decks)

-----

Contains the files:


#### `convert.py`:
Wrapper for `vera_to_openmc.py`.

#### `vera_to_openmc.py`:
Module which performs the operations necessary to generate an OpenMC input. Contains the class `MC_Case` (child of `Case`), which has the attributes and methods required to create the OpenMC objects.

Currently converts the neutronics portions of all the progression problems except for critical boron searches.

#### `read_xml.py`:
Describes the class `Case`, which should contain all of the information present in the XML of a VERA case.

#### `objects.py`:
Module containing useful classes for `read_xml.py`

#### `functions.py`:
Module containing useful functions for `read_xml.py`

#### `tallies.py`:
Module containing functions to find the power distribution for some of the benchmark cases. 
This is an area of ongoing development.

------

Contains the directories:

#### `gold/`
Directory containing the xml.gold files for VERA benchmark problems.

#### `Plots/`
Directory containing plots of selected benchmark problems.

