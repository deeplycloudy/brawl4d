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

class LMAAnimator(object):
    
    
    def __init__(self, duration, variable='time'):
        self.tstart = time.time()
        self.duration = duration
        
    def draw_frame(self, animator, time_fraction):
        pass
        
    
    def init_draw(self, animator):
        pass


class LMAController(object):
    """ Manages bounds object with LMA-specific criteria. Convenience functions for loading LMA data.
    """
    
    z_alt_mapping = {'z':('alt', (lambda v: (v[0]*1.0e3 - 1.0e3, v[1]*1.0e3 + 1.0e3)) ) }
    
    def __init__(self, *args, **kwargs):
        super(LMAController, self).__init__(*args, **kwargs)
        self.bounds = Bounds(chi2=(0.0, 1.0), stations=(6, 99))
        self.default_color_bounds = Bounds(parent=self.bounds, charge=(-1,1))
        self.datasets = set()
        self.flash_datasets = set()
    
    def pipeline_for_dataset(self, d, panels, 
                             names4d=('lon', 'lat', 'alt', 'time'),
                             transform_mapping=None,
                             scatter_kwargs = {}
                             ):
        """ Set 4d_names to the spatial coordinate names in d that provide 
            longitude, latitude, altitude, and time. Default of 
            lon, lat, alt, and time which are assumed to be in deg, deg, meters, seconds
        
            entries in the scatter_kwargs dictionary are passed as kwargs to the matplotlib
            scatter call.
        """
        # Set up dataset -> time-height bound filter -> brancher
        branch = Branchpoint([])
        brancher = branch.broadcast()
        
        # strictly speaking, z in the map projection and MSL alt aren't the same - z is somewhat distorted by the projection.
        # therefore, add some padding. filtered again later after projection.
        
        quality_filter = BoundsFilter(target=brancher, bounds=self.bounds).filter()
        if transform_mapping is None:
            transform_mapping = self.z_alt_mapping
        # Use 'time', which is the name in panels.bounds, and not names4d[3], which should
        # is linked to 'time' by transform_mapping if necessary
        bound_filter = BoundsFilter(target=quality_filter, bounds=panels.bounds, 
                                    restrict_to=('time'), transform_mapping=transform_mapping)
        filterer = bound_filter.filter()
        d.target = filterer
        
        # Set up brancher -> coordinate transform -> final_filter -> mutli-axis scatter updater
        scatter_ctrl = PanelsScatterController(
                            panels=panels, 
                            color_field=names4d[3], 
                            default_color_bounds=self.default_color_bounds,
                            **scatter_kwargs)
        scatter_outlet_broadcaster = scatter_ctrl.branchpoint
        scatter_updater = scatter_outlet_broadcaster.broadcast() 
        final_bound_filter = BoundsFilter(target=scatter_updater, bounds=panels.bounds)
        final_filterer = final_bound_filter.filter()
        cs_transformer = panels.cs.project_points(
                            target=final_filterer, 
                            x_coord='x', y_coord='y', z_coord='z', 
                            lat_coord=names4d[1], lon_coord=names4d[0], alt_coord=names4d[2],
                            distance_scale_factor=1.0e-3)
        branch.targets.add(cs_transformer)
        
        # return each broadcaster so that other things can tap into results of transformation of this dataset
        return branch, scatter_ctrl
    
    @coroutine
    def flash_stat_printer(self, min_points=10):
        while True:
            ev, fl = (yield)
            template = "{0} of {1} flashes have > {3} points. Their average area = {2:5.1f} km^2"
            N = len(fl)
            good = (fl['n_points'] >= min_points)
            N_good = len(fl[good])
            area = np.mean(fl['area'][good])
            print template.format(N_good, N, area, min_points)
        
    def flash_stats_for_dataset(self, d, selection_broadcaster):
        
        flash_stat_branchpoint = Branchpoint([self.flash_stat_printer()])
        flash_stat_brancher = flash_stat_branchpoint.broadcast()
        
        @coroutine
        def flash_data_for_selection(target, flash_id_key = 'flash_id'):
            """ Accepts an array of event data from the pipeline, and sends 
                event and flash data.
            """
            while True:
                ev = (yield) # array of event data
                fl_dat = d.flash_data
                
                flash_ids = set(ev[flash_id_key])
                flashes = np.fromiter(
                            (fl for fl in fl_dat if fl[flash_id_key] in flash_ids), 
                            dtype=fl_dat.dtype)
                target.send((ev, flashes))
                
        selection_broadcaster.targets.add(flash_data_for_selection(flash_stat_brancher))
        return flash_stat_branchpoint
        
        
        
        
    @indexed()
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
        
        if d.flash_table is not None:
            print "found flash data"
        
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
        
    def load_hdf5_flashes_to_panels(self, panels, hdf5dataset):
        """ Set up a flash dataset display. The sole argument is usually the HDF5 
            LMA dataset returned by a call to self.load_hdf5_to_panels """
        from hdf5_lma import HDF5FlashDataset
        if hdf5dataset.flash_table is not None:
            flash_d = HDF5FlashDataset(hdf5dataset)
            transform_mapping = {}
            transform_mapping['time'] = ('start', (lambda v: (v[0], v[1])) )
            transform_mapping['lat'] = ('init_lat', (lambda v: (v[0], v[1])) )
            transform_mapping['lon'] = ('init_lon', (lambda v: (v[0], v[1])) )
            transform_mapping['z'] = ('init_alt',  (lambda v: (v[0]*1.0e3 - 1.0e3, v[1]*1.0e3 + 1.0e3)) )
            flash_post_filter_brancher, flash_scatter_ctrl = self.pipeline_for_dataset(flash_d, panels, 
                    transform_mapping=transform_mapping, 
                    names4d=('init_lon', 'init_lat', 'init_alt', 'start') )
            for art in flash_scatter_ctrl.artist_outlet_controllers:
                # there is no time variable, but the artist updater is set to expect
                # time. Patch that up.
                if art.coords == ('time', 'z'):
                    art.coords = ('start', 'z')
                # Draw flash markers in a different style
                art.artist.set_edgecolor('k')
        self.flash_datasets.add(flash_d)
        return flash_d, flash_post_filter_brancher, flash_scatter_ctrl

class LassoChargeController(LassoPayloadController):
    """ The "charge" attribute is one of {-1, 0, 1} to set 
        negative, unclassified, or positive charge, or None
        to do nothing.
    """
    charge = LassoPayloadController.Payload()        