.. brawl4d documentation master file, created by
   sphinx-quickstart on Sat Nov 16 11:09:09 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to brawl4d's documentation!
===================================

Quickstart
==========

brawl4d (B4D) is meant to be used within an IPython notebook, which allows for both GUI-driven and programmatic exploration of the data.

Plots defaults to use of a map projection in kilometers centered at a specified geographic location. Anything plotted on the time axis is specified in float seconds since a reference day. So basic startup looks like this::

    %pylab
    from datetime import datetime
    from brawl4d.brawl4d import B4D_startup
    stadium = 33.591023, -101.872908
    panels = B4D_startup(basedate=datetime(2013,9,7), ctr_lat=stadium[0], ctr_lon=stadium[1])
    
The `panels` instance represents the four-dimensional linked-panels plot. It contains references to each of the matplotlib axes instances in the `panels.panels` dictionary. If you need to make a static addition to the plot, just like you would in an ordinary plotting script, this is the way to do it::

    # valid keys are 'xy', 'xz', 'zy', 'tz'
    panels.panels['xy'].text(0,0,'TTU Football Stadium')
    # zoom in on the TTU campus
    panels.panels['xy'].axis(-5, 5, -5, 5)

`panels.cs` also contains information about the coordinate system for the map projection used. Let's label another feature of interest::
    
    # These can be arrays of locations, too
    atmo_lat, atmo_lon, atmo_alt = 33.58185, -101.88097, 0.0
    X,Y,Z = panels.cs.geoProj.toECEF(atmo_lon, atmo_lat, atmo_alt)
    x,y,z = panels.cs.mapProj.fromECEF(X,Y,Z)
    panels.panels['xy'].text(x,y,'TTU Atmospheric Science')
    

brawl4d can use the underlying stormdrain framework to manage multidimensional data that remains synced across axes. To take advantage of this requires setting up a data processing pipeline that responds to changes to the plot's bounds (stored in `panels.bounds`) and handles the necessary coordinate transformations automatically.

`brawl4d.plot_demo_dataset` contains a good example.

    
Accessing data in the current view
----------------------------------


Loading LMA data
----------------

.. code-block:: python
    from brawl4d.LMA.controller import LMAController
    



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

