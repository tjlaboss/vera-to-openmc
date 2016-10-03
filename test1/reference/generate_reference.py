import openmc

a = 'ao'

fuel = openmc.Material(1, "Fuel - 3.1% enriched")
fuel.add_nuclide("U-234", 6.11864E-06, a)
fuel.add_nuclide("U-235", 7.18132E-04, a)
fuel.add_nuclide("U-236", 3.29861E-06, a)
fuel.add_nuclide("U-238", 2.21546E-02, a)
fuel.add_nuclide("O-16",  4.57642E-02, a)

gap = openmc.Material(2, "Gap")
gap.add_nuclide("H-4", 2.68714E-05, a)

fuel.add_nuclide()





