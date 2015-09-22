import numpy as np
import datetime

from collection import RadarFileCollection
from pyart.graph.common import sweep_coords_to_cart, corner_to_point
from quadmesh_geometry import mesh_from_quads, radar_example_data

from vispy import gloo
import vispy
import vispy.app
# from vispy.scene.widgets import ViewBox
from vispy.scene.visuals import Mesh
from vispy.scene.visuals import Text
from vispy.geometry import MeshData
from vispy.scene import STTransform, MatrixTransform, ChainTransform

from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

import glob

loc_ka = (33.73732, -101.84326)
loc_88d = (33.654140472412109, -101.81416320800781)
dx_ka, dy_ka = corner_to_point(loc_ka, loc_88d) #meters

#-------------------
# Selection of interesting times
#-------------------

# filenames = glob.glob('/data/20140607/Ka2/Ka2140608031*')#[5:10]
# filenames_88d = glob.glob('/data/20140607/88D/KLBB20140608_031*')
# t_start = datetime.datetime(2014,6,8,3,16,29)

# filenames = glob.glob('/data/20140607/Ka2/Ka2140608033*')#[5:10]
# filenames_88d = glob.glob('/data/20140607/88D/KLBB20140608_033*')
# t_start = datetime.datetime(2014,6,8,3,39,05)



# t_end  = t_start
# timer_interval = 10.0

#-------------------
filenames = glob.glob('/data/20140607/Ka2/Ka2140608031*')#[5:10]
filenames_88d = glob.glob('/data/20140607/88D/KLBB20140608_031*')
t_start = datetime.datetime(2014,6,8,3,10,0)
t_end  = datetime.datetime(2014,6,8,3,20,0)
#
#
# filenames = glob.glob('/data/20140607/Ka2/Ka2140608034*')#[5:10]
# filenames_88d = glob.glob('/data/20140607/88D/KLBB20140608_034*')
# t_start = datetime.datetime(2014,6,8,3,40,0)
# t_end  = datetime.datetime(2014,6,8,3,50,0)

timer_interval = 1.0
#-------------------


#-------------------

rfc = RadarFileCollection(filenames)
rfc_88d = RadarFileCollection(filenames_88d)



class Canvas(vispy.scene.SceneCanvas):
    def __init__(self):
                
        # self.vb = scene.widgets.ViewBox(parent=self.scene, border_color='b')
        # vb.camera.rect = 0, 0, 1, 1
        
        # self.rotation = MatrixTransform()

        # Generate some data to work with
        x,y,z,d = radar_example_data()
        # print x.shape, y.shape, z.shape
        # print d.shape, d.min(), d.max()
        mesh = self._init_mesh(x,y,z,d)
        mesh_88d = self._init_mesh(x,y,z,d)
        
        # Use colormapping class from matplotlib
        self.DZcm = ScalarMappable(norm=Normalize(-25,80), cmap='gist_ncar')
        self.VRcm = ScalarMappable(norm=Normalize(-32,32), cmap='PuOr_r')
        self.SWcm = ScalarMappable(norm=Normalize(0.0,5.0), cmap='cubehelix_r')

        
        self.radar_mesh = mesh
        self.mesh_88d = mesh_88d
        self.meshes = (mesh, mesh_88d)
        
        self.rot_view=None
        

        vispy.scene.SceneCanvas.__init__(self, keys='interactive')
        
        self.size = (800, 800)
        self.show()
        view = self.central_widget.add_view()
        view.camera='turntable'
        view.camera.mode='ortho'
        view.camera.up='z'
        view.camera.distance=20
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
        self.loop_start = t_start 
        self.loop_dt = datetime.timedelta(seconds=10)
        self.loop_end  = t_end
        self.loop_duration = datetime.timedelta(seconds=10)
        self.loop_current = self.loop_start
    
    def loop_radar(self, event):        
        current = self.loop_current
        last = current
        print(current)        
        self.loop_current = current + self.loop_dt

        # ----- Do Ka data -----
        ka_field = 'spectrum_width'
        # ka_field = 'reflectivity'
        r,az,el,t,data = rfc.sweep_data_for_time_range(current, 
                                                       current+self.loop_duration, 
                                                       fieldnames=(ka_field,))
        if r is not None:
            if np.abs(az.mean() - 315.0) > 10:
                az += 90.0
            d = data[ka_field][1:-1, 1:-150]
            
            # print "Found Ka", r.shape, az.shape, el.shape, d.shape
            # print r.min(), r.max(), el.min(), el.max(), az.min(), az.max(), d.min(), d.max()
            verts, faces, face_colors = self._make_plot(r[1:-150], az[1:-1], el[1:-1], 
                                                        # d, vmin=-32.0, vmax=25.0, cm=self.DZcm,
                                                        d, vmin=-1.0, vmax=5.0, cm=self.SWcm,
                                                        dx=-dx_ka, dy=-dy_ka)
                                                        
            # print('vert range', verts.min(), verts.max())
                                                        
            self.radar_mesh.set_data(vertices=verts, faces=faces, face_colors=face_colors)

        # ----- Do 88D data -----       
        base88d_field = 'reflectivity'
        # base88d_field = 'spectrum_width'
        r,az,el,t,data = rfc_88d.sweep_data_for_time_range(current, 
                                                       current+self.loop_duration, 
                                                       fieldnames=(base88d_field,))
        if r is not None:
            if (el.mean() < 2.0):
                d = data[base88d_field][1:-1, 1:300]
                # print "Found 88D", r.shape, az.shape, el.shape, d.shape
                # print r.min(), r.max(), el.min(), el.max(), az.min(), az.max(), d.min(), d.max()
                verts, faces, face_colors = self._make_plot(r[1:300], az[1:-1], el[1:-1], 
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
        x,y,z = sweep_coords_to_cart(r,az,el, edges=True)
        x += dx
        y += dy
        # print(x.shape, y.shape, z.shape, d.shape)
        verts, faces = mesh_from_quads(x,y,z)

        squashed = d.filled(vmin).flatten()
        face_colors = np.empty((faces.shape[0], 4))        
        if cm is None:
            squashed -= squashed.min()
            squashed /= (vmax-vmin) # squashed.max()
            # print squashed.min(), squashed.max()
            # print(face_colors[0::2,0].shape, squashed.shape)
            face_colors[0::2,0] = squashed # d.flat
            face_colors[0::2,1] = squashed # d.flat
            face_colors[0::2,2] = squashed # d.flat
            face_colors[1::2,0] = squashed # d.flat
            face_colors[1::2,1] = squashed # d.flat
            face_colors[1::2,2] = squashed # d.flat
            face_colors[:,3] = 1.0 # transparency
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

        


canvas = Canvas()
vispy.app.run()
# canvas.radar_mesh.set_data(self, vertices=None, faces=None, vertex_colors=None, face_colors=None, meshdata=None, color=None)