import numpy as np

from collection import RadarFileCollection
from pyart.core.transforms import antenna_vectors_to_cartesian, corner_to_point
from quadmesh_geometry import mesh_from_quads, radar_example_data

from vispy import gloo
import vispy
import vispy.app
# from vispy.scene.widgets import ViewBox
from vispy.scene.visuals import Mesh, Text
from vispy.geometry import MeshData
from vispy.scene import STTransform, ChainTransform, MatrixTransform

from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

import glob


class Canvas(vispy.scene.SceneCanvas):
    def __init__(self, size=(800, 800), name="Radar Loop",
                 timer_interval=1.0,
                 num_radars=1,
                 radar_filenames=None,
                 radar_latlons=None,
                 radar_fields=None,
                 time_start=None, time_end=None,
                 loop_step=10, image_duration=10):

        '''
        Parameters
        ----------
        size : 2-tuple int
            (x, y) size in pixels of window.
        name : str
            Name to use in window label.
        timer_interval : float
            Interval at which to update data in window.
        num_radars : int
            The number of radars to display.
        radar_filenames : list
            List of radar filenames to process. This can be a list of lists
            if multiple radars are desired. num_radars must be > 1.
        radar_latlons : list of tuples
            List of (latitude, longitude) coordinates. This can be a list
            the same length as radar_filenames. num_radars must be > 1.
        time_start : datetime instance
            Start time to use for subset.
        time_end : datetime instance
            End time to use for subset.
        loop_step : float
            Seconds between image update in frame.
        image_duration : float
            Seconds that each image will last in frame.
        '''
        # self.vb = scene.widgets.ViewBox(parent=self.scene, border_color='b')
        # vb.camera.rect = 0, 0, 1, 1

        # self.rotation = MatrixTransform()

        # Perform a couple of checks
        if radar_filenames is None:
            print("Must provide a list of filenames!")
            return
        if (num_radars > 1) & (len(radar_filenames) != num_radars) & (len(radar_latlons) != num_radars):
            print("ERROR: Must provide filenames and lat-lons for each radar!")
            return

        # Prepare some variables if two radars are chosen
        self.radar_filenames = radar_filenames
        self.t_start = time_start
        self.t_end = time_end
        self.rnum = num_radars
        self.loop_dt = np.timedelta64(loop_step * 1000000000, 'ns')
        self.loop_duration = np.timedelta64(image_duration * 1000000000, 'ns')

        # Read in the radar files into a collection
        self.rfc = []
        self.rfc = []
        for ii in range(self.rnum):
            self.rfc.append(RadarFileCollection(self.radar_filenames[ii]))

##        self.rfc = RadarFileCollection(filenames)
        self.rfc_88d = RadarFileCollection(filenames_88d)

        # Initialize variables for later use
        self.dx, self.dy = [], []
        if radar_fields is None:
            self.radar_fields = ['reflectivity']
        else:
            self.radar_fields = [radar_fields[0]]

        # Find corner points if required
        if len(radar_latlons) > 1:
            for num in range(1, len(radar_latlons)):
                dx_tmp, dy_tmp = corner_to_point(radar_latlons[num], radar_latlons[num-1]) #meters
                self.dx.append(dx_tmp)
                self.dy.append(dy_tmp)
                try:
                    self.radar_fields.append(radar_fields[num])
                except:
                    self.radar_fields.append('reflectivity')

        # Generate dummy data to initialize the Mesh instance
        x, y, z, d = radar_example_data()
        # print x.shape, y.shape, z.shape
        # print d.shape, d.min(), d.max()
        mesh = self._init_mesh(x, y, z, d)
        mesh_88d = self._init_mesh(x, y, z, d)

        # Use colormapping class from matplotlib
        self.DZcm = ScalarMappable(norm=Normalize(-25,80), cmap='gist_ncar')
        self.VRcm = ScalarMappable(norm=Normalize(-32,32), cmap='PuOr_r')
        self.SWcm = ScalarMappable(norm=Normalize(0.0,5.0), cmap='cubehelix_r')

        self.radar_mesh = mesh
        self.mesh_88d = mesh_88d
        self.meshes = (mesh, mesh_88d)

        self.rot_view = None

        vispy.scene.SceneCanvas.__init__(self, keys='interactive',
                                         title=name, size=size, show=True)

        view = self.central_widget.add_view()
        view.camera = 'turntable'
        view.camera.mode = 'ortho'
        view.camera.up = 'z'
        view.camera.distance = 20
        self.rot_view = view

        for a_mesh in self.meshes:
            self.rot_view.add(a_mesh)

        self.unfreeze() # allow addition of new attributes to the canvas
        self.t1 = Text('Time', parent=self.scene, color='white')
        self.t1.font_size = 18
        self.t1.pos = self.size[0] // 2, self.size[1] // 10

        self.loop_reset()
        self.timer = vispy.app.Timer(connect=self.loop_radar)
        self.timer.start(timer_interval)

    def _init_mesh(self, x,y,z,d):
        verts, faces = mesh_from_quads(x,y,z)
        face_colors = np.empty((faces.shape[0], 4))
        face_colors[0::2,0] = d.flat
        face_colors[0::2,1] = d.flat
        face_colors[0::2,2] = d.flat
        face_colors[1::2,0] = d.flat
        face_colors[1::2,1] = d.flat
        face_colors[1::2,2] = d.flat
        face_colors[:,3] = 1.0 # transparency
        mdata = MeshData(vertices=verts, faces=faces, face_colors=face_colors)
        mesh = Mesh(meshdata=mdata)

        # mesh.transform = ChainTransform([STTransform(translate=(0, 0, 0),
        #                                              scale=(1.0e-3, 1.0e-3, 1.0e-3) )])
        mesh.transform = vispy.scene.transforms.MatrixTransform()
        mesh.transform.scale([1./1000, 1./1000, 1./1000])
        # mesh.transform.shift([-.2, -.2, -.2])
        return mesh

    def loop_reset(self):
        if self.t_start is not None:
            self.loop_start = self.t_start
        else:
            self.loop_start = np.datetime64(np.min(self.rfc[0].times.values()), 'ns')
        if self.t_end is not None:
            self.loop_end  = self.t_end
        else:
            self.loop_end = np.datetime64(np.max(self.rfc[0].times.values()), 'ns')
        self.loop_current = self.loop_start

    def loop_radar(self, event):
        current = self.loop_current
        last = current
        print(current)
        self.loop_current = current + self.loop_dt

        # ----- Do Ka data -----
#         ka_field = 'spectrum_width'
#         # ka_field = 'reflectivity'
#         r,az,el,t,data = self.rfc.sweep_data_for_time_range(current,
#                                                        current+self.loop_duration,
#                                                        fieldnames=(ka_field,))
#         if r is not None:
#             if np.abs(az.mean() - 315.0) > 10:
#                 az += 90.0
#             d = data[ka_field][1:-1, 1:-150]
#
#             # print "Found Ka", r.shape, az.shape, el.shape, d.shape
#             # print r.min(), r.max(), el.min(), el.max(), az.min(), az.max(), d.min(), d.max()
#             verts, faces, face_colors = self._make_plot(r[1:-150], az[1:-1], el[1:-1],
#                                                         # d, vmin=-32.0, vmax=25.0, cm=self.DZcm,
#                                                         d, vmin=-1.0, vmax=5.0, cm=self.SWcm,
#                                                         dx=-dx_ka, dy=-dy_ka)
#
#             # print('vert range', verts.min(), verts.max())
#
#             self.radar_mesh.set_data(vertices=verts, faces=faces, face_colors=face_colors)

        # ----- Do 88D data -----
        for ii in range(self.rnum):
            r, az, el, t, data = self.rfc[ii].sweep_data_for_time_range(current,
                                                       current+self.loop_duration,
                                                       fieldnames=(self.radar_fields[0],))
            if r is not None:
                if (el.mean() < 2.0):
                    d = data[self.radar_fields[ii]][1:-1, 1:300]
                    # print "Found 88D", r.shape, az.shape, el.shape, d.shape
                    # print r.min(), r.max(), el.min(), el.max(), az.min(), az.max(), d.min(), d.max()
                    verts, faces, face_colors = self._make_plot(
                                                   r[1:300], az[1:-1], el[1:-1],
                                                   d, vmin=-25.0, vmax=80.0, cm=self.DZcm)
                                                # d, vmin=0.0, vmax=0.4, cm=self.SWcm)
                                                # d, vmin=-32.0, vmax=32.0, cm=self.VRcm)
                    self.mesh_88d.set_data(vertices=verts, faces=faces, face_colors=face_colors)
                    face_colors[:,3] = 0.5

        # ----- Update plot -----
        self.t1.text='{0} UTC'.format(current)
        # for m in self.meshes:
        #     m._program._need_build = True
        self.update()

        if last>self.loop_end:
            self.loop_reset()

    def _make_plot(self, r, az, el, d, vmin=-32, vmax=70, dx=0.0, dy=0.0, cm=None):
        """ Data are normalized using the min of the data array
            after replacing missing values with vmin, so vmin should be less
            than the minimum data value
        """
        x, y, z = antenna_vectors_to_cartesian(r, az, el, edges=True)
        x += dx
        y += dy
        # print(x.shape, y.shape, z.shape, d.shape)
        verts, faces = mesh_from_quads(x, y, z)

        squashed = d.filled(vmin).flatten()
        face_colors = np.empty((faces.shape[0], 4))
        if cm is None:
            squashed -= squashed.min()
            squashed /= (vmax-vmin) # squashed.max()
            # print squashed.min(), squashed.max()
            # print(face_colors[0::2,0].shape, squashed.shape)
            face_colors[0::2, 0] = squashed # d.flat
            face_colors[0::2, 1] = squashed # d.flat
            face_colors[0::2, 2] = squashed # d.flat
            face_colors[1::2, 0] = squashed # d.flat
            face_colors[1::2, 1] = squashed # d.flat
            face_colors[1::2, 2] = squashed # d.flat
            face_colors[:, 3] = 1.0 # transparency
        else:
            colors = cm.to_rgba(squashed)
            face_colors[0::2] = colors
            face_colors[1::2] = colors

        return verts, faces, face_colors

    def on_draw(self, ev):
        gloo.set_clear_color('black')
        gloo.clear(color=True, depth=True, stencil=True)
        if self.rot_view is not None:
            self.draw_visual(self.rot_view)
            self.draw_visual(self.t1)
        # for mesh in self.meshes:
        #     print mesh
        #     self.draw_visual(mesh)


if __name__ == '__main__':

#-------------------
# Selection of interesting times
#-------------------

# filenames = glob.glob('/data/20140607/Ka2/Ka2140608031*')#[5:10]
# filenames_88d = glob.glob('/data/20140607/88D/KLBB20140608_031*')
#    t_start = np.datetime64('2014-06-08T03:16:29Z', 'ns')

# filenames = glob.glob('/data/20140607/Ka2/Ka2140608033*')#[5:10]
# filenames_88d = glob.glob('/data/20140607/88D/KLBB20140608_033*')
#    t_start = np.datetime64('2014-06-08T03:39:05Z', 'ns')



# t_end  = t_start
# timer_interval = 10.0

#-------------------
#
#
# filenames = glob.glob('/data/20140607/Ka2/Ka2140608034*')#[5:10]
# filenames_88d = glob.glob('/data/20140607/88D/KLBB20140608_034*')
#    t_start = np.datetime64('2014-06-08T03:40:00Z', 'ns')
#    t_end  = np.datetime64('2014-06-08T03:50:00Z', 'ns')

#-------------------

    filenames = glob.glob('/Users/guy/data/test/brawl_vispy/Ka2/Ka2140608031*')#[5:10]
    filenames_88d = glob.glob('/Users/guy/data/test/brawl_vispy/88D/KLBB20140608_031*')
##    t_start = datetime.datetime(2014,6,8,3,10,0)
##    t_end  = datetime.datetime(2014,6,8,3,20,0)
    t_start = np.datetime64('2014-06-08T03:10:00Z', 'ns')
    t_end  = np.datetime64('2014-06-08T03:20:00Z', 'ns')
#    dloop, dimage = 10, 10

    canvas = Canvas(
                    radar_filenames=[filenames_88d],
                    radar_latlons=[(33.654140472412109, -101.81416320800781),
                                   (33.73732, -101.84326)],
                    time_start=t_start, time_end=t_end,
##                    loop_step=dloop, image_duration=dimage
                    )
    vispy.app.run()
# canvas.radar_mesh.set_data(self, vertices=None, faces=None, vertex_colors=None, face_colors=None, meshdata=None, color=None)