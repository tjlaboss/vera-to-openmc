# Postprocess
#
# Visualize some data

import openmc
from matplotlib import pyplot
from numpy import *

STATEPOINT = "test1/statepoint.0100.h5"


def process_fission_rate_tally(state, tally_name = "fission tally", lat_shape = (17, 17),
	                           case_name = ""):
	"""Write and view the fission rate tally
	
	Input:
		state:      instance of openmc.StatePoint
	"""
	
	# Get the
	#tally = state.get_tally(name = tally_name)
	tally = state.get_tally(id = 1)
	tal_vals = tally.get_values(scores = ["fission"])
	fission_rates = tal_vals[:, 0, 0]
	
	# Clean up the data a bit
	fission_rates[fission_rates == 0] = nan
	fission_rates.shape = lat_shape
	fission_rates /= nanmean(fission_rates)
	savetxt("fission_rates.dat", fission_rates)
	
	# Plot
	fig = pyplot.figure()
	hotplot = pyplot.imshow(fission_rates.squeeze(), interpolation = 'none', cmap = 'jet')
	print(nanmax(fission_rates), nanmin(fission_rates))
	pyplot.clim(nanmax(fission_rates), nanmin(fission_rates))
	pyplot.title(case_name + " Fission Rates")
	pyplot.colorbar(hotplot)
	return None


#def assembly_fission_rate_tally(state, tally_name = "fission tally"):
#	return None

def axial_power_tally(state):
	#print(state.tallies)
	
	# Get these from some external source
	nzs = [1, 7, 1, 6, 1, 6, 1, 6, 1, 6, 1, 6, 1, 5]
	dzs = [3.866, 8.2111429, 3.81, 8.065, 3.81, 8.065, 3.81, 8.065, 3.81, 8.065, 3.81, 8.065, 3.81, 7.9212]
	z0 = 11.951
	z = z0
	zlist = zeros(sum(nzs))
	xlist = zeros(sum(nzs))
	
	n = len(nzs)
	k = 0
	for i in range(n):
		nz = nzs[i]
		dz = dzs[i]
		talvalsi = state.get_tally(id = i+1).get_values()
		talvalsi.shape = (nz, 1)
		for j in range(nz):
			z += dz
			zlist[k] = z
			xlist[k] = talvalsi[j]/dz
			k += 1
	
	xlist /= xlist.mean()
	return xlist, zlist


def axial_plot(xlista, zlista, xlistb, zlistb):
	pyplot.figure()
	pyplot.plot(xlista, zlista, "bD-", label = "Case 3A Axial")
	pyplot.plot(xlistb, zlistb, "r.-", label = "Case 3B Axial")
	pyplot.grid()
	pyplot.xticks(linspace(0, 1.75, 8))
	pyplot.yticks(linspace(0, 400, 9))
	pyplot.xlabel("Relative power")
	pyplot.ylabel("z (cm)")
	pyplot.xlim(0, 1.75)
	pyplot.ylim(0, 400)
	pyplot.legend()
	