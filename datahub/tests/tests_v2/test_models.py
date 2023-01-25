from django.test import TestCase
from model_bakery import baker
from accounts.models import User
from pprint import pprint

class UserTestModel(TestCase):
    """
    Class to test the model User
    """

    def setUp(self):
        self.user = baker.make(User)
        pprint(self.user.__dict__)
