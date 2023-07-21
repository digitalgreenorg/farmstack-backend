# import pytest
# from django.test import SimpleTestCase
# from django.urls import resolve, reverse
#
#
# class TestUrls(SimpleTestCase):
#     def test_datasetv2_list(self):
#         """Unit test cases for Dataset V2 URLs"""
#         url = reverse("dataset/v2-list")
#         print("List View URL", url, resolve(url)._func_path)
#         assert resolve(url)._func_path == "datahub.views.DatasetV2ViewSet"
