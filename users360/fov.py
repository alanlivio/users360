from head_motion_prediction.Utils import *
from spherical_geometry import polygon
import numpy as np
from numpy.typing import NDArray
from .data import *

X1Y0Z0 = np.array([1, 0, 0])
HOR_DIST = degrees_to_radian(110)
HOR_MARGIN = degrees_to_radian(110 / 2)
VER_MARGIN = degrees_to_radian(90 / 2)
_fov_x1y0z0_points = None
_fov_x1y0z0_area = None


def fov_x1y0z0_points() -> NDArray:
    global _fov_x1y0z0_points
    if _fov_x1y0z0_points is None:
        fov_x1y0z0_fov_points_euler = np.array([
            eulerian_in_range(-HOR_MARGIN, VER_MARGIN),
            eulerian_in_range(HOR_MARGIN, VER_MARGIN),
            eulerian_in_range(HOR_MARGIN, -VER_MARGIN),
            eulerian_in_range(-HOR_MARGIN, -VER_MARGIN)
        ])
        _fov_x1y0z0_points = np.array([
            eulerian_to_cartesian(*fov_x1y0z0_fov_points_euler[0]),
            eulerian_to_cartesian(*fov_x1y0z0_fov_points_euler[1]),
            eulerian_to_cartesian(*fov_x1y0z0_fov_points_euler[2]),
            eulerian_to_cartesian(*fov_x1y0z0_fov_points_euler[3])
        ])
    return _fov_x1y0z0_points


def fov_x1y0z0_area():
    global _fov_x1y0z0_area
    if _fov_x1y0z0_area is None:
        _fov_x1y0z0_area = polygon.SphericalPolygon(fov_x1y0z0_points()).area()
    return _fov_x1y0z0_area


def fov_points(trace) -> NDArray:
    if Data.singleton().fov_points is None:
        Data.singleton().fov_points = {}
    if (trace[0], trace[1], trace[2]) not in Data.singleton().fov_points:
        rotation = rotationBetweenVectors(X1Y0Z0, np.array(trace))
        points = np.array([
            rotation.rotate(fov_x1y0z0_points()[0]),
            rotation.rotate(fov_x1y0z0_points()[1]),
            rotation.rotate(fov_x1y0z0_points()[2]),
            rotation.rotate(fov_x1y0z0_points()[3]),
        ])
        Data.singleton().fov_points[(trace[0], trace[1], trace[2])] = points
    return Data.singleton().fov_points[(trace[0], trace[1], trace[2])]


def fov_poly(trace) -> polygon.SphericalPolygon:
    if Data.singleton().fov_polys is None:
        Data.singleton().fov_polys = {}
    if (trace[0], trace[1], trace[2]) not in Data.singleton().fov_polys:
        points_trace = fov_points(trace)
        Data.singleton().fov_polys[(trace[0], trace[1], trace[2])] = polygon.SphericalPolygon(points_trace)
    return Data.singleton().fov_polys[(trace[0], trace[1], trace[2])]
