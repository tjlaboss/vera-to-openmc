# vera_xml
Read VERAin's xml.gold files and export them in the XML format of OpenMC and/or OpenCG.

Contains the files:

#### `read_xml.py`:
Still under development. Describes the class `Case`, which should contain all of the information present in the XML of a VERA case.

#### `vera_to_openmc.py`:
Under active development. Module which performs the operations necessary to generate an OpenMC input. Contains the class `MC_Case` (child of `Case`), which has the attributes and methods required to create the OpenMC objects.

#### `vera_to_opencg.py`:
Currently shelved. Equivalent to `vera_to_openmc.py`, but for OpenCG geometries. OpenMC's Python API already has a function to convert to OpenCG geometries, so this module may be unnecessary.

#### `objects.py`:
Module containing useful classes for `read_xml.py`

#### `functions.py`:
Module containing useful functions for `read_xml.py`

#### `isotopes.py`:
Module containing some essential isotopic data for `read_xml.py`

#### `2a_dep.xml.gold` and `p7.xml.gold`:
Two example inputs (one simple and one complex, respectively) for the XML generated by VERAin. Nothing special about these two cases in particular.
