import math
from psychopy.misc import deg2cm, cm2deg, cm2pix, pix2cm, deg2pix, pix2deg

def get_dist(pos1, pos2, aspect=1.0):
    dist=math.sqrt((pos1[0]-pos2[0])**2+((pos1[1]-pos2[1])/aspect)**2)
    return dist

def get_vertex_list(radius, n, aspect=1.0):
    vertex_angle=2*math.pi/float(n)
    vertex_list=[]
    for i in range(int(n)):
        vertex_list.append([radius*math.sin(vertex_angle*(i+1))/aspect, radius*math.cos(vertex_angle*(i+1))])
    return vertex_list

def parse_coordinate(node):
    x=float(node.find('x').text)
    y=float(node.find('y').text)
    return x,y

def cm2norm_x(position, window):
    scrWidthCm = window.getWidth()
    return position/(scrWidthCm*.5)

def cm2norm_y(position, window):
    pix=cm2pix(position,window.monitor)
    return pix2norm_y(pix, window)

def deg2norm_x(position, window):
    pix=deg2pix(position, window.monitor)
    return pix2norm_x(pix, window)

def deg2norm_y(position, window):
    pix=deg2pix(position, window.monitor)
    return pix2norm_y(pix, window)

def pix2norm_x(position, window):
    scrSizePix = window.size
    return position/(scrSizePix[0]*.5)

def pix2norm_y(position, window):
    scrSizePix = window.size
    return position/(scrSizePix[1]*.5)

def norm2cm_x(position, window):
    scrWidthCm=window.monitor.getWidth()*.5
    return position*scrWidthCm

def norm2cm_y(position, window):
    scrHeightCm=window.monitor.getHeight()*.5
    return position*scrHeightCm

def norm2deg_x(position, window):
    pix=norm2pix_x(position, window)
    return pix2deg(pix, window.monitor)

def norm2deg_y(position, window):
    pix=norm2pix_y(position, window)
    return pix2deg(pix, window.monitor)

def norm2pix_x(position, window):
    scrSizePix = window.size
    return position*scrSizePix[0]*.5

def norm2pix_y(position, window):
    scrSizePix = window.size
    return position*scrSizePix[1]*.5

def convert_position(position, from_units, to_units, window):
    if from_units=='cm':
        if to_units=='deg':
            return (cm2deg(position[0],window.monitor),cm2deg(position[1],window.monitor))
        elif to_units=='norm':
            return (cm2norm_x(position[0],window),cm2norm_y(position[1],window))
        elif to_units=='pix':
            return (cm2pix(position[0],window.monitor),cm2pix(position[1],window.monitor))
    elif from_units=='deg':
        rad=position[0]
        if to_units=='cm':
            return (deg2cm(position[0],window.monitor),deg2cm(position[1],window.monitor))
        elif to_units=='norm':
            return (deg2norm_x(position[0],window), deg2norm_y(position[1],window))
        elif to_units=='pix':
            return (deg2pix(position[0],window.monitor),deg2pix(position[1],window.monitor))
    elif from_units=='pix':
        if to_units=='cm':
            return (pix2cm(position[0], window.monitor), pix2cm(position[1], window.monitor))
        elif to_units=='deg':
            return (pix2deg(position[0], window.monitor),pix2deg(position[1],window.monitor))
        elif to_units=='norm':
            return (pix2norm_x(position[0], window), pix2norm_y(position[1],window))
    elif from_units=='norm':
        if to_units=='cm':
            return (norm2cm_x(position[0], window), norm2cm_y(position[1],window))
        elif to_units=='deg':
            return (norm2deg_x(position[0], window), norm2deg_y(position[1],window))
        elif to_units=='pix':
            return (norm2pix_x(position[0], window), norm2pix_y(position[1], window))
    return position

def convert_size(size, from_units, to_units, window):
    if from_units=='cm':
        if to_units=='deg':
            return cm2deg(size, window.monitor)
        elif to_units=='norm':
            return cm2norm_x(size, window)
        elif to_units=='pix':
            return cm2pix(size, window.monitor)
    elif from_units=='deg':
        if to_units=='cm':
            return deg2cm(size, window.monitor)
        elif to_units=='norm':
            return deg2norm_x(size, window)
        elif to_units=='pix':
            return deg2pix(size, window.monitor)
    elif from_units=='norm':
        if to_units=='cm':
            return norm2cm_x(size, window)
        elif to_units=='deg':
            return norm2deg_x(size, window)
        elif to_units=='pix':
            return norm2pix_x(size, window)
    elif from_units=='pix':
        if to_units=='cm':
            return pix2cm(size, window.monitor)
        elif to_units=='deg':
            return pix2deg(size, window.monitor)
        elif to_units=='norm':
            return pix2norm_x(size, window)
    return size

def getCamelCase(s, sep=' '):
    s=s.replace('_',' ')
    return ' '.join([t.title() for t in s.split(sep)])

def convert_color_to_qt(color_tuple):
    return ((color_tuple[0]+1)/2, (color_tuple[1]+1)/2, (color_tuple[2]+1)/2)

def convert_color_to_psychopy(color_tuple):
    return (color_tuple[0]*2-1,color_tuple[1]*2-1,color_tuple[2]*2-1)



