from users360 import *
import unittest
from numpy import ndarray


class User360Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dataset = Dataset.singleton()
        cls.one_user = Traces(cls.dataset.traces_one_video_one_user(), title_sufix="one_video_one_user")
        cls.all_users = Traces(cls.dataset.traces_one_video(), title_sufix="one_video_all_users")
        cls.some_users = Traces(cls.dataset.traces_random_one_user(4), title_sufix="some_users")
        cls.one_trace = Traces(cls.dataset.one_trace())

    def test_plot_traces_shape(self):
        self.assertIsNotNone(self.one_trace)
        self.assertIsInstance(self.one_user.traces, ndarray)
        self.assertIsNotNone(self.all_users)
        self.assertIsInstance(self.all_users.traces, ndarray)
        self.assertIsNotNone(self.some_users)
        self.assertIsInstance(self.some_users.traces, ndarray)
        self.assertIsNotNone(self.one_trace)
        self.assertIsInstance(self.one_trace.traces, ndarray)

    def test_plot_sphere(self):
        self.one_user.sphere(VPEXTRACT_RECT_6_4_CENTER, to_html=True)
        self.one_trace.sphere_show_one_trace_vp(VPEXTRACT_RECT_6_4_CENTER, to_html=True)
        self.some_users.metrics_vpextract(VPEXTRACTS_RECT, plot_bars=False,
                                          plot_traces=False, plot_heatmaps=False)

    def test_plot_shpere_voro(self):
        self.one_user.sphere(VPEXTRACT_VORO_14_CENTER, to_html=True)
        self.one_trace.sphere_show_one_trace_vp(VPEXTRACT_VORO_14_CENTER, to_html=True)
        self.some_users.metrics_vpextract(VPEXTRACTS_VORO, plot_bars=False, plot_traces=False, plot_heatmaps=False)

    def test_plot_erp(self):
        self.one_user.erp_heatmap(VPEXTRACT_RECT_6_4_CENTER, to_html=True)

    def test_entropy(self):
        self.dataset.users_entropy(VPEXTRACT_RECT_6_4_CENTER)
        self.assertIsNotNone(self.dataset.users_low)
        self.assertIsNotNone(self.dataset.users_medium)
        self.assertIsNotNone(self.dataset.users_hight)


if __name__ == '__main__':
    unittest.main()
