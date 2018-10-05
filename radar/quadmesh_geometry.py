# Eric Bruning, 11 October 2014. License: BSD (new).
# Modified from the vispy Mesh and ModularMesh examples.

from __future__ import absolute_import
import numpy as np
pi = np.pi


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

    all_r  = np.arange(5, 50.0, 0.75)
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

def mesh_from_quads(x,y,z, dup_verts=False):
    """ x, y, z are M x N arrays giving the edge locations for
        a quadrilateral mesh of Nq = (M-1) x (N-1) implied quad faces.
        After conversion to triangles, this is Nf=2*Nq faces.
        Nv = M x N.
        
        If the keyword argument dup_verts=True, then x,y,z vertices 
        will be replicated, such that each quad has its own
        vertices not shared with other quads. This allows one to specify
        colors by vertex if coloring by face is not supported.
        
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
    
    if dup_verts:
        n_repeat = 2
    else:
        n_repeat = 1
        
    M, N = x.shape
    Nv = (M * n_repeat) * (N * n_repeat)
    Nq = (M-1) * (N-1)
    Nf = 2*Nq
    verts = np.empty((Nv, 3), dtype='f4')
    faces = np.empty((Nf, 3), dtype='i4')
    
    xv = np.repeat(np.repeat(x,n_repeat,axis=0), n_repeat, axis=1)
    yv = np.repeat(np.repeat(y,n_repeat,axis=0), n_repeat, axis=1)
    zv = np.repeat(np.repeat(z,n_repeat,axis=0), n_repeat, axis=1)
    
    verts[:,0] = xv.flat
    verts[:,1] = yv.flat
    verts[:,2] = zv.flat
        
    q_range = np.arange(Nq, dtype='i4')*n_repeat
    q_range += (N*n_repeat + 1)*(n_repeat-1)
    
    # When the index along M changes, need to skip ahead to avoid connecting
    # the edges together.
    adjust_start = (np.arange(M-1, dtype='i4')[:,None] * 
                    np.ones(N-1, dtype='i4')[None,:]).flatten()
    adjust_adjust = adjust_start * (N*n_repeat+1)
    q_range+=adjust_start + adjust_adjust*(n_repeat-1)

    # for N-1=3 and M-1=4 and n_repeat=1, the final values are
    # adjust_start = (0,0,0,1,1,1,2,2,2,3,3,3) 
    # q_range = (0,1,2,4,5,6,8,9,10,12,13,14)

    
    # repeated arrays for N-1=4, M-1=3 -- need to redo this block with correct N, M
    # xv=array([[0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
    #        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
    #        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
    #        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
    #        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
    #        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
    #        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
    #        [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]])

    # yv=array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    #        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    #        [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    #        [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    #        [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
    #        [3, 3, 3, 3, 3, 3, 3, 3, 3, 3]])    
    #     First quad is 11, 12, 21, 22, which becomes and upper and lower triangle 
    #         (first column of expanded indices below)
    #     Second quad is 13, 14, 23, 24
    #     Third quad is 15, 16, 25, 26
    #     Fourth quad is 17, 18, 27, 28 --- skip down two rows now, adding 20=N*n_repeat*n_repeat to the first 
    #     Fifth quad is 31, 32, 41, 42
    #     Six quad is 33, 34, 43, 44
    
    # M=5, N=4
    # each quad becomes and upper and lower triangle (first column of expanded indices below)
    # first entry is q_range[0] + (N*n_repeat + 1)*(n_repeat-1)
    # First quad is 9, 10, 17, 18  (instead of 0, 1, 4, 5) - second pair increases by N*n_repeat
    # Second quad is 11, 12, 19, 20 (instead of 1, 2, 5, 6) - second quad increases by two in each pos'n - q_range*n_repeat and adjust_range*n_repeat
    # Third quad is 13, 14, 21, 22 (insted of 2, 3, 6, 7)

    # skip down two rows now, adding 16 = N*n_repeat*n_repeat. This is the number by which to multiply adjust_start.
    # Fourth quad is 25, 26, 33, 34 (instead of 4, 5, 8, 9)
    # Fifth quad is 27, 28, 35, 36 (instead of 5, 6, 9, 10)
    # Sixth quad is 29, 30, 37, 38 (instead of 6, 7, 10, 11)
    #     print(adjust_start)
    #     print(q_range                 )
    #     print(q_range + 1             )
    #     print(q_range + N*n_repeat    )
    #     print(q_range + N*n_repeat + 1)
    #     print(xv)
    #     print(yv)

    #     np.repeat(q_range,n_repeat)
    
    # numbers below are for for N-1=3 and M-1=4 and n_repeat=1
    # even (0,2,4,...) triangles
    faces[0::2, 0] = q_range + 1               # (1,2,3,5, 6, 7, 9,10,11,13,14,15)
    faces[0::2, 1] = q_range                   # (0,1,2,4, 5, 6, 8, 9,10,12,13,14)
    faces[0::2, 2] = q_range + N*n_repeat      # (4,5,6,8, 9,10,12,13,14,16,17,18)
    # odd (1,3,5,...) trianges
    faces[1::2, 0] = q_range + N*n_repeat      # (4,5,6,8, 9,10,12,13,14,16,17,18)
    faces[1::2, 1] = q_range + N*n_repeat + 1  # (5,6,7,9,10,11,13,14,15,17,18,19)
    faces[1::2, 2] = q_range + 1               # (1,2,3,5, 6, 7, 9,10,11,13,14,15)

    return verts, faces    

def tri_colors_from_quadmesh(x,y,z,d, dup_verts=True, cm=None, vmin=0, vmax=1):
    verts, faces = mesh_from_quads(x,y,z, dup_verts=dup_verts)
    # print(verts.shape, faces.shape)

    # Face_colors increases first in range, then in azimuth. 
    # d[azidx, ridx]
    # The triangles receive colors with the lower triangles all in a row, then the upper triangles all in a row,
    # which completes all the triangles in range.
    # For six azimuths and five ranges, this is [d[0,:], d[0,:]] for the first azimuth,  

    squashed = d.flatten()
    face_colors = np.empty((faces.shape[0], 4))
    if cm is None:
        squashed -= squashed.min()
        squashed /= (vmax-vmin) # squashed.max()
        face_colors[0::2,0] = squashed
        face_colors[0::2,1] = squashed
        face_colors[0::2,2] = squashed
        face_colors[1::2,0] = squashed
        face_colors[1::2,1] = squashed
        face_colors[1::2,2] = squashed
        face_colors[:,3] = 1.0 # transparency
    else:
        colors = cm.to_rgba(squashed)
        face_colors[0::2] = colors
        face_colors[1::2] = colors

    if dup_verts:
        n_repeat=2
    else:
        n_repeat=1
    xv = np.repeat(np.repeat(x,n_repeat,axis=0), n_repeat, axis=1)
    dv = np.zeros_like(xv)
    dv[1:-1, 1:-1] = np.repeat(np.repeat(d,n_repeat,axis=0), n_repeat, axis=1)

    squashed = dv.flatten()
    if cm is None:
        vert_colors = np.ones((verts.shape[0], 4))
        squashed -= squashed.min()
        squashed /= (vmax-vmin) # squashed.max()
        vert_colors[:,0] = squashed
        vert_colors[:,1] = squashed
        vert_colors[:,2] = squashed
    else:
        vert_colors = cm.to_rgba(squashed)
        
    colors=vert_colors
    
    return verts, faces, colors