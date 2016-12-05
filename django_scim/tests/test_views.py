import json
from unittest import skip

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import Client
from django.test import RequestFactory
from django.utils.six.moves.urllib.parse import urljoin

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from django_scim import views
from django_scim.constants import BASE_SCIM_LOCATION
from django_scim.constants import BASE_URL
from django_scim.models import SCIMServiceProviderConfig
from django_scim.schemas import ALL as ALL_SCHEMAS
from django_scim.utils import get_group_adapter
from django_scim.utils import get_group_model
from django_scim.utils import get_user_adapter


class SCIMTestCase(TestCase):
    maxDiff = None
    factory = RequestFactory()

    @skip('')
    def test_dispatch(self):
        self.fail('TODO')

    def test_status_501(self):
        request = self.factory.get('/noop')

        class Status501View(views.SCIMView):
            implemented = False

        resp = Status501View.as_view()(request)
        self.assertEqual(resp.status_code, 501)

    @skip('')
    def test_auth_request(self):
        self.fail('TODO')


class FilterMixinTestCase(TestCase):
    maxDiff = None
    factory = RequestFactory()

    def test__page(self):
        request = self.factory.get('/noop?startIndex=11&count=23')
        start, count = views.FilterMixin()._page(request)

        self.assertEqual(start, 11)
        self.assertEqual(count, 23)

    @skip('')
    def test__search(self):
        self.fail('TODO')

    def test__build_response(self):
        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford',
            username='rford',
        )
        ford = get_user_adapter()(ford)
        abernathy = get_user_model().objects.create(
            first_name='Dolores',
            last_name='Abernathy',
            username='dabernathy',
        )
        abernathy = get_user_adapter()(abernathy)

        qs = get_user_model().objects.all()
        mixin = views.FilterMixin()
        mixin.scim_adapter = get_user_adapter()
        resp = mixin._build_response(qs, 1, 5)

        result = json.loads(resp.content)
        expected = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 2,
            "itemsPerPage": 5,
            "startIndex": 1,
            'Resources': [
                ford.to_dict(),
                abernathy.to_dict(),
            ],
        }
        self.assertEqual(expected, result)


class SearchTestCase(TestCase):
    maxDiff = None

    def test_search_without_schema(self):
        """
        Test POST /Users/.search/?filter=userName eq ""
        """
        c = Client()
        url = reverse('scim:users-search')
        body = json.dumps({
            'schemas': ['urn:ietf:params:scim:api:messages:2.0:NotSearchRequest'],
        })
        resp = c.post(url, body, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 400, resp.content)

        result = json.loads(resp.content)
        expected = {
            'detail': u'Invalid schema uri. Must be SearchRequest.',
            'schemas': [u'urn:ietf:params:scim:api:messages:2.0:Error'],
            'status': 400
        }
        self.assertEqual(expected, result)

    def test_search_for_user_with_username_filter(self):
        """
        Test POST /Users/.search/?filter=userName eq ""
        """
        c = Client()
        url = reverse('scim:users-search')
        body = json.dumps({
            'schemas': ['urn:ietf:params:scim:api:messages:2.0:SearchRequest'],
            'filter': 'userName eq ""',
        })
        resp = c.post(url, body, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)
        location = urljoin(BASE_SCIM_LOCATION, BASE_URL)
        location = urljoin(location, 'Users/.search')
        self.assertEqual(resp['Location'], location)

        result = json.loads(resp.content)
        expected = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 0,
            "itemsPerPage": 50,
            "startIndex": 1,
            "Resources": [],
        }
        self.assertEqual(expected, result)


class UserTestCase(TestCase):
    maxDiff = None

    def test_get_user_with_username_filter(self):
        """
        Test GET /Users?filter=userName eq ""
        """
        c = Client()
        url = reverse('scim:users') + '?filter=userName eq ""'
        resp = c.get(url, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)

        result = json.loads(resp.content)
        expected = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 0,
            "itemsPerPage": 50,
            "startIndex": 1,
            "Resources": [],
        }
        self.assertEqual(expected, result)

    def test_get_user_by_id(self):
        """
        Test GET /Users/{id}
        """
        # create user
        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford'
        )
        ford = get_user_adapter()(ford)

        c = Client()
        url = reverse('scim:users', kwargs={'uuid': ford.id})
        resp = c.get(url, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp['Location'], ford.location)

        result = json.loads(resp.content)
        expected = ford.to_dict()
        self.assertEqual(expected, result)

    def test_get_all_users(self):
        """
        Test GET /Users
        """
        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford',
            username='rford',
        )
        ford = get_user_adapter()(ford)
        abernathy = get_user_model().objects.create(
            first_name='Dolores',
            last_name='Abernathy',
            username='dabernathy',
        )
        abernathy = get_user_adapter()(abernathy)

        c = Client()
        url = reverse('scim:users')
        resp = c.get(url, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)

        result = json.loads(resp.content)
        expected = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 2,
            "itemsPerPage": 50,
            "startIndex": 1,
            'Resources': [
                ford.to_dict(),
                abernathy.to_dict(),
            ],
        }
        self.assertEqual(expected, result)

    def test_post(self):
        c = Client()
        url = reverse('scim:users')
        data = {
            'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'],
            'userName': 'ehughes',
            'name': {
                'givenName': 'Elsie',
                'familyName': 'Hughes',
            },
            'password': 'notTooSecret',
            'emails': [{'value': 'ehughes@westworld.com', 'primary': True}],
        }
        body = json.dumps(data)
        resp = c.post(url, body, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 201, resp.content)

        # test object
        elsie = get_user_model().objects.get(username='ehughes')
        self.assertEqual(elsie.first_name, 'Elsie')
        self.assertEqual(elsie.last_name, 'Hughes')
        self.assertEqual(elsie.email, 'ehughes@westworld.com')

        # test response
        elsie = get_user_adapter()(elsie)
        result = json.loads(resp.content)
        self.assertEqual(result, elsie.to_dict())
        self.assertEqual(resp['Location'], elsie.location)

    def test_put(self):
        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford',
            username='rford',
            email='rford@ww.com',
        )

        c = Client()
        url = reverse('scim:users', kwargs={'uuid': ford.id})
        data = get_user_adapter()(ford).to_dict()
        data['userName'] = 'updatedrford'
        data['name'] = {'givenName': 'Bobby'}
        data['emails'] = [{'value': 'rford@westworld.com', 'primary': True}]
        body = json.dumps(data)
        resp = c.put(url, body, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)

        # test object
        ford.refresh_from_db()
        self.assertEqual(ford.first_name, 'Bobby')
        self.assertEqual(ford.last_name, '')
        self.assertEqual(ford.username, 'updatedrford')
        self.assertEqual(ford.email, 'rford@westworld.com')

        # test response
        result = json.loads(resp.content)
        ford = get_user_adapter()(ford)
        self.assertEqual(result, ford.to_dict())

    @skip('')
    def test_patch(self):
        self.fail('TODO')

    def test_delete(self):
        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford',
            username='rford',
            email='rford@ww.com',
        )

        c = Client()
        url = reverse('scim:users', kwargs={'uuid': ford.id})
        resp = c.delete(url)
        self.assertEqual(resp.status_code, 204, resp.content)

        ford = get_user_model().objects.filter(id=ford.id).first()
        self.assertIsNone(ford)


class GroupTestCase(TestCase):
    maxDiff = None

    def test_get_group_by_id(self):
        """
        Test GET /Group/{id}
        """
        behavior = get_group_model().objects.create(
            name='Behavior Group',
        )

        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford'
        )
        ford.groups.add(behavior)

        behavior = get_group_adapter()(behavior)

        c = Client()
        url = reverse('scim:groups', kwargs={'uuid': behavior.id})
        resp = c.get(url, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp['Location'], behavior.location)

        result = json.loads(resp.content)
        expected = behavior.to_dict()
        self.assertEqual(expected, result)

    def test_get_all_groups(self):
        """
        Test GET /Groups
        """
        behavior = get_group_model().objects.create(
            name='Behavior Group',
        )
        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford',
            username='rford',
        )
        ford.groups.add(behavior)
        behavior = get_group_adapter()(behavior)

        security = get_group_model().objects.create(
            name='Security Group',
        )
        abernathy = get_user_model().objects.create(
            first_name='Dolores',
            last_name='Abernathy',
            username='dabernathy',
        )
        abernathy.groups.add(security)
        security = get_group_adapter()(security)

        c = Client()
        url = reverse('scim:groups')
        resp = c.get(url, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)

        result = json.loads(resp.content)
        expected = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 2,
            "itemsPerPage": 50,
            "startIndex": 1,
            'Resources': [
                behavior.to_dict(),
                security.to_dict(),
            ],
        }
        self.assertEqual(expected, result)

    def test_post(self):
        c = Client()
        url = reverse('scim:groups')
        data = {
            'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'],
            'displayName': 'Behavior Group',
        }
        body = json.dumps(data)
        resp = c.post(url, body, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 201, resp.content)

        # test object exists
        behavior = get_group_model().objects.get(name='Behavior Group')

        # test response
        behavior = get_group_adapter()(behavior)
        result = json.loads(resp.content)
        self.assertEqual(result, behavior.to_dict())
        self.assertEqual(resp['Location'], behavior.location)

    def test_put(self):
        behavior = get_group_model().objects.create(
            name='Behavior Group',
        )
        c = Client()
        url = reverse('scim:groups', kwargs={'uuid': behavior.id})
        data = get_group_adapter()(behavior).to_dict()
        data['displayName'] = 'Better Behavior Group'
        body = json.dumps(data)
        resp = c.put(url, body, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)

        # test object
        behavior.refresh_from_db()
        self.assertEqual(behavior.name, 'Better Behavior Group')

        # test response
        result = json.loads(resp.content)
        behavior = get_group_adapter()(behavior)
        self.assertEqual(result, behavior.to_dict())

    def test_patch_add(self):
        behavior = get_group_model().objects.create(
            name='Behavior Group',
        )
        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford',
            username='rford',
        )
        ford.groups.add(behavior)
        abernathy = get_user_model().objects.create(
            first_name='Dolores',
            last_name='Abernathy',
            username='dabernathy',
        )
        scim_abernathy = get_user_adapter()(abernathy)

        data = {
            'schemas': ['urn:ietf:params:scim:api:messages:2.0:PatchOp'],
            'Operations': [
                {
                    'op': 'add',
                    'path': 'members',
                    'value': [
                        {
                            'value': scim_abernathy.id
                        }
                    ]
                }
            ]
        }
        data = json.dumps(data)

        c = Client()
        url = reverse('scim:groups', kwargs={'uuid': behavior.id})
        resp = c.patch(url, data=data, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)

        result = json.loads(resp.content)
        expected = get_group_adapter()(behavior).to_dict()
        self.assertEqual(expected, result)

        self.assertEqual(behavior.user_set.count(), 2)

    def test_patch_remove(self):
        behavior = get_group_model().objects.create(
            name='Behavior Group',
        )
        ford = get_user_model().objects.create(
            first_name='Robert',
            last_name='Ford',
            username='rford',
        )
        ford.groups.add(behavior)
        abernathy = get_user_model().objects.create(
            first_name='Dolores',
            last_name='Abernathy',
            username='dabernathy',
        )
        abernathy.groups.add(behavior)
        scim_abernathy = get_user_adapter()(abernathy)

        data = {
            'schemas': ['urn:ietf:params:scim:api:messages:2.0:PatchOp'],
            'Operations': [
                {
                    'op': 'remove',
                    'path': 'members',
                    'value': [
                        {
                            'value': ford.id
                        },
                        {
                            'value': abernathy.id
                        },
                    ]
                }
            ]
        }
        data = json.dumps(data)

        c = Client()
        url = reverse('scim:groups', kwargs={'uuid': behavior.id})
        resp = c.patch(url, data=data, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)

        result = json.loads(resp.content)
        expected = get_group_adapter()(behavior).to_dict()
        self.assertEqual(expected, result)

        self.assertEqual(behavior.user_set.count(), 0)

    def test_patch_replace(self):
        behavior = get_group_model().objects.create(
            name='Behavior Group',
        )

        data = {
            'schemas': ['urn:ietf:params:scim:api:messages:2.0:PatchOp'],
            'Operations': [
                {
                    'op': 'replace',
                    'path': 'name',
                    'value': [
                        {
                            'value': 'Way better Behavior Group Name'
                        }
                    ]
                }
            ]
        }
        data = json.dumps(data)

        c = Client()
        url = reverse('scim:groups', kwargs={'uuid': behavior.id})
        resp = c.patch(url, data=data, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 200, resp.content)

        behavior.refresh_from_db()

        result = json.loads(resp.content)
        expected = get_group_adapter()(behavior).to_dict()
        self.assertEqual(expected, result)

        self.assertEqual(behavior.name, 'Way better Behavior Group Name')

    def test_patch_atomic(self):
        behavior = get_group_model().objects.create(
            name='Behavior Group',
        )
        ids = list(get_user_model().objects.all().values_list('id', flat=True)) or [0]
        max_id = max(ids)

        data = {
            'schemas': ['urn:ietf:params:scim:api:messages:2.0:PatchOp'],
            'Operations': [
                {
                    'op': 'replace',
                    'path': 'name',
                    'value': [
                        {
                            'value': 'Way better Behavior Group Name'
                        }
                    ]
                },
                # Adding a non-existent user should cause this PATCH to fail
                {
                    'op': 'add',
                    'path': 'members',
                    'value': [
                        {
                            'value': max_id + 1
                        }
                    ]
                }
            ]
        }
        data = json.dumps(data)

        c = Client()
        url = reverse('scim:groups', kwargs={'uuid': behavior.id})
        resp = c.patch(url, data=data, content_type='application/scim+json')
        self.assertEqual(resp.status_code, 400, resp.content)

        behavior.refresh_from_db()
        self.assertEqual(behavior.name, 'Behavior Group')

    def test_delete(self):
        behavior = get_group_model().objects.create(
            name='Behavior Group',
        )

        c = Client()
        url = reverse('scim:groups', kwargs={'uuid': behavior.id})
        resp = c.delete(url)
        self.assertEqual(resp.status_code, 204, resp.content)

        behavior = get_group_model().objects.filter(id=behavior.id).first()
        self.assertIsNone(behavior)


class ServiceProviderConfigTestCase(TestCase):
    maxDiff = None

    def test_get(self):
        c = Client()
        url = reverse('scim:service-provider-config')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        config = SCIMServiceProviderConfig()
        self.assertEqual(config.to_dict(), json.loads(resp.content))


class ResourceTypesTestCase(TestCase):
    maxDiff = None

    def test_get_all(self):
        c = Client()
        url = reverse('scim:resource-types')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        user_type = get_user_adapter().resource_type_dict()
        group_type = get_group_adapter().resource_type_dict()
        expected = list(sorted((user_type, group_type)))
        result = json.loads(resp.content)
        self.assertEqual(expected, result)

    def test_get_single(self):
        c = Client()
        url = reverse('scim:resource-types', kwargs={'uuid': 'User'})
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        expected = get_user_adapter().resource_type_dict()
        result = json.loads(resp.content)
        self.assertEqual(expected, result)


class SchemasTestCase(TestCase):
    maxDiff = None

    def test_get_all(self):
        c = Client()
        url = reverse('scim:schemas')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        expected = list(sorted(ALL_SCHEMAS))
        result = json.loads(resp.content)
        self.assertEqual(expected, result)

    def test_get_single(self):
        schemas_by_uri = {s['id']: s for s in ALL_SCHEMAS}

        c = Client()
        uuid = 'urn:ietf:params:scim:schemas:core:2.0:User'
        url = reverse('scim:schemas', kwargs={'uuid': uuid})
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        expected = schemas_by_uri[uuid]
        result = json.loads(resp.content)
        self.assertEqual(expected, result)

