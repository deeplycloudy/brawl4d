"""
This code can be used to display a stream of LiveLMA data, read using the
Websocket stream support in lmatools.

Example
-------

# In an IPython notebook, you can then run:
%pylab

server="ws://someuniversity.edu:port/path/to/stream"

import numpy as np
from datetime import datetime
today = datetime.now().date()
basedate = datetime(today.year, today.month, today.day)
print basedate

from brawl4d.brawl4d import B4D_startup
from brawl4d.LMA.controller import LMAController
from brawl4d.LMA.live import LiveLMADataset

panels = B4D_startup(basedate=basedate)
lma_ctrl = LMAController()
d = LiveLMADataset(host=server)
post_filter_brancher, post_transform_branch_to_scatter_artists = lma_ctrl.pipeline_for_dataset(d, panels)

panels.panels['tz'].axis((0, 86400, 0, 20))
lma_ctrl.bounds.stations=(6,99)
lma_ctrl.bounds.chi2=(0,1.0)

This example does not automatically update the time in the plot, but is
easily accomplished by tapping into matplotlib's timer events.

"""

from datetime import datetime
import threading
from collections import deque

import numpy as np
from numpy.lib.recfunctions import rename_fields

from stormdrain.pubsub import get_exchange
from lmatools.live.liveLMA import LiveLMAController, WebsocketClient

    

class LiveLMATimeController(object):
    def __init__(self, panels, timespan=600.0, track_realtime=True, future_margin=.1, time_name='time'):
        """ Contol the real-time display aspects of a live display
            timespan is the total duration of the time axis in seconds
            future_margin is the fraction of total width of time to be displayed
            if track_realtime is set, the view will be updated every timespan * future_margin
            """
        self.panels = panels
        self.time_name = time_name
        self.timespan = timespan
        self.future_margin = future_margin
        # Timer is in milliseconds
        scroll_interval = 1000.0*timespan*future_margin
        self.scroll_timer = panels.figure.canvas.new_timer()
        self.scroll_timer.add_callback(self.scroll_to_current)
        # interval needs to be specified last to work around some sort of bug in
        # QT's timer. https://github.com/jonathanrocher/Code-samples/blob/master/matplotlib/animation_demo.py
        self.scroll_timer.interval = scroll_interval 
        self.scroll_timer.start()
        
        self.draw_timer = panels.figure.canvas.new_timer()
        self.draw_timer.add_callback(self.draw)
        self.draw_timer.interval = 1.0*1000.0
        self.draw_timer.start()

        self.track_realtime = track_realtime
        if self.track_realtime:
            self.scroll_to_current()

    def draw(self):
        self.panels.figure.canvas.draw()
    
    def scroll_to_current(self):
        if self.track_realtime:
            t_now = (datetime.utcnow() - self.panels.basedate).total_seconds()
            margin = self.future_margin * self.timespan
            t_min = t_now - self.timespan + margin
            t_max = t_now + margin
            t_ax = self.panels.panels['tz']
            t_ax.set_xlim((t_min, t_max))
            

class LiveLMADataset(object):
    
    def __init__(self, target=None, host=None, basedate=None):
        self.target = target
        self.bounds_updated_xchg = get_exchange('SD_bounds_updated')
        self.bounds_updated_xchg.attach(self)
        
        self._t_offset = 0.0
        if basedate is not None:
            # corrects for the meaning of time in the LMA analysis code
            self._t_offset += (basedate - datetime(1970, 1, 1)).total_seconds()           
            
        self._dataq = deque([])
        
        self.livesource = LiveLMAController()
        
        # New sources are sent as messages to self.show
        self.livesource.views.append(self)
        
        self._websocket_client = WebsocketClient(host=host)
        # client.connect(on_message=liveDataController.on_message)
        sock_thr = threading.Thread(target=self._websocket_client.connect, 
                        kwargs={'on_message':self.livesource.on_message})
        sock_thr.daemon=True
        sock_thr.start()
        
    def show(self, header, newdata):
        # print("{0} new, {1} stations".format(header['num_sources'][0], header['num_stations'][0]))
        if newdata.shape[0] > 0:
            newdata = rename_fields(newdata, {'t':'time'})
            newdata['time'] -= self._t_offset
            self._dataq.append(newdata)
            self.send("B4D_LMAnewsources_live")
    
    def send(self, msg):
        """ SD_bounds_updated messages are sent here """
        
        # do we send the whole events table, or somehow dynamically determine that?
        if len(self._dataq) > 0:
            data = np.hstack([d for d in self._dataq if (d.shape[0] > 0)])
            # print "sending data to {0} with generator frame {1}".format(self.target, self.target.gi_frame)
            if self.target is not None:
                self.target.send(data)
