import threading
from collections import deque

import numpy as np

from stormdrain.pubsub import get_exchange
from lmatools.live.liveLMA import LiveLMAController, WebsocketClient

class LiveLMADataset(object):
    
    def __init__(self, target=None, host=None):
        self.target = target
        self.bounds_updated_xchg = get_exchange('SD_bounds_updated')
        self.bounds_updated_xchg.attach(self)
        
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
        print("{0} new, {1} stations".format(header['num_sources'][0], header['num_stations'][0]))
        self._dataq.append(newdata)
        self.send("B4D_LMAnewsources_live")

    def send(self, msg):
        """ SD_bounds_updated messages are sent here """
        
        # do we send the whole events table, or somehow dynamically determine that?
        if len(self._dataq) > 0:
            data = np.hstack([d for d in self._dataq if (d.shape[0] > 0)])
        
            if self.target is not None:
                self.target.send(data)