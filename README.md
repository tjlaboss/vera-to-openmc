# vera-to-openmc
Read VERAin's xml.gold files and export them in the XML format of OpenMC.

Requires:

https://github.com/tjlaboss/pwr - Toolbox to simplify PWR modeling with the Python API of OpenMC
https://github.com/CASL/VERAin  - VERA common input processor (produces xml from VERA decks)
-----

Contains the files:


#### `vera_to_openmc.py`:
Under active development. Module which performs the operations necessary to generate an OpenMC input. Contains the class `MC_Case` (child of `Case`), which has the attributes and methods required to create the OpenMC objects.

Currently converts Problems 1 (pincell), 2 (lattice), and 3 (assembly).

#### `read_xml.py`:
Completed. Describes the class `Case`, which should contain all of the information present in the XML of a VERA case.

#### `objects.py`:
Module containing useful classes for `read_xml.py`

#### `functions.py`:
Module containing useful functions for `read_xml.py`


------

#### `gold/`
Directory containing the xml.gold files for VERA benchmark problems.

------

#### `test1/tests.py`
Directory/file containing temporary test cases. These will be removed once a standard wrapper is written.

#### `Results/*`
Directory containing the results of said tests.
