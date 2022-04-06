from users360 import *
import unittest
from numpy import ndarray


class ProjectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dataset = Dataset.singleton()
        cls.some_traces = Projection(cls.dataset.traces_one_video_one_user_n(4), title_sufix="some_traces")
        cls.one_user = Projection(cls.dataset.traces_one_video_one_user(), title_sufix="one_video_one_user")
        cls.all_users = Projection(cls.dataset.traces_one_video_users(), title_sufix="one_video_all_users")
        cls.one_trace = Projection(cls.dataset.one_trace())

    def test_shape(self):
        self.assertIsNotNone(self.one_trace)
        self.assertIsInstance(self.one_user.traces, ndarray)
        self.assertIsNotNone(self.all_users)
        self.assertIsInstance(self.all_users.traces, ndarray)
        self.assertIsNotNone(self.some_traces)
        self.assertIsInstance(self.some_traces.traces, ndarray)
        self.assertIsNotNone(self.one_trace)
        self.assertIsInstance(self.one_trace.traces, ndarray)

    def test_sphere_rect(self):
        self.one_user.sphere(VPEXTRACT_RECT_6_4_CENTER, to_html=True)
        self.one_trace.sphere_vp_trace(VPEXTRACT_RECT_6_4_CENTER, to_html=True)
        # self.some_traces.metrics_vpextract_users(VPEXTRACTS_RECT, plot_bars=False, plot_traces=False, plot_heatmaps=False)

    def test_shpere_voro(self):
        self.one_user.sphere(VPEXTRACT_VORO_14_CENTER, to_html=True)
        self.one_trace.sphere_vp_trace(VPEXTRACT_VORO_14_CENTER, to_html=True)
        # self.some_traces.metrics_vpextract_users(VPEXTRACTS_VORO, plot_bars=False, plot_traces=False, plot_heatmaps=False)

    def test_erp(self):
        self.one_user.erp_heatmap(VPEXTRACT_RECT_6_4_CENTER, to_html=True)


if __name__ == '__main__':
    unittest.main()
