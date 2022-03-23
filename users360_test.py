from users360 import *
import unittest


class User360Test(unittest.TestCase):
    def test_one_user(self):
        one_user = Plot(Dataset().get_traces_one_video_one_user(), title_sufix="one_video_one_user")
        self.assertIsNotNone(one_user)
        one_user.plot_sphere_voro(VORONOI_14P, to_html=True)
        one_user.plot_sphere_voro(VORONOI_24P, to_html=True)
        one_user.plot_sphere_rectan(6, 4, to_html=True)

    def test_entropy(self):
        users_entropy = Dataset().get_cluster_entropy_by_vpextract()
        self.assertIsNotNone(users_entropy)

    def test_all_users(self):
        all_users = Plot(Dataset().get_traces_one_video_all_users(), title_sufix="one_video_all_users")
        self.assertIsNotNone(all_users)
        all_users.plot_sphere_voro(VORONOI_24P,  to_html=True)
        all_users.plot_sphere_rectan(6, 4, to_html=True)

    def test_one_trace(self):
        one_trace = Plot(Dataset().get_one_trace())
        self.assertIsNotNone(one_trace)
        one_trace.plot_sphere_rectan_with_vp(6, 4, to_html=True)
        one_trace.plot_sphere_rectan_with_vp(4, 4, to_html=True)
        one_trace.plot_sphere_voro_with_vp(VORONOI_24P, to_html=True)

    def test_plot_per_fov(self):
        some_users = Plot(Dataset().get_traces_random_one_user(4), verbose=True)
        some_users.plot_reqs_per_func(VPEXTRACT_METHODS, plot_bars=False, plot_lines=False, plot_heatmaps=False)


if __name__ == '__main__':
    unittest.main()
