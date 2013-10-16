import numpy as np
from numpy.lib.recfunctions import append_fields

from stormdrain.pubsub import get_exchange
from stormdrain.bounds import Bounds, BoundsFilter
from stormdrain.data import NamedArrayDataset
from stormdrain.pipeline import Branchpoint, coroutine, ItemModifier
from stormdrain.support.matplotlib.artistupdaters import PanelsScatterController
from stormdrain.support.matplotlib.markers import filled_plus

from lmatools.NLDN import NLDNdataFile


class GroundMarkerHeightController(object):
    """ When the bounds of the current view change, it's necessary to adjust
        the height at which the ground-level markers are plotted, since they should be along
        the bottom edge of the height view (their height is actually arbitrary) in order
        to remain visible.
    """
    def __init__(self, target=None, initial_height=0.0, alt_name='alt', alt_factor=1000.0):

        self.bounds_updated_xchg = get_exchange('SD_bounds_updated')
        self.bounds_updated_xchg.attach(self)

        self.alt_factor = alt_factor
        self.alt_name = alt_name
        self.z = initial_height
        self.target=target
        
    @coroutine
    def adjust_height(self):
        while True:
            a = (yield)
            # print "height adjust got {0}".format(a)
            a[self.alt_name] = self.z
            if self.target is not None:
                # print "send after height adjust"
                self.target.send(a)

    def send(self, bounds):
        # SD_bounds_updated sent here.
        b_z = bounds.z
        # print "new alt bounds = {0}".format(b_z)
        dz = b_z[1] - b_z[0]
        self.z = self.alt_factor*(b_z[0] + 0.05*dz)
        


class TimedGroundMarkerController(object):    
    def pipeline_for_dataset(self, d, panels, marker='s'):
        # Set up dataset -> time-height bound filter -> brancher
        branch = Branchpoint([])
        brancher = branch.broadcast()
        
        # strictly speaking, z in the map projection and MSL alt aren't the same - z is somewhat distorted by the projection.
        # therefore, add some padding. filtered again later after projection.
            
        
        # quality_filter = BoundsFilter(target=brancher, bounds=self.bounds).filter()
        
        transform_mapping = {'z':('alt', (lambda v: (v[0]*1.0e3 - 1.0e3, v[1]*1.0e3 + 1.0e3)) ) }
        # make the target in the line below quality_filter to add additional data-dependent
        # filtering.
        bound_filter = BoundsFilter(target=brancher, bounds=panels.bounds, 
                                    restrict_to=('time'), transform_mapping=transform_mapping)
        filterer = bound_filter.filter()
        # Adjust the height in response to bounds changes, so that the markers stay near
        # the bottom axis in a time-height view
        height_control = GroundMarkerHeightController(target=filterer, alt_name='alt')
        height_adjuster = height_control.adjust_height()
        d.target = height_adjuster
        
        # Set up brancher -> coordinate transform -> final_filter -> mutli-axis scatter updater
        scatter_ctrl = PanelsScatterController(
                            panels=panels, s=64,
                            color_field='time', marker=marker)
                            #default_color_bounds=self.default_color_bounds)
        
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
    
class NLDNController(TimedGroundMarkerController):
    """ Support for loading NLDN data into brawl4d. 
    
        Example
        -------
        from brawl4d.NLDN import NLDNController
        nldn = NLDNController()
        npos, nneg = nldn.load_NLDN_to_panels(panels, '/data/20120604/20120604-20120605-NLDN.asc')

        # Bonus code to print out NLDN points in the current view
        from stormdrain.pipeline import coroutine
        @coroutine
        def print_CG():
            while True:
                a=(yield)
                print "NLDN points: {0}".format(a)
        CGprinter = print_CG()
    
        neg_ctrl = nneg[-1]
        neg_branchpoint = neg_ctrl.branchpoint    
        neg_branchpoint.targets.add(CGprinter)    
    """
        
    def load_NLDN_to_panels(self, panels, *args, **kwargs):
        """ All args and kwargs are passed to the NLDNdataFile object from lmatools
            peak_current is assumed to be the name of the polarity field. This
            should eventually be made a kwarg.
        """
    
        nldn = NLDNdataFile(*args, **kwargs)
    
        # correct for panels basedate. Copy the array so that the data in the 
        # nldn object is still consistent with nldn.basedate. Make the copy
        # by appending a height field, which will be adjusted by the pipeline
        # in response to bounds changes so that the CG markers are always at the ground
        data = append_fields(nldn.data, 'alt', np.zeros(nldn.data.shape))
        data['time'] += (nldn.basedate-panels.basedate).total_seconds()
    
        d_pos = NamedArrayDataset(data[data['peak_current'] >= 0.0])
        d_neg = NamedArrayDataset(data[data['peak_current'] <= 0.0])
    
        pos_mark = filled_plus(0.4)
        neg_mark = '^'
    
        post_filter_brancher_pos,  scatter_ctrl_pos = self.pipeline_for_dataset(d_pos, panels, marker=pos_mark)
        post_filter_brancher_neg,  scatter_ctrl_neg = self.pipeline_for_dataset(d_neg, panels, marker=neg_mark)
    
        return ((d_pos, post_filter_brancher_pos, scatter_ctrl_pos), 
                (d_neg, post_filter_brancher_neg, scatter_ctrl_neg))
    