# Eric Bruning, 11 October 2014. License: BSD (new).
# Modified from the vispy Mesh and ModularMesh examples.

import numpy as np
pi = np.pi

import vispy
import vispy.app
# from vispy.scene.visuals.modular_mesh import ModularMesh
from vispy.scene.visuals import Mesh
from vispy.geometry import MeshData
from vispy.scene import STTransform##, MatrixTransform

def synthetic_field(x,y):
    # Trapp and Doswell (2000, Mon. Weather Rev.) analytic input field
    z0 = 0.5
    amplitude = 0.5
    Lx = Ly = 30.0
    x_shift = 0#10.0 # shift the field, leave the radar at 0,0
    y_shift = 15/4.0 #-5.0
    x_wavenumber = 2
    y_wavenumber = x_wavenumber
    D = z0+amplitude * (np.cos(2*pi*x_wavenumber*(x-x_shift)/Lx) *
                        np.sin(2*pi*y_wavenumber*(y-y_shift)/Ly) )
    return D

# create polar mesh data
def radar_example_data():
    """ Create a cone of regularly gridded data in spherical
        (range, azimuth, elevation) coordinates. The data values
        have an undulating pattern tied to the cartesian x,y location.

        This is a quadrilateral 2D mesh surface, but demonstrative of
        a more general case where the quadrilaterals' corners
        must each be specified manually. This is a common need in the case
        of, for instance, weather radar data.

        Returns x,y,z locations of the M x N vertices and
        (M-1) x (N-1) data value arrays.
        """
    radar_x0 = 0.0
    radar_y0 = 0.0
    radar_z0 = 0.0

    el = np.radians(30.0)

    all_r  = np.arange(5, 35, 0.75)
    all_az_deg = np.arange(0,361, 2)
    all_az = np.radians(all_az_deg)

    # Observation locations
    r_edge, az_edge = np.meshgrid(all_r, all_az)
    # >>> print r.shape
    # 360, 200 = (naz, nr)
    r  = (( r_edge[1:, 1:] +  r_edge[:-1, :-1]) / 2.0)
    az = ((az_edge[1:, 1:] + az_edge[:-1, :-1]) / 2.0)

    x_radar_edge = r_edge*np.cos(az_edge) + radar_x0
    y_radar_edge = r_edge*np.sin(az_edge) + radar_y0
    z_radar_edge = r_edge*np.sin(el) + radar_z0

    x_radar = r*np.cos(az) + radar_x0
    y_radar = r*np.sin(az) + radar_y0
    z_radar = r*np.sin(el) + radar_z0

    # values at sampled locations
    all_d = synthetic_field(x_radar, y_radar)

    return (x_radar_edge, y_radar_edge, z_radar_edge, all_d)

def mesh_from_quads(x,y,z):
    """ x, y, z are M x N arrays giving the edge locations for
        a quadrilateral mesh of Nq = (M-1) x (N-1) implied quad faces.
        After conversion to triangles, this is Nf=2*Nq faces.
        Nv = M x N.

        returns
        vertices : ndarray, shape (Nv, 3) - Vertex coordinates.
        faces : ndarray, shape (Nf, 3) - Indices into the vertex array.

        Along each row, the triangles' diagonals are oriented in
        the same direction. Each new row of triangles is specified from
        left-to-right.

        An alternate face specification (1) would go back and forth,
        alternating the triangles' diagonal direction. It would be
        more amenable GL_TRIANGLE_STRIP.
        (1) http://dan.lecocq.us/wordpress/2009/12/25/triangle-strip-for-grids-a-construction/
        """
    M, N = x.shape
    Nv = M * N
    Nq = (M-1) * (N-1)
    Nf = 2*Nq
    verts = np.empty((Nv, 3), dtype='f4')
    faces = np.empty((Nf, 3), dtype='i4')

    verts[:,0] = x.flat
    verts[:,1] = y.flat
    verts[:,2] = z.flat

    q_range = np.arange(Nq, dtype='i4')

    # When the index along M changes, need to skip ahead to avoid connecting
    # the edges together.
    # Should look like (0,0,0,1,1,1,2,2,2,3,3,3) for N-1=3 and M-1=4
    adjust_start = (np.arange(M-1, dtype=np.int32)[:,None]*np.ones(N-1, dtype=np.int32)[None,:]).flatten()
#    adjust_start = (np.arange(M-1, dtype='i4')[:,None]*np.ones(N-1, dtype='i4')[None,:]).flatten()
    q_range+=adjust_start

    # even (0,2,4,...) triangles
    faces[0::2, 0] = q_range + 1
    faces[0::2, 1] = q_range
    faces[0::2, 2] = q_range + N
    # odd (1,3,5,...) trianges
    faces[1::2, 0] = q_range + N
    faces[1::2, 1] = q_range + N + 1
    faces[1::2, 2] = q_range + 1

    return verts, faces



class Canvas(vispy.scene.SceneCanvas):
    def __init__(self):
##        self.rotation = MatrixTransform()
        self.rotation = vispy.scene.transforms.MatrixTransform()

        # Generate some data to work with
        x,y,z,d = radar_example_data()
        print x.shape, y.shape, z.shape
        print d.shape, d.min(), d.max()

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
        mesh.transform = vispy.scene.transforms.MatrixTransform()
        mesh.transform.scale([1./10, 1./10, 1./10])

        vispy.scene.SceneCanvas.__init__(self, keys='interactive')

        self.size = (800, 800)
        self.show()
        view = self.central_widget.add_view()
        # view.set_camera('turntable', mode='ortho', up='z', distance=2)
        view.camera='turntable'
        view.camera.mode='ortho'
        view.camera.up='z'
        view.camera.distance=20
        view.add(mesh)


if __name__ == '__main__':
    win = Canvas()
    import sys
    if sys.flags.interactive != 1:
        vispy.app.run()
