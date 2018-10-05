""" Why brawl4d? It's inherited from an old IDL-based 3D viewer that was designed to plot
    Balloons, Radar, and Aircraft with Lightning = BRAWL.

"""
import datetime
import numpy as np

from stormdrain.bounds import BoundsFilter
from stormdrain.data import NamedArrayDataset
from stormdrain.pipeline import Branchpoint

from stormdrain.pubsub import get_exchange
from stormdrain.support.matplotlib.linked import LinkedPanels
from stormdrain.support.matplotlib.mplevents import MPLaxesManager
from stormdrain.support.matplotlib.artistupdaters import PanelsScatterController, FigureUpdater
from stormdrain.support.matplotlib.formatters import SecDayFormatter
from stormdrain.support.coords.filters import CoordinateSystemController

from stormdrain.support.matplotlib.poly_lasso import PolyLasso


def redraw(panels):
    """ this function forces a manual redraw / re-flow of the data to the plot.
    
    """
    get_exchange('SD_bounds_updated').send(panels.bounds)
    get_exchange('SD_reflow_start').send('Manual redraw')
    get_exchange('SD_reflow_done').send('Manual redraw complete')


class PanelLasso(object):
    def __init__(self, panels):
        self.panels = panels
        


class Panels4D(LinkedPanels):
    # 1.618
    # 89,55,34,21,13,8,5,3,2,1,1,0

    x0 = .025 # shift all panels to right by this amount to leave space for the left axis label
    dx = .89*0.55
    dz = .89*0.21
    mg = .89*0.05 # margin
    dy = dx
    dt = dx+dz 
    w = mg+dt+mg
    h = mg+dy+dz+mg+dz+mg
    aspect = h/w # = 1.30

    # Left, bottom, width, height
    margin_defaults = {
        'xy':(mg*aspect+x0, mg, dx*aspect, dy),
        'xz':(mg*aspect+x0, mg+dy, dx*aspect, dz),
        'zy':((mg+dx)*aspect+x0, mg, dz*aspect, dy),
        'tz':(mg*aspect+x0, mg+dy+dz+mg, dt*aspect, dz),
        }

    def __init__(self, *args, **kwargs):
        self.names_4D = kwargs.pop('names_4D', ('lon', 'lat', 'alt', 'time'))
        self.figure = kwargs.pop('figure', None)
        self.basedate = kwargs.pop('basedate', None)
        if self.basedate is None:
            self.basedate = datetime.datetime(1970,1,1,0,0,0)

        ctr_lat, ctr_lon, ctr_alt = kwargs.pop('ctr_lat', 33.5), kwargs.pop('ctr_lon', -101.5), kwargs.pop('ctr_alt', 0.0)
        self.cs = CoordinateSystemController(ctr_lat, ctr_lon, ctr_alt)
        
        if self.figure is not None:
            fig = self.figure
            self.panels = {}
            self.panels['xy'] = fig.add_axes(Panels4D.margin_defaults['xy'])
            self.panels['xz'] = fig.add_axes(Panels4D.margin_defaults['xz'], sharex=self.panels['xy'])
            self.panels['zy'] = fig.add_axes(Panels4D.margin_defaults['zy'], sharey=self.panels['xy'])
            self.panels['tz'] = fig.add_axes(Panels4D.margin_defaults['tz'], sharey=self.panels['xz'])
            
            self.panels['xy'].set_xlabel('East distance (km)')
            self.panels['xy'].set_ylabel('North distance (km)')
            self.panels['xz'].set_ylabel('Altitude (km)')
            self.panels['zy'].set_xlabel('Altitude (km)')
            self.panels['tz'].set_xlabel('Time (UTC)')
            self.panels['tz'].set_ylabel('Altitude (km)')
                        
            ax_specs = { self.panels['xy']: (self.names_4D[0], self.names_4D[1]), 
                         self.panels['xz']: (self.names_4D[0], self.names_4D[2]),
                         self.panels['zy']: (self.names_4D[2], self.names_4D[1]),
                         self.panels['tz']: (self.names_4D[3], self.names_4D[2]), }
            kwargs['ax_specs'] = ax_specs
            
            self.panels['tz'].xaxis.set_major_formatter(SecDayFormatter(self.basedate, self.panels['tz'].xaxis))
            
        super(Panels4D, self).__init__(*args, **kwargs)
        
        # The built-in is a good idea. But zooming on a wide, short area in x,y causes the
        # data to subset but the axes to remain zoomed out. There is some sort of
        # problematic interaciton with the interaction-complete notification.
        # self.panels['xy'].set_aspect('equal')
        self.equal_ax.add(self.panels['xy'])

        # Note this won't work in <1.2.x: https://github.com/matplotlib/matplotlib/pull/1585/
        resize_id = self.figure.canvas.mpl_connect('resize_event', self._figure_resized)
    
    def _figure_resized(self, event):
        # Force a reflow of data by notifying the xy axis manager, which needs to
        # be kept square, that something happened to the figure. In this case,
        # no change to limits, but the axes aspect changed.
        # Might want to make this a generic exchange-based event at some point.
        
        # To force a certain aspect ratio on the figure, might also use
        # figure.canvas.resize(w,h)
        
        ax_name = self.ax_specs[self.panels['xy']]
        ax_mgr  = self.axes_managers[ax_name]
        self.send(ax_mgr)
    
    def _lasso_callback(self, ax, lasso_line, verts):
        self.figure.canvas.widgetlock.release(self._active_lasso)
        self._active_lasso=None
        xchg = get_exchange('B4D_panel_lasso_drawn')
        xchg.send((self, ax, lasso_line, verts))


    def lasso(self):
        """ Attach to B4D_panel_lasso_drawn exchange to get the panels, axes, 
            MPL line artist, and verts for each lasso drawn
        """        
        lock = self.figure.canvas.widgetlock
        if lock.locked()==False:
            self._active_lasso = PolyLasso(self.figure, self._lasso_callback)
            lock(self._active_lasso)
        else:
            print "Please deselect other tools to use the lasso."

    

def get_demo_dataset(): 
    data = np.asarray( [ ('The Most Toxic \nTown in America', 36.983, -94.833,  250. , 1.34 ),
                        ('Dublin, TX',                       32.087, -98.343,  446. , 5.25 ),
                        ('Floating Mesa',                    35.277, -102.049, 1064., 1.90 ),
                        ('Lubbock',                          33.582, -101.881, 984. , 5.37 ),
                        ('Stonehenge Replica',               31.892, -102.326, 886. , 7.01 ),
                        ('Very Large Array',                 34.079, -107.618, 2126., 4.23 ),
                       ],  
                       dtype = [ ('name', '|S32'), ('lat', '>f4'), ('lon', '>f4'), 
                                 ('alt', '>f4'), ('time', '>f4') ]  )
    # Create a dataset that stores numpy named array data, and automatically receives updates 
    # when the bounds of a plot changes.
    d = NamedArrayDataset(data)
    
    
    return d
   
    
def plot_demo_dataset(d, panels):
    # Create a scatterplot representation of the dataset, and add the necessary transforms
    # to get the data to the plot. In this case, it's a simple filter on the plot bounds, and 
    # distribution to all the scatter artists. Might also add map projection here if the plot
    # were not directly showing lat, lon, alt.
    
    # Set up dataset -> time-height bound filter -> brancher
    branch = Branchpoint([])
    brancher = branch.broadcast()
    
    # strictly speaking, z in the map projection and MSL alt aren't the same - z is somewhat distorted by the projection.
    # therefore, add some padding. filtered again later after projection.
    transform_mapping = {'z':('alt', (lambda v: (v[0]*1.0e3 - 1.0e3, v[1]*1.0e3 + 1.0e3)) ) }
    bound_filter = BoundsFilter(target=brancher, bounds=panels.bounds, restrict_to=('time'), transform_mapping=transform_mapping)
    filterer = bound_filter.filter()
    d.target = filterer
    
    # Set up brancher -> coordinate transform -> final_filter -> mutli-axis scatter updater
    scatter_ctrl = PanelsScatterController(panels=panels, color_field='time')
    scatter_outlet_broadcaster = scatter_ctrl.branchpoint
    scatter_updater = scatter_outlet_broadcaster.broadcast() 
    final_bound_filter = BoundsFilter(target=scatter_updater, bounds=panels.bounds)
    final_filterer = final_bound_filter.filter()
    cs_transformer = panels.cs.project_points(target=final_filterer, x_coord='x', y_coord='y', z_coord='z', 
                        lat_coord='lat', lon_coord='lon', alt_coord='alt', distance_scale_factor=1.0e-3)
    branch.targets.add(cs_transformer)
    
    # return each broadcaster so that other things can tap into results of transformation of this dataset
    return branch, scatter_outlet_broadcaster
    

def B4D_startup(show=False, basedate=None, ctr_lat=33.5, ctr_lon=-101.5, figsize=(8.5, 11.0), dpi=80):
    import matplotlib
    fontspec = {'family':'Helvetica', 'weight':'bold', 'size':10}
    matplotlib.rc('font', **fontspec)
    
    import matplotlib.pyplot as plt
                        
    panel_fig = plt.figure(figsize=figsize, dpi=dpi)
    panels = Panels4D(figure=panel_fig, names_4D=('x', 'y', 'z', 'time'), basedate=basedate, ctr_lat=ctr_lat, ctr_lon=ctr_lon)
    fig_updater = FigureUpdater(panel_fig)
    
    panels.panels['xy'].axis((-1000, 1000, -1000, 1000))
    panels.panels['tz'].axis((0, 10, 0, 5))
    
    if show is True:
        plt.show()
        
    return panels
    
if __name__ == '__main__':
    B4D_startup(show=True)
    panels = B4D_startup()
    d = get_demo_dataset()
    post_filter_brancher, post_transform_branch_to_scatter_artists = plot_demo_dataset(d, panels)