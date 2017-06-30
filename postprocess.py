# Postprocess
#
# Visualize some data

import openmc
from matplotlib import pyplot
from numpy import *

STATEPOINT = "test1/statepoint.0110.h5"
sp = openmc.StatePoint(STATEPOINT)


def process_fission_rate_tally(state, tally_name = "fission tally", lat_shape = (17, 17),
                               case_name = ""):
	"""Write and view the fission rate tally
	
	Input:
		state:      instance of openmc.StatePoint
	"""
	
	# Get the
	tally = state.get_tally(name = tally_name)
	tal_vals = tally.get_values(scores = ["fission"])
	fission_rates = tal_vals[:, 0, 0]
	
	# Clean up the data a bit
	fission_rates[fission_rates == 0] = nan
	fission_rates.shape = lat_shape
	fission_rates /= nanmean(fission_rates)
	savetxt("fission_rates.dat", fission_rates)
	
	# Plot
	fig = pyplot.figure()
	pyplot.imshow(fission_rates.squeeze(), interpolation = 'none', cmap = 'jet')
	pyplot.title(case_name + " Fission Rates")
	pyplot.colorbar()
	return None


process_fission_rate_tally(sp)
pyplot.show()
