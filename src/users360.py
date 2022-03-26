# %%
import os
from head_motion_prediction.Utils import *
from abc import abstractmethod
from enum import Enum, auto
from plotly.subplots import make_subplots
from scipy.spatial import SphericalVoronoi, geometric_slerp
from scipy.stats import entropy
from spherical_geometry import polygon
from typing import Tuple, Iterable
from abc import ABC
import math
import numpy as np
from numpy import ndarray
from os.path import exists
import pickle
import plotly
import plotly.express as px
import plotly.graph_objs as go
import scipy.stats

ONE_USER = '0'
ONE_VIDEO = '10_Cows'
LAYOUT = go.Layout(width=600)
TILES_H6, TILES_V4 = 6, 4
TRINITY_NPATCHS = 14


def layout_with_title(title):
    return go.Layout(width=800, title=title)


def points_voro(npatchs) -> SphericalVoronoi:
    points = np.empty((0, 3))
    for i in range(0, npatchs):
        zi = (1 - 1.0/npatchs) * (1 - 2.0*i / (npatchs - 1))
        di = math.sqrt(1 - math.pow(zi, 2))
        alphai = i * math.pi * (3 - math.sqrt(5))
        xi = di * math.cos(alphai)
        yi = di * math.sin(alphai)
        new_point = np.array([[xi, yi, zi]])
        points = np.append(points, new_point, axis=0)
    sv = SphericalVoronoi(points, 1, np.array([0, 0, 0]))
    sv.sort_vertices_of_regions()
    return sv


VORONOI_14P = points_voro(TRINITY_NPATCHS)
VORONOI_24P = points_voro(24)


def points_rect_tile_cartesian(i, j, t_hor, t_vert) -> Tuple[ndarray, ndarray]:
    d_hor = np.deg2rad(360/t_hor)
    d_vert = np.deg2rad(180/t_vert)
    theta_c = d_hor * (j + 0.5)
    phi_c = d_vert * (i + 0.5)
    polygon_rect_tile = np.array([
        eulerian_to_cartesian(d_hor * j, d_vert * (i+1)),
        eulerian_to_cartesian(d_hor * (j+1), d_vert * (i+1)),
        eulerian_to_cartesian(d_hor * (j+1), d_vert * i),
        eulerian_to_cartesian(d_hor * j, d_vert * i)])
    return polygon_rect_tile, eulerian_to_cartesian(theta_c, phi_c)


def points_fov_cartesian(trace) -> ndarray:
    # https://daglar-cizmeci.com/how-does-virtual-reality-work/
    margin_lateral = np.deg2rad(90/2)
    margin_ab = np.deg2rad(110/2)
    theta_vp, phi_vp = cartesian_to_eulerian(*trace)
    polygon_fov = np.array([
        eulerian_to_cartesian(theta_vp+margin_lateral, phi_vp-margin_ab),
        eulerian_to_cartesian(theta_vp+margin_lateral, phi_vp+margin_ab),
        eulerian_to_cartesian(theta_vp-margin_lateral, phi_vp+margin_ab),
        eulerian_to_cartesian(theta_vp-margin_lateral, phi_vp-margin_ab)])
    return polygon_fov


class Dataset:
    sample_dataset = None
    sample_dataset_pickle = 'users360.pickle'

    def __init__(self, dataset=None):
        if dataset is None:
            self.dataset = self._get_sample_dataset()
            self.users_id = [key for key in self.dataset.keys()]

    # -- dataset funcs

    def _get_sample_dataset(self, load=False):
        if Dataset.sample_dataset is None:
            if load or not exists(Dataset.sample_dataset_pickle):
                project_path = "head_motion_prediction"
                cwd = os.getcwd()
                print(cwd)
                if os.path.basename(cwd) != project_path:
                    print(f"Dataset.sample_dataset from {project_path}")
                    os.chdir(project_path)
                    import head_motion_prediction.David_MMSys_18.Read_Dataset as david
                    Dataset.sample_dataset = david.load_sampled_dataset()
                    os.chdir(cwd)
                    with open(Dataset.sample_dataset_pickle, 'wb') as f:
                        pickle.dump(Dataset.sample_dataset, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                print(f"Dataset.sample_dataset from {Dataset.sample_dataset_pickle}")
                with open(Dataset.sample_dataset_pickle, 'rb') as f:
                    Dataset.sample_dataset = pickle.load(f)
        return Dataset.sample_dataset

    # -- cluster funcs

    def get_cluster_entropy_by_vpextract(self, vp=None):
        if vp is None:
            vp = VPExtractTilesRect(6, 4, cover=VPExtract.Cover.CENTER)
        users_entropy = np.ndarray(len(self.users_id))
        # fill users_entropy
        for index, user in enumerate(self.users_id[:1]):
            heatmaps = []
            for trace in self.dataset[user][ONE_VIDEO][:, 1:]:
                heatmap, _, _ = vp.request(trace)
                heatmaps.append(heatmap)
            sum = np.sum(heatmaps, axis=0).reshape((-1))
            print(sum)
            # https://stackoverflow.com/questions/15450192/fastest-way-to-compute-entropy-in-python
            users_entropy[index] = scipy.stats.entropy(sum)
            # print(users_entropy[index])
        # define class threshold
        # https://www.askpython.com/python/normal-distribution
        # https://matthew-brett.github.io/teaching/random_fields.html
        return users_entropy

    def get_one_trace(self) -> ndarray:
        return self.dataset[ONE_USER][ONE_VIDEO][:, 1:][:1]

    def get_traces_one_video_one_user(self) -> ndarray:
        return self.dataset[ONE_USER][ONE_VIDEO][:, 1:]

    def get_traces_one_video_all_users(self) -> ndarray:
        n_traces = len(self.dataset[ONE_USER][ONE_VIDEO][:, 1:])
        traces = np.ndarray((len(self.dataset.keys())*n_traces, 3))
        count = 0
        for user in self.dataset.keys():
            for trace in self.dataset[user][ONE_VIDEO][:, 1:]:
                traces.itemset((count, 0), trace[0])
                traces.itemset((count, 1), trace[1])
                traces.itemset((count, 2), trace[2])
                count += 1
        return traces

    def get_traces_random_one_user(self, num) -> ndarray:
        one_user = self.get_traces_one_video_one_user()
        step = int(len(one_user)/num)
        return one_user[::step]


class VPExtract(ABC):
    class Cover(Enum):
        ANY = auto()
        CENTER = auto()
        ONLY20PERC = auto()
        ONLY33PERC = auto()

    @abstractmethod
    def request(self, trace) -> tuple[ndarray, float, list]:
        pass

    @property
    def title(self):
        pass

    def title_with_sum_heatmaps(self, heatmaps):
        reqs_sum = np.sum(np.sum(heatmaps, axis=0))
        return f"{self.title} (reqs={reqs_sum})"

    cover: Cover
    shape: tuple[float, float]


class VPExtractTilesRect(VPExtract):
    def __init__(self, t_hor, t_vert, cover: VPExtract.Cover):
        self.t_hor, self.t_vert = t_hor, t_vert
        self.cover = cover
        self.shape = (self.t_vert, self.t_hor)

    @property
    def title(self):
        prefix = f'vpextract_rect{self.t_hor}x{self.t_vert}'
        match self.cover:
            case VPExtract.Cover.ANY:
                return f'{prefix}_any'
            case VPExtract.Cover.CENTER:
                return f'{prefix}_center'
            case VPExtract.Cover.ONLY20PERC:
                return f'{prefix}_20perc'
            case VPExtract.Cover.ONLY33PERC:
                return f'{prefix}_33perc'

    def request(self, trace):
        match self.cover:
            case VPExtract.Cover.CENTER:
                return self._request_110radius_center(trace)
            case VPExtract.Cover.ANY:
                return self._request_min_cover(trace, 0.0)
            case VPExtract.Cover.ONLY20PERC:
                return self._request_min_cover(trace, 0.2)
            case VPExtract.Cover.ONLY33PERC:
                return self._request_min_cover(trace, 0.33)

    def _request_min_cover(self, trace, required_cover: float):
        heatmap = np.zeros((self.t_vert, self.t_hor), dtype=np.int32)
        areas_in = []
        vp_quality = 0.0
        vp_threshold = np.deg2rad(110/2)
        for i in range(self.t_vert):
            for j in range(self.t_hor):
                rect_tile_points, tile_center = points_rect_tile_cartesian(i, j, self.t_hor, self.t_vert)
                dist = compute_orthodromic_distance(trace, tile_center)
                if dist <= vp_threshold:
                    rect_tile_polygon = polygon.SphericalPolygon(rect_tile_points)
                    fov_polygon = polygon.SphericalPolygon(points_fov_cartesian(trace))
                    view_area = rect_tile_polygon.overlap(fov_polygon)
                    if view_area > required_cover:
                        heatmap[i][j] = 1
                        areas_in.append(view_area)
                        vp_quality += fov_polygon.overlap(rect_tile_polygon)
        return heatmap, vp_quality, areas_in

    def _request_110radius_center(self, trace):
        heatmap = np.zeros((self.t_vert, self.t_hor), dtype=np.int32)
        vp_110_rad_half = np.deg2rad(110/2)
        areas_in = []
        vp_quality = 0.0
        for i in range(self.t_vert):
            for j in range(self.t_hor):
                rect_tile_points, tile_center = points_rect_tile_cartesian(i, j, self.t_hor, self.t_vert)
                dist = compute_orthodromic_distance(trace, tile_center)
                if dist <= vp_110_rad_half:
                    heatmap[i][j] = 1
                    rect_tile_polygon = polygon.SphericalPolygon(rect_tile_points)
                    fov_polygon = polygon.SphericalPolygon(points_fov_cartesian(trace))
                    view_area = rect_tile_polygon.overlap(fov_polygon)
                    areas_in.append(view_area)
                    vp_quality += fov_polygon.overlap(rect_tile_polygon)
        return heatmap, vp_quality, areas_in


class VPExtractTilesVoro(VPExtract):
    def __init__(self, sphere_voro: SphericalVoronoi, cover: VPExtract.Cover):
        self.sphere_voro = sphere_voro
        self.cover = cover
        self.shape = (len(sphere_voro.points)//6, -1)

    @property
    def title(self):
        prefix = f'vpextract_voro{len(self.sphere_voro.points)}'
        match self.cover:
            case VPExtract.Cover.ANY:
                return f'{prefix}_any'
            case VPExtract.Cover.CENTER:
                return f'{prefix}_center'
            case VPExtract.Cover.ONLY20PERC:
                return f'{prefix}_20perc'
            case VPExtract.Cover.ONLY33PERC:
                return f'{prefix}_33perc'

    def request(self, trace):
        match self.cover:
            case VPExtract.Cover.CENTER:
                return self._request_110radius_center(trace)
            case VPExtract.Cover.ANY:
                return self._request_min_cover(trace, 0)
            case VPExtract.Cover.ONLY20PERC:
                return self._request_min_cover(trace, 0.2)
            case VPExtract.Cover.ONLY33PERC:
                return self._request_min_cover(trace, 0.33)

    def _request_110radius_center(self, trace):
        vp_110_rad_half = np.deg2rad(110/2)
        areas_in = []
        vp_quality = 0.0
        heatmap = np.zeros(len(self.sphere_voro.regions))
        for index, region in enumerate(self.sphere_voro.regions):
            dist = compute_orthodromic_distance(trace, self.sphere_voro.points[index])
            if dist <= vp_110_rad_half:
                heatmap[index] += 1
                voro_tile_polygon = polygon.SphericalPolygon(self.sphere_voro.vertices[region])
                fov_polygon = polygon.SphericalPolygon(points_fov_cartesian(trace))
                view_area = voro_tile_polygon.overlap(fov_polygon)
                areas_in.append(view_area)
                vp_quality += fov_polygon.overlap(voro_tile_polygon)
        return heatmap, vp_quality, areas_in

    def _request_min_cover(self, trace, required_cover: float):
        areas_in = []
        vp_quality = 0.0
        heatmap = np.zeros(len(self.sphere_voro.regions))
        for index, region in enumerate(self.sphere_voro.regions):
            voro_tile_polygon = polygon.SphericalPolygon(self.sphere_voro.vertices[region])
            fov_polygon = polygon.SphericalPolygon(points_fov_cartesian(trace))
            view_area = voro_tile_polygon.overlap(fov_polygon)
            if view_area > required_cover:
                heatmap[index] += 1
                # view_area = 1 if view_area > 1 else view_area  # fixed with compute_orthodromic_distance
                areas_in.append(view_area)
                vp_quality += fov_polygon.overlap(voro_tile_polygon)
        return heatmap, vp_quality, areas_in


VPEXTRACTS_VORO = [
    VPExtractTilesVoro(VORONOI_14P, VPExtract.Cover.CENTER),
    VPExtractTilesVoro(VORONOI_24P, VPExtract.Cover.CENTER),
    VPExtractTilesVoro(VORONOI_14P, VPExtract.Cover.ANY),
    VPExtractTilesVoro(VORONOI_24P, VPExtract.Cover.ANY),
    VPExtractTilesVoro(VORONOI_14P, VPExtract.Cover.ONLY20PERC),
    VPExtractTilesVoro(VORONOI_24P, VPExtract.Cover.ONLY20PERC),
    VPExtractTilesVoro(VORONOI_14P, VPExtract.Cover.ONLY33PERC),
    VPExtractTilesVoro(VORONOI_24P, VPExtract.Cover.ONLY33PERC),
]
VPEXTRACTS_RECT = [
    VPExtractTilesRect(6, 4, VPExtract.Cover.CENTER),
    VPExtractTilesRect(6, 4, VPExtract.Cover.ONLY33PERC),
    VPExtractTilesRect(6, 4, VPExtract.Cover.ONLY20PERC),
]

VPEXTRACT_METHODS = [*VPEXTRACTS_VORO, *VPEXTRACTS_RECT]


class Plot:
    def __init__(self, traces: ndarray, title_sufix=""):
        assert traces.shape[1] == 3  # check if cartesian
        self.traces = traces
        self.title = f"{str(len(traces))}_traces{title_sufix}"
        print("Dataset.traces.shape is " + str(traces.shape))

    # -- sphere funcs

    def _sphere_data_surface(self):
        theta = np.linspace(0, 2*np.pi, 100)
        phi = np.linspace(0, np.pi, 100)
        x = np.outer(np.cos(theta), np.sin(phi))*0.98
        y = np.outer(np.sin(theta), np.sin(phi))*0.98
        z = np.outer(np.ones(100), np.cos(phi))*0.98
        # https://community.plotly.com/t/3d-surface-bug-a-custom-colorscale-defined-with-rgba-values-ignores-the-alpha-specification/30809
        colorscale = [[0, "rgba(200, 0, 0, 0.1)"], [1.0, "rgba(255, 0, 0, 0.1)"]]
        return go.Surface(x=x, y=y, z=z, colorscale=colorscale, showlegend=False, showscale=False)

    def _sphere_data_voro(self, sphere_voro: SphericalVoronoi, with_generators=False):
        data = [self._sphere_data_surface()]
        # generator points
        if with_generators:
            gens = go.Scatter3d(x=sphere_voro.points[:, 0], y=sphere_voro.points[:, 1], z=sphere_voro.points[:, 2],
                                mode='markers', marker={'size': 1, 'opacity': 1.0, 'color': 'blue'}, name='voron center')
            data.append(gens)
        # edges
        for region in sphere_voro.regions:
            n = len(region)
            t = np.linspace(0, 1, 100)
            for i in range(n):
                start = sphere_voro.vertices[region][i]
                end = sphere_voro.vertices[region][(i + 1) % n]
                result = np.array(geometric_slerp(start, end, t))
                edge = go.Scatter3d(x=result[..., 0], y=result[..., 1], z=result[..., 2], mode='lines', line={
                                    'width': 5, 'color': 'black'}, name='region edge', showlegend=False)
                data.append(edge)
        return data

    def _sphere_data_add_user(self, data):
        trajc = go.Scatter3d(x=self.traces[:, 0],
                             y=self.traces[:, 1],
                             z=self.traces[:, 2],
                             mode='lines', line={'width': 1, 'color': 'blue'}, name='trajectory', showlegend=False)
        data.append(trajc)

    def _sphere_data_rect_tiles(self, t_hor, t_vert):
        data = [self._sphere_data_surface()]
        for i in range(t_hor+1):
            for j in range(t_vert+1):
                # -- add rect tiles edges
                rect_tile_points, _ = points_rect_tile_cartesian(i, j, t_hor, t_vert)
                n = len(rect_tile_points)
                t = np.linspace(0, 1, 100)
                for index in range(n):
                    start = rect_tile_points[index]
                    end = rect_tile_points[(index + 1) % n]
                    result = np.array(geometric_slerp(start, end, t))
                    edge = go.Scatter3d(x=result[..., 0], y=result[..., 1], z=result[..., 2], mode='lines', line={
                        'width': 5, 'color': 'black'}, name='region edge', showlegend=False)
                    data.append(edge)
        return data

    def sphere_voro_matplot(self, sphere_voro: SphericalVoronoi = VORONOI_14P, with_generators=False):
        import matplotlib.pyplot as plt
        fig = plt.figure()
        fig.set_size_inches(18.5, 10.5)
        u, v = np.mgrid[0: 2 * np.pi: 20j, 0: np.pi: 10j]
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_surface(np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v), alpha=0.1, color="r")
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        t_vals = np.linspace(0, 1, 2000)
        # generator points
        if with_generators:
            ax.scatter(sphere_voro.points[:, 0], sphere_voro.points[:, 1], sphere_voro.points[:, 2], c='b')
            ax.scatter(sphere_voro.vertices[:, 0], sphere_voro.vertices[:, 1], sphere_voro.vertices[:, 2], c='g')
        # edges
        for region in sphere_voro.regions:
            n = len(region)
            for i in range(n):
                start = sphere_voro.vertices[region][i]
                end = sphere_voro.vertices[region][(i + 1) % n]
                result = geometric_slerp(start, end, t_vals)
                ax.plot(result[..., 0],
                        result[..., 1],
                        result[..., 2],
                        c='k')
        # trajectory = get_traces_one_video_one_user()
        ax.plot(self.traces[:, 0], self.traces[:, 1], self.traces[:, 2], label='parametric curve')
        plt.show()

    def sphere_rect(self, t_hor, t_vert, to_html=False):
        data = self._sphere_data_rect_tiles(t_hor, t_vert)
        self._sphere_data_add_user(data)
        title = f"{self.title} rect{t_hor}x{t_vert}"
        fig = go.Figure(data=data, layout=layout_with_title(title))
        if to_html:
            plotly.offline.plot(fig, filename=f'./plot_figs/{title}.html', auto_open=False)
        else:
            fig.show()

    def sphere_voro(self, sphere_voro: SphericalVoronoi, to_html=False):
        data = self._sphere_data_voro(sphere_voro)
        self._sphere_data_add_user(data)
        title = f"{self.title} voro{len(sphere_voro.points)}"
        fig = go.Figure(data=data, layout=layout_with_title(title))
        if to_html:
            plotly.offline.plot(fig, filename=f'./plot_figs/{title}.html', auto_open=False)
        else:
            fig.show()

    def sphere_voro_with_vp(self, vpextract: VPExtractTilesVoro, to_html=False):
        data = self._sphere_data_voro(vpextract.sphere_voro)
        for trace in [self.traces[0]]:
            fov_polygon = points_fov_cartesian(trace)
            n = len(fov_polygon)
            t = np.linspace(0, 1, 100)
            for index in range(n):
                start = fov_polygon[index]
                end = fov_polygon[(index + 1) % n]
                result = np.array(geometric_slerp(start, end, t))
                edge = go.Scatter3d(x=result[..., 0], y=result[..., 1], z=result[..., 2], mode='lines', line={
                    'width': 5, 'color': 'blue'}, name='vp edge', showlegend=False)
                data.append(edge)
        heatmap, _, _ = vpextract.request(self.traces[0])
        title = f"{self.title} {vpextract.title_with_sum_heatmaps([heatmap])}"
        fig = go.Figure(data=data, layout=layout_with_title(title))
        if to_html:
            plotly.offline.plot(fig, filename=f'./plot_figs/{title}.html', auto_open=False)
        else:
            fig.show()

    def sphere_rect_with_vp(self, vpextract: VPExtractTilesRect, to_html=False):
        t_hor, t_vert = vpextract.shape
        data = self._sphere_data_rect_tiles(t_hor, t_vert)
        for trace in [self.traces[0]]:
            fov_polygon = points_fov_cartesian(trace)
            n = len(fov_polygon)
            t = np.linspace(0, 1, 100)
            for index in range(n):
                start = fov_polygon[index]
                end = fov_polygon[(index + 1) % n]
                result = np.array(geometric_slerp(start, end, t))
                edge = go.Scatter3d(x=result[..., 0], y=result[..., 1], z=result[..., 2], mode='lines', line={
                    'width': 5, 'color': 'blue'}, name='vp edge', showlegend=False)
                data.append(edge)
        heatmap, _, _ = vpextract.request(self.traces[0])
        title = f"{self.title} {vpextract.title_with_sum_heatmaps([heatmap])}"
        fig = go.Figure(data=data, layout=layout_with_title(title))
        if to_html:
            plotly.offline.plot(fig, filename=f'./plot_figs/{title}.html', auto_open=False)
        else:
            fig.show()

    # -- erp funcs

    def erp_heatmap(self, vpextract: VPExtract, to_html=False):
        heatmaps = []
        for trace in self.traces:
            heatmap, _, _,  = vpextract.request(trace)
            heatmaps.append(heatmap)
        fig = px.imshow(np.sum(heatmaps, axis=0), labels=dict(
            x="longitude", y="latitude", color="requests"))
        title = f"{self.title} {vpextract.title_with_sum_heatmaps(heatmaps)}"
        fig.update_layout(layout_with_title(title))
        if to_html:
            plotly.offline.plot(fig, filename=f'./plot_figs/{title}.html', auto_open=False)
        else:
            fig.show()

    # -- vpextract funcs

    def metrics_vpextract(self, vpextract_l: Iterable[VPExtract], plot_bars=True,
                          plot_traces=False, plot_heatmaps=False):
        fig_reqs = go.Figure(layout=LAYOUT)
        fig_areas = go.Figure(layout=LAYOUT)
        fig_quality = go.Figure(layout=LAYOUT)
        vpextract_n_reqs = []
        vpextract_avg_area = []
        vpextract_quality = []
        for vpextract in vpextract_l:
            traces_n_reqs = []
            traces_areas = []
            traces_areas_svg = []
            traces_heatmaps = []
            traces_vp_quality = []
            # call func per trace
            for trace in self.traces:
                heatmap_in, quality_in, areas_in = vpextract.request(trace)
                traces_n_reqs.append(np.sum(heatmap_in))
                traces_heatmaps.append(heatmap_in)
                traces_areas.append(areas_in)
                traces_areas_svg.append(np.average(areas_in))
                traces_vp_quality.append(quality_in)
            # line reqs
            fig_reqs.add_trace(go.Scatter(y=traces_n_reqs, mode='lines', name=f"{vpextract.title}"))
            # line areas
            fig_areas.add_trace(go.Scatter(y=traces_areas_svg, mode='lines', name=f"{vpextract.title}"))
            # line quality
            fig_quality.add_trace(go.Scatter(y=traces_vp_quality, mode='lines', name=f"{vpextract.title}"))
            # heatmap
            if(plot_heatmaps and len(traces_heatmaps)):
                fig_heatmap = px.imshow(
                    np.sum(traces_heatmaps, axis=0).reshape(vpextract.shape),
                    title=f"{vpextract.title_with_sum_heatmaps(traces_heatmaps)}",
                    labels=dict(x="longitude", y="latitude", color="VP_Extracts"))
                fig_heatmap.update_layout(LAYOUT)
                fig_heatmap.show()
            # sum
            vpextract_n_reqs.append(np.sum(traces_n_reqs))
            vpextract_avg_area.append(np.average(traces_areas_svg))
            vpextract_quality.append(np.average(traces_vp_quality))

        # line fig reqs areas
        if(plot_traces):
            fig_reqs.update_layout(xaxis_title="user trace", title="req_tiles " + self.title).show()
            fig_areas.update_layout(xaxis_title="user trace",
                                    title="avg req_tiles view_ratio " + self.title).show()
            fig_quality.update_layout(xaxis_title="user trace", title="avg quality ratio " + self.title).show()

        # bar fig vpextract_n_reqs vpextract_avg_area
        vpextract_names = [str(vpextract.title) for vpextract in vpextract_l]
        fig_bar = make_subplots(rows=1, cols=4,  subplot_titles=(
            "req_tiles", "avg req_tiles view_ratio", "avg VP quality_ratio", "score=quality_ratio/(req_tiles*(1-view_ratio)))"), shared_yaxes=True)
        fig_bar.add_trace(go.Bar(y=vpextract_names, x=vpextract_n_reqs, orientation='h'), row=1, col=1)
        fig_bar.add_trace(go.Bar(y=vpextract_names, x=vpextract_avg_area, orientation='h'), row=1, col=2)
        fig_bar.add_trace(go.Bar(y=vpextract_names, x=vpextract_quality, orientation='h'), row=1, col=3)
        vpextract_score = [vpextract_quality[i] * (1 / (vpextract_n_reqs[i] * (1 - vpextract_avg_area[i])))
                           for i, _ in enumerate(vpextract_n_reqs)]
        fig_bar.add_trace(go.Bar(y=vpextract_names, x=vpextract_score, orientation='h'), row=1, col=4)
        fig_bar.update_layout(width=1500, showlegend=False, title_text=self.title)
        fig_bar.update_layout(barmode="stack")
        if(plot_bars):
            fig_bar.show()

# %%