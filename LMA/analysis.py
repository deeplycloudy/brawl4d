"""
Get a plot of the flash energy spectrum for flashes in the current brawl4d view.
lma_ctrl is an instance of brawl4d.LMA.controller.LMAController that 

>>> from brawl4d.brawl4d import B4D_startup
>>> from datetime import datetime
>>> panels = B4D_startup(basedate=datetime(2012,5,29), ctr_lat=35.2791257, ctr_lon=-97.9178678)
>>> from brawl4d.LMA.controller import LMAController
>>> lma_file = '/data/20120529/flash_sort_prelim/h5_files/2012/May/29/LYLOUT_120529_233000_0600.dat.flash.h5'
>>> lma_ctrl = LMAController()
>>> d, post_filter_brancher, scatter_ctrl, charge_lasso = lma_ctrl.load_hdf5_to_panels(panels, lma_file)
>>> current_events_flashes = lma_ctrl.flash_stats_for_dataset(d, scatter_ctrl.branchpoint)
>>> energy_spectrum_plotter = FlashEnergySpectrumController(bounds_provider=panels)
>>> current_events_flashes.targets.add(energy_spectrum_plotter.inlet)

"""
import numpy as np
from stormdrain.pipeline import coroutine
from stormdrain.support.matplotlib.artistupdaters import LineArtistUpdater
from lmatools.flash_stats import events_flashes_receiver, histogram_for_parameter, energy_plot_setup, calculate_energy_from_area_histogram

        
class FlashEnergySpectrumController(object):
    def __init__(self, coord_names=('length_scale', 'energy'), bin_unit='km', bounds_provider=None):
        """ The inlet attribute of this object is a running coroutine ready to receive (events,flashes).
            bounds_provider should have a bounds attribute that provides a time coordinate 'time' in seconds
        """

        min_pwr = -2
        max_pwr = 4
        delta_pwr = 0.1
        powers = np.arange(min_pwr, max_pwr+delta_pwr, delta_pwr)
        footprint_bin_edges = 10**powers

        self.coord_names=coord_names
        self.bounds_provider = bounds_provider
        
        fig, spectrum_ax, fivethirds_line_artist, spectrum_artist = energy_plot_setup()
        self.spectrum_ax=spectrum_ax
        self.spectrum_plot_outlet = LineArtistUpdater(spectrum_artist, coord_names=self.coord_names).update()
        self.histogrammer = histogram_for_parameter('area', footprint_bin_edges, target=self.calculate_energy(target=self.spectrum_plot_outlet))
        self.inlet = events_flashes_receiver(target=self.histogrammer)        
        
    @coroutine
    def calculate_energy(self, target=None, length_scale_factor=1000.0, t_coord='time'):
        """ Presumes the histogram is of area, and that area is in km^2 (as indicated by length_scale_factor) """
        xname, yname = self.coord_names
        dtype = [(xname,'f4'), (yname,'f4')]
        while True:
            t_range = self.bounds_provider.bounds[t_coord]
            duration = t_range[1] - t_range[0]
            histo, bin_edges = (yield)
            
            flash_1d_extent, specific_energy = calculate_energy_from_area_histogram(histo, bin_edges, duration)
            
            if target is not None:
                # package energy spectrum as a named array
                a = np.empty_like(flash_1d_extent, dtype=dtype)
                a[xname]=flash_1d_extent
                a[yname]=specific_energy
                target.send(a)
                self.spectrum_ax.figure.canvas.draw()
                #ax.loglog(flash_1d_extent, specific_energy, 'r')
                



