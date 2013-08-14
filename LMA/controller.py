""" Support for LMA data display in brawl4d.
    
    These are meant to be lightweight wrappers to coordinate data formats 
    understood by the lmatools package.

"""
import numpy as np

from lmatools.flashsort.autosort.LMAarrayFile import LMAdataFile

from stormdrain.bounds import Bounds, BoundsFilter
from stormdrain.data import NamedArrayDataset, indexed
from stormdrain.pipeline import Branchpoint, coroutine, ItemModifier
from stormdrain.support.matplotlib.artistupdaters import scatter_dataset_on_panels
from stormdrain.support.matplotlib.poly_lasso import LassoPayloadController




class LMAController(object):
    """ Manages bounds object with LMA-specific criteria. Convenience functions for loading LMA data.
    """
    def __init__(self, *args, **kwargs):
        super(LMAController, self).__init__(*args, **kwargs)
        self.bounds = Bounds(chi2=(0.0, 1.0), stations=(6, 99))
        self.datasets = set()
    
    def pipeline_for_dataset(self, d, panels):
        # Set up dataset -> time-height bound filter -> brancher
        branch = Branchpoint([])
        brancher = branch.broadcast()

        # strictly speaking, z in the map projection and MSL alt aren't the same - z is somewhat distorted by the projection.
        # therefore, add some padding. filtered again later after projection.
        
        quality_filter = BoundsFilter(target=brancher, bounds=self.bounds).filter()
        
        transform_mapping = {'z':('alt', (lambda v: (v[0]*1.0e3 - 1.0e3, v[1]*1.0e3 + 1.0e3)) ) }
        bound_filter = BoundsFilter(target=quality_filter, bounds=panels.bounds, 
                                    restrict_to=('time'), transform_mapping=transform_mapping)
        filterer = bound_filter.filter()
        d.target = filterer

        # Set up brancher -> coordinate transform -> final_filter -> mutli-axis scatter updater
        scatter_outlet_broadcaster = scatter_dataset_on_panels(panels=panels, color_field='time')
        scatter_updater = scatter_outlet_broadcaster.broadcast() 
        final_bound_filter = BoundsFilter(target=scatter_updater, bounds=panels.bounds)
        final_filterer = final_bound_filter.filter()
        cs_transformer = panels.cs.project_points(
                            target=final_filterer, 
                            x_coord='x', y_coord='y', z_coord='z', 
                            lat_coord='lat', lon_coord='lon', alt_coord='alt',
                            distance_scale_factor=1.0e-3)
        branch.targets.add(cs_transformer)

        # ask for a copy of the array from each selection operation, so that
        # it's saved and ready for any lasso operations
        
        charge_lasso = LassoChargeController(
                            target=ItemModifier(
                            target=d.update(field_names=['charge']), 
                                            item_name='charge').modify())
        scatter_outlet_broadcaster.targets.add(charge_lasso.cache_segment.cache_segment())

        # return each broadcaster so that other things can tap into results of transformation of this dataset
        return branch, scatter_outlet_broadcaster, charge_lasso
    
    @indexed
    def load_dat(self, *args, **kwargs):
        """ All args and kwargs are passed to the LMAdataFile object from lmatools"""
        lma = LMAdataFile(*args, **kwargs)
        stn = lma.stations # adds stations to lma.data as a side-effect
        d = NamedArrayDataset(lma.data)
        self.datasets.add(d)
        return d
        
    @indexed    
    def load_hdf5(self, LMAfileHDF):
        import tables
        # this could be made more interestin: file itself as a proxy dataset.
        # registers to receive event updates when charge ID is done
        
        # get the HDF5 table name
        LMAh5 = tables.openFile(LMAfileHDF, 'r')
        table_names = LMAh5.root.events._v_children.keys()
        table_path = '/events/' + table_names[0]
        events = LMAh5.getNode(table_path)
        d = NamedArrayDataset(events[:])
        LMAh5.close()
        return d
        



class LassoChargeController(LassoPayloadController):
    """ The "charge" attribute is one of {-1, 0, 1} to set 
        negative, unclassified, or positive charge, or None
        to do nothing.
    """
    charge = LassoPayloadController.Payload()        