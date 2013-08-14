""" Support for LMA data display in brawl4d.
    
    These are meant to be lightweight wrappers to coordinate data formats 
    understood by the lmatools package.

"""
import numpy as np

from lmatools.flashsort.autosort.LMAarrayFile import LMAdataFile

from stormdrain.bounds import Bounds, BoundsFilter
from stormdrain.data import NamedArrayDataset, indexed
from stormdrain.pipeline import Branchpoint, coroutine, ItemModifier
from stormdrain.support.matplotlib.artistupdaters import PanelsScatterController
from stormdrain.support.matplotlib.poly_lasso import LassoPayloadController




class LMAController(object):
    """ Manages bounds object with LMA-specific criteria. Convenience functions for loading LMA data.
    """
    def __init__(self, *args, **kwargs):
        super(LMAController, self).__init__(*args, **kwargs)
        self.bounds = Bounds(chi2=(0.0, 1.0), stations=(6, 99))
        self.default_color_bounds = Bounds(parent=self.bounds, charge=(-1,1))
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
        scatter_ctrl = PanelsScatterController(
                            panels=panels, 
                            color_field='time', 
                            default_color_bounds=self.default_color_bounds)
        scatter_outlet_broadcaster = scatter_ctrl.branchpoint
        scatter_updater = scatter_outlet_broadcaster.broadcast() 
        final_bound_filter = BoundsFilter(target=scatter_updater, bounds=panels.bounds)
        final_filterer = final_bound_filter.filter()
        cs_transformer = panels.cs.project_points(
                            target=final_filterer, 
                            x_coord='x', y_coord='y', z_coord='z', 
                            lat_coord='lat', lon_coord='lon', alt_coord='alt',
                            distance_scale_factor=1.0e-3)
        branch.targets.add(cs_transformer)
        
        # return each broadcaster so that other things can tap into results of transformation of this dataset
        return branch, scatter_ctrl
    
    @indexed
    def read_dat(self, *args, **kwargs):
        """ All args and kwargs are passed to the LMAdataFile object from lmatools"""
        lma = LMAdataFile(*args, **kwargs)
        stn = lma.stations # adds stations to lma.data as a side-effect
        d = NamedArrayDataset(lma.data)
        self.datasets.add(d)
        return d
        
    def load_dat_to_panels(self, panels, *args, **kwargs):
        """ All args and kwargs are passed to the LMAdataFile object from lmatools"""
        d = self.read_dat(*args, **kwargs)
        post_filter_brancher,  scatter_ctrl = self.pipeline_for_dataset(d, panels)
        branch_to_scatter_artists = scatter_ctrl.branchpoint
        # ask for a copy of the array from each selection operation, so that
        # it's saved and ready for any lasso operations
        
        charge_lasso = LassoChargeController(
                            target=ItemModifier(
                            target=d.update(field_names=['charge']), 
                                            item_name='charge').modify())
        branch_to_scatter_artists.targets.add(charge_lasso.cache_segment.cache_segment())
        
        return d, post_filter_brancher, scatter_ctrl, charge_lasso
        
    @indexed(index_name='hdf_row_idx')     
    def read_hdf5(self, LMAfileHDF):
        try:
            import tables
        except ImportError:
            print "couldn't import pytables"
            return None
        from hdf5_lma import HDF5Dataset
        
        # get the HDF5 table name
        LMAh5 = tables.openFile(LMAfileHDF, 'r')
        table_names = LMAh5.root.events._v_children.keys()
        table_path = '/events/' + table_names[0]
        LMAh5.close()
        d = HDF5Dataset(LMAfileHDF, table_path=table_path, mode='a')
        self.datasets.add(d)
        return d
        
    def load_hdf5_to_panels(self, panels, LMAfileHDF):
        d = self.read_hdf5(LMAfileHDF)
        post_filter_brancher, scatter_ctrl = self.pipeline_for_dataset(d, panels)
        branch_to_scatter_artists = scatter_ctrl.branchpoint
        charge_lasso = LassoChargeController(
                            target=ItemModifier(
                            target=d.update(index_name='hdf_row_idx',
                                            field_names=['charge']), 
                                            item_name='charge').modify())
        branch_to_scatter_artists.targets.add(charge_lasso.cache_segment.cache_segment())
        return d, post_filter_brancher, scatter_ctrl, charge_lasso
        


class LassoChargeController(LassoPayloadController):
    """ The "charge" attribute is one of {-1, 0, 1} to set 
        negative, unclassified, or positive charge, or None
        to do nothing.
    """
    charge = LassoPayloadController.Payload()        