""" There are four kinds of plots, depending on typical scan mode.

    PPI from PPI mode
    RHI from RHI mode
    pseduo-RHI from PPI mode
    pseduo-PPI from RHI mode
    
    Could we delegate plotting to pyart? That seems like a good idea.
    
    We might want multiple views of the same radar dataset
    with a single view controller that pushes data to the relevant artists
    
    Each of the classes below therefore stores the view state (abstractly)
    and builds and maintains the necessary pipelines to combine the view
    state with the data in the *radar* object to transform the data toward 
    target plots.
    - PIPE: radar -> assemble orderly sweep array -> az,el,ran bounds filter -> 
                transform to panels xyz -> branch to each plot type
    
    PPIViewController
        - bounds for range, azimuth. 
        - elevation property that stores a target az plus sets actual azimuth bounds
            and has logic to determine the slice to use
        - pcolor in plan view 
        - ghosted polgon for radar cone in xz, zy and valid times on t axis.
            - get cones by taking x,y,z gate data, stripping coord not needed
                and 
        - time polygon could get respond to click to hide/show pcolor.
    
    RHIViewController
        - bounds for range, elevation. 
        - azimuth property that stores a target az plus sets actual azimuth bounds
            and has logic to determine what slice to use.
        - panels plan view slice locator
        - new figure with RHI data
    
    Probably could make these subclasses of the non-pseudo classes.
    PseudoPPIViewController
    PseudoRHIViewController
    
    The RadarController class itself could do other coordination tasks
    like manage updates to a real-time radar object that is then set as the
    radar attribute of other views managed by the controller.
    

    
"""


class RadarController(object):
    """ Manage loading radar datasets and creation of displays. """
    def __init__(self):
        self.datasets = set()
        
    
    def _pyart_read(self, filename, **kwargs):
        try:
            import pyart
            return pyart.io.read(filename, **kwargs)
        except ImportError:
            print "Can't read radar: pyart not installed"
            return None
            
    def radar_to_panels(self, radar, panels, **kwargs):
        if radar not in self.datasets:
            self.datasets.add(radar)
        
    
    def read(self, filename, **kwargs):
        """ By default, delegate radar support to pyart.
        """
        radar = self._pyart_read(filename, **kwargs)
        if radar is not None:
            self.datasets.add(radar)
        return radar
        
    
        


