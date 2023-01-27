from pytest_factoryboy import register
from datahub.tests.tests_v2.factories import UserRoleFactory, UserFactory, OrganizationFactory, UserMapFactory,  DatasetV2Factory

register(UserRoleFactory)
register(UserFactory)
register(OrganizationFactory)
register(UserMapFactory)
register(DatasetV2Factory)
