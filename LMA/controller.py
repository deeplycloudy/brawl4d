""" Support for LMA data display in brawl4d.
    
    These are meant to be lightweight wrappers to coordinate data formats 
    understood by the lmatools package.

"""

import numpy as np
from numpy.lib.recfunctions import append_fields

from lmatools.flashsort.autosort.LMAarrayFile import LMAdataFile

from stormdrain.bounds import Bounds, BoundsFilter
from stormdrain.data import NamedArrayDataset
from stormdrain.pipeline import Branchpoint
from stormdrain.support.matplotlib.artistupdaters import scatter_dataset_on_panels


from stormdrain.data import NamedArrayDataset

class LMAController(object):
    """ Manages bounds object with LMA-specific criteria. Convenience functions for loading LMA data.
    """
    def __init__(self, *args, **kwargs):
        super(LMAController, self).__init__()
        self.bounds = Bounds(chi2=(0.0, 1.0),
                             stations=(6, 99)
                             )
        self.datasets = set()
    
    
    
    def pipeline_for_dataset(self, d, panels):
        # Set up dataset -> time-height bound filter -> brancher
        branch = Branchpoint([])
        brancher = branch.broadcast()

        # strictly speaking, z in the map projection and MSL alt aren't the same - z is somewhat distorted by the projection.
        # therefore, add some padding. filtered again later after projection.
        
        quality_filter = BoundsFilter(target=brancher, bounds=self.bounds).filter()
        
        transform_mapping = {'z':('alt', (lambda v: (v[0]*1.0e3 - 1.0e3, v[1]*1.0e3 + 1.0e3)) ) }
        bound_filter = BoundsFilter(target=quality_filter, bounds=panels.bounds, restrict_to=('time'), transform_mapping=transform_mapping)
        filterer = bound_filter.filter()
        d.target = filterer

        # Set up brancher -> coordinate transform -> final_filter -> mutli-axis scatter updater
        scatter_outlet_broadcaster = scatter_dataset_on_panels(panels=panels, color_field='time')
        scatter_updater = scatter_outlet_broadcaster.broadcast() 
        final_bound_filter = BoundsFilter(target=scatter_updater, bounds=panels.bounds)
        final_filterer = final_bound_filter.filter()   
        cs_transformer = panels.cs.project_points(target=final_filterer, x_coord='x', y_coord='y', z_coord='z', 
                            lat_coord='lat', lon_coord='lon', alt_coord='alt', distance_scale_factor=1.0e-3)
        branch.targets.add(cs_transformer)

        # return each broadcaster so that other things can tap into results of transformation of this dataset
        return branch, scatter_outlet_broadcaster
        
    
    
    def load_dat(self, *args, **kwargs):
        """ All args and kwargs are passed to the LMAdataFile object from lmatools"""
        lma = LMAdataFile(*args, **kwargs)
        # this adds stations to lma.data
        stn = lma.stations
        # a = append_fields(lma.data, 'stations', stn, usemask=False)
        d = NamedArrayDataset(lma.data)
        self.datasets.add(d)
        return d
        
        
    def load_hdf5(self):
        # this one will be harder: file itself needs to be a proxy dataset.
        # registers to receive event updates when charge ID is done
        pass