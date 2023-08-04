import os
import time
import django
import unittest
import uuid
from django.conf import settings
from django.test.runner import DiscoverRunner
from testcontainers.postgres import PostgresContainer

class DockerizedTestRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start PostgreSQL container using testcontainers
        cls.postgres_container = PostgresContainer()
        cls.postgres_container.start()
        time.sleep(200)
        # Set up Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
        django.setup()

        # Dynamically update the database settings to use the PostgreSQL container
        db_host = cls.postgres_container.get_container_host_ip()
        db_port = cls.postgres_container.get_exposed_port(5432)
        db_name = 'mydatabase'  # Replace with your desired database name
        db_user = 'myuser'      # Replace with your desired database username
        db_password = 'mypassword'  # Replace with your desired database password

        settings.DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'
        settings.DATABASES['default']['HOST'] = db_host
        settings.DATABASES['default']['PORT'] = db_port
        settings.DATABASES['default']['NAME'] = db_name
        settings.DATABASES['default']['USER'] = db_user
        settings.DATABASES['default']['PASSWORD'] = db_password

    @classmethod
    def tearDownClass(cls):
        # Stop the PostgreSQL container
        cls.postgres_container.stop()

    def test_django_app(self):
        # Run the tests
        test_runner = DiscoverRunner()
        failures = test_runner.run_tests(['datahub'])
        self.assertFalse(failures)

if __name__ == '__main__':
    unittest.main()

