from head_motion_prediction.Utils import *
import numpy as np
from abc import abstractmethod
from enum import Enum, auto
from spherical_geometry import polygon
from abc import ABC
import numpy as np
from numpy.typing import NDArray
from .fov import *
from .data import *


def _init_tileset(t_ver, t_hor):
    d_hor = degrees_to_radian(360 / t_hor)
    d_ver = degrees_to_radian(180 / t_ver)
    polys, centers = {}, {}
    for row in range(t_ver):
        polys[row], centers[row] = {}, {}
        for col in range(t_hor):
            points = tile_points(t_ver, t_hor, row, col)
            # sometimes tile points are same on poles
            # they need be unique otherwise it broke the SphericalPolygon.area
            _, idx = np.unique(points, axis=0, return_index=True)
            polys[row][col] = polygon.SphericalPolygon(points[np.sort(idx)])
            theta_c = d_hor * (col + 0.5)
            phi_c = d_ver * (row + 0.5)
            # at eulerian_to_cartesian: theta is hor and phi is ver
            centers[row][col] = eulerian_to_cartesian(theta_c, phi_c)
    Data.singleton().ts_polys[(t_ver, t_hor)] = polys
    Data.singleton().ts_centers[(t_ver, t_hor)] = centers


def tile_points(t_ver, t_hor, row, col) -> NDArray:
    d_ver = degrees_to_radian(180 / t_ver)
    d_hor = degrees_to_radian(360 / t_hor)
    assert (row < t_ver and col < t_hor)
    points = np.array([
        eulerian_to_cartesian(d_hor * col, d_ver * (row + 1)),
        eulerian_to_cartesian(d_hor * (col + 1), d_ver * (row + 1)),
        eulerian_to_cartesian(d_hor * (col + 1), d_ver * row),
        eulerian_to_cartesian(d_hor * col, d_ver * row),
    ])
    return points


def tile_poly(t_ver, t_hor, row, col):
    if (t_ver, t_hor) not in Data.singleton().ts_polys:
        _init_tileset(t_ver, t_hor)
    return Data.singleton().ts_polys[(t_ver, t_hor)][row][col]


def tile_center(t_ver, t_hor, row, col):
    if (t_ver, t_hor) not in Data.singleton().ts_polys:
        _init_tileset(t_ver, t_hor)
    return Data.singleton().ts_centers[(t_ver, t_hor)][row][col]


class TileCover(Enum):
    ANY = auto()
    CENTER = auto()
    ONLY20PERC = auto()
    ONLY33PERC = auto()


class TileSetIF(ABC):
    # https://realpython.com/python-interface/

    cover: TileCover
    shape: tuple[int, int]

    @abstractmethod
    def request(self, trace, return_metrics=False) -> NDArray | tuple[NDArray, float, list]:
        pass

    @property
    def title(self):
        match self.cover:
            case TileCover.ANY:
                return f'{self.prefix}_cov_any'
            case TileCover.CENTER:
                return f'{self.prefix}_cov_ctr'
            case TileCover.ONLY20PERC:
                return f'{self.prefix}_cov_20p'
            case TileCover.ONLY33PERC:
                return f'{self.prefix}_cov_33p'

    @property
    def prefix(self):
        pass

    def title_with_reqs(self, heatmaps):
        reqs_sum = np.sum(np.sum(heatmaps, axis=0))
        if isinstance(self, type(TileSet.default())):
            return f"(reqs={reqs_sum})"
        else:
            return f"({self.title} reqs={reqs_sum})"


class TileSet(TileSetIF):

    _default = None
    _variations = None

    def __init__(self, t_ver, t_hor, cover: TileCover):
        self.t_ver, self.t_hor = t_ver, t_hor
        self.shape = (self.t_ver, self.t_hor)
        self.cover = cover

    @classmethod
    def default(cls) -> TileSetIF:
        if cls._default is None:
            cls._default = TileSet(4, 6, TileCover.CENTER)
        return cls._default

    @classmethod
    def variations(cls):
        if cls._variations is None:
            cls._variations = [
                TileSet(4, 6, TileCover.CENTER),
                TileSet(4, 6, TileCover.ANY),
                TileSet(4, 6, TileCover.ONLY20PERC),
            ]
        return cls._variations

    @property
    def prefix(self):
        return f'tiles{self.t_ver}x{self.t_hor}'

    def request(self, trace: NDArray, return_metrics=False):
        match self.cover:
            case TileCover.CENTER:
                return self._request_110radius_center(trace, return_metrics)
            case TileCover.ANY:
                return self._request_min_cover(trace, 0.0, return_metrics)
            case TileCover.ONLY20PERC:
                return self._request_min_cover(trace, 0.2, return_metrics)
            case TileCover.ONLY33PERC:
                return self._request_min_cover(trace, 0.33, return_metrics)

    def _request_110radius_center(self, trace, return_metrics):
        heatmap = np.zeros((self.t_ver, self.t_hor), dtype=np.int32)
        areas_out = []
        vp_quality = 0.0
        fov_poly_trace = fov_poly(trace)
        for row in range(self.t_ver):
            for col in range(self.t_hor):
                dist = compute_orthodromic_distance(trace, tile_center(self.t_ver, self.t_hor, row, col))
                if dist <= HOR_MARGIN:
                    heatmap[row][col] = 1
                    if (return_metrics):
                        try:
                            poly_rc = tile_poly(self.t_ver, self.t_hor, row, col)
                            view_ratio = poly_rc.overlap(fov_poly_trace)
                        except:
                            print(f"request error for row,col,trace={row},{col},{repr(trace)}")
                            continue
                        areas_out.append(1 - view_ratio)
                        vp_quality += fov_poly_trace.overlap(poly_rc)
        if (return_metrics):
            return heatmap, vp_quality, np.sum(areas_out)
        else:
            return heatmap

    def _request_min_cover(self, trace: NDArray, required_cover: float, return_metrics):
        heatmap = np.zeros((self.t_ver, self.t_hor), dtype=np.int32)
        areas_out = []
        vp_quality = 0.0
        fov_poly_trace = fov_poly(trace)
        for row in range(self.t_ver):
            for col in range(self.t_hor):
                dist = compute_orthodromic_distance(trace, tile_center(self.t_ver, self.t_hor, row, col))
                if dist >= HOR_DIST:
                    continue
                try:
                    poly_rc = tile_poly(self.t_ver, self.t_hor, row, col)
                    view_ratio = poly_rc.overlap(fov_poly_trace)
                except:
                    print(f"request error for row,col,trace={row},{col},{repr(trace)}")
                    continue
                if view_ratio > required_cover:
                    heatmap[row][col] = 1
                    if (return_metrics):
                        areas_out.append(1 - view_ratio)
                        vp_quality += fov_poly_trace.overlap(poly_rc)
        if (return_metrics):
            return heatmap, vp_quality, np.sum(areas_out)
        else:
            return heatmap
