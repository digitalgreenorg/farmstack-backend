import os
import pytest
import uuid
from datahub.models import Organization

@pytest.fixture(scope="session", autouse="true")
def docker_compose_file(pytestconfig):
    return os.path.join(str(pytestconfig.rootdir), "mycustomdir", "docker-compose.yml")

def test_organization_model():
    org_obj = Organization(id=uuid.uuid4(), name="ugesh", email="test_gmail.com")
