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

------

#### `gold*`
Directory containing the xml.gold files of three main types:

#### `1[n].xml.gold`
Examle input for the XML generated by VERAin for a single reflected pin cell.

#### `2[n].xml.gold`
Example inputs for VERA assemblies. `2o.xml.gold` contains gadolinia.

#### `p[n].xml.gold`:
Full-core example inputs.

------

#### `pwr*`
Directory containing the following:

#### `__init__.py`
Initializer for proposed openmc.pwr module

#### `assembly.py`:
Under active development. Module to generate a complete OpenMC fuel assembly geometry.

------

#### `test*`
Directories containing the following tests:
##### - `tests.py`
Very simple test suite for a pin cell, assembly, and full core
##### - `test_core.py`
Test for a full-core problem, such as p7
##### - `test_pwr_assembly.py`
Test for the module `PWR_assembly.py`
