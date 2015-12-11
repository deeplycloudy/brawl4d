import pandas
import numpy as np
import pyart

def diagnose_vcp(radar):
    # swp_start = radar.sweep_start_ray_index['data']
    # swp_end = radar.sweep_end_ray_index['data']+1
    if 'ppi' in radar.scan_type.lower():
        angles = [np.median(el) for el in radar.iter_elevation()]
    else:
        angles = [np.median(az) for az in radar.iter_azimuth()]
    return angles

def data_for_ray_slice(radar, ray_sl, fieldnames=None):
    """ Given a slice object ray_sl, return r,az,el,t,data
        corresponding to the fieldnames. If fieldname is None,
        no data will be returned. Fieldnames should be a sequence of field
        names. A data dictionary is returned with a key for each of the field names.

        ray_sl is typically found from the radar's sweep index record.
        For some sweep id N, this is:
        ray_sl = slice( radar.sweep_start_ray_index['data'][N],
                        radar.sweep_end_ray_index['data'][N] + 1)
    """
    r = radar.range['data']
    az = radar.azimuth['data'][ray_sl]
    el = radar.elevation['data'][ray_sl]
    t = radar.time['data'][ray_sl]
    data_dict = {}
    if fieldnames is not None:
        for fieldname in fieldnames:
            try:
                data = radar.fields[fieldname]['data'][ray_sl, :]
            except KeyError:
                data = None
                print("Couldn't find {1} data in {0}".format(radar,fieldname))
            data_dict[fieldname] = data

    return r,az,el,t,data_dict

def iter_sweep_data(radar, fieldnames):
    for swp_start, swp_end in zip(radar.sweep_start_ray_index['data'],
                                  radar.sweep_end_ray_index['data']):
        print swp_start, swp_end
        ray_sl = slice(swp_start,swp_end+1)
        yield data_for_ray_slice(radar,ray_sl,fieldnames=fieldnames)

class RadarFileCollection(object):
    """

    """
    def __init__(self, filenames):
        self.filenames=filenames
        self.radars = {}
        self.times = {}
        for fname in filenames:
            radar = pyart.io.auto_read.read(fname)
            self.radars[fname] = radar
            times = pyart.util.datetime_utils.datetimes_from_radar(self.radars[fname])
            self.times[fname] = times
        self.sweep_table = pandas.DataFrame([v for v in self._iter_sweep_index_data()],
                                            columns = ('filename', 'sweep_slice', 'start', 'end', 'mode', 'angle')
                                            )

    def _iter_sweep_time_range(self, fname):
        """ Yields (sweep_slice, min_t, max_t)
            for the given radar filename. Times are datetime objects.
            """
        radar = self.radars[fname]
        datetimes = self.times[fname]
        for swp_start, swp_end in zip(radar.sweep_start_ray_index['data'],
                                      radar.sweep_end_ray_index['data']):
            ray_sl = slice(swp_start,swp_end+1)
            t = datetimes[ray_sl]
            yield ray_sl, min(t), max(t)

    def _iter_sweep_index_data(self):
        for fname in self.filenames:
            radar = self.radars[fname]
            mode = radar.scan_type.lower()
            vcp = diagnose_vcp(radar)
            for (swp_sl, swp_ta, swp_tb), angle in zip(self._iter_sweep_time_range(fname), vcp):

                yield fname, swp_sl, np.datetime64(swp_ta, 'ns'), np.datetime64(swp_tb, 'ns'), mode, angle


    def sweep_for_time_range(self, t0, t1, overlap_idx=0):
        """ Given some time range t0, t1 return the closest sweep to that time.
            t0 and t1 are datetime objects

            If there is only one sweep that overlaps, return it.

            overlap_idx = 0: (default) returns the first sweep with overlap
            overlap_idx = -1: returns the last sweep with overlap
            So, the default behavior is to return the first sweep to have any overlap.

            Returns filename, sweep_slice.

            Unimplemented
            -------------
            If there are two sweeps that overlap, one could:
                return first or last, or the one with the most overlap

            With more than two sweeps, the first and last will have partial overlap
                return first or last partial overlap
                return the first or last that fully overlaps
                return the sweep with most overlap
                    choosing the first or last of those if there are several of the same length



                                   t0           t1
                                   |            |
            ... -------------- -------------- ------------------ -------------- ...
                ta3        tb3 ta4        tb4 ta5            tb5 ta6        tb6

            conditions for some overlap
            t1 > ta4  so t1 - ta4 > 0
            t0 < tb4  so t0 - tb4 < 0

        """

        #target = pandas.DataFrame([(t0, t1),], columns=('start', 'end'))
##        print("t0/t1 type = {0}/{1}".format(np.dtype(t0), np.dtype(t1)))
##        print("sweep_table['end'] type = {0}".format(np.dtype(self.sweep_table['end'])))
##        print("sweep_table['start'] type = {0}".format(np.dtype(self.sweep_table['start'])))
        dt_zero = np.timedelta64(0,'ns')
        overlap = ((t0 - self.sweep_table['end'].values) < dt_zero) & ((t1 - self.sweep_table['start'].values) > dt_zero )
        sweeps = self.sweep_table[overlap]
        if len(sweeps) > 0:
            selection = np.zeros(len(sweeps), dtype=bool)
            selection[overlap_idx] = True
            sweep_info = sweeps[selection]
            # only one element left at this point.
            return sweep_info['filename'].values[0], sweep_info['sweep_slice'].values[0]
        else:
            return None, None

    def sweep_data_for_time_range(self, t0, t1, fieldnames=None, **kwargs):
        """ return r,az,el,t,data corresponding to the fieldnames. If fieldname is None,
            no data will be returned. Fieldnames should be a sequence of field
            names. A data dictionary is returned with a key for each of the field names.

            t0, t1 and extra kwargs are passed to self.sweep_for_time_range
        """
        filename, ray_slice = self.sweep_for_time_range(t0, t1, **kwargs)
        if filename is not None:
            radar = self.radars[filename]
            return data_for_ray_slice(radar, ray_slice, fieldnames=fieldnames)
        else:
            return None, None, None, None, None

    def _time_range_for_file(self, fname):
        """ Called once by init to set up frame lookup tables and yield
            the frame start times. _frame_lookup goes from
            datetime->(nc file, frame index)"""
        # datetimes_from_radar returns the time of each ray to the nearest second
        times = pyart.util.datetime_utils.datetimes_from_radar(self.radars[fname])
        return min(times), max(times)

    def _all_times(self):
        for f in self.filenames:
            for tmin,tmax in self._time_range_for_file(f):
                yield tmin, tmax
