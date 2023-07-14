class SupportTicketV2TestCasesView(TestCase):
    # data store for support ticket v2 and resolutions

    def setUp(self) -> None:

        # self.support_url = reverse("support_ticket")
        self.support_url = "/participant/support_ticket/"
        self.resolutions_url = "/participant/ticket_resolution/"
        self.monkeypatch = MonkeyPatch()

        UserRole.objects.create(role_name="datahub_admin", id=1)
        UserRole.objects.create(role_name="datahub_team_member", id=2)
        UserRole.objects.create(role_name="datahub_participant_root", id=3)
        user = User.objects.create(
            email="jai+6@digitalgreen.org",
            first_name="jaibhatt",
            last_name="jaibhatt",
            role=UserRole.objects.get(role_name="datahub_participant_root"),
            phone_number="8696957626",
            profile_picture="sasas",
            subscription="aaaa",
        )
        # print(user.id)
        org = Organization.objects.create(
            org_email="jai+99@digitalgreen.org",
            name="jaidigitalgreen",
            phone_number="8696957627",
            website="website.com",
            address=json.dumps({"city": "Bangalore"}),
        )
        # Test model str class
        user_map = UserOrganizationMap.objects.create(
            user=User.objects.get(first_name="jaibhatt"),
            organization=Organization.objects.get(org_email="jai+99@digitalgreen.org"),
        )

        self.user_map_id = user_map.id
        sup_ticket = SupportTicketV2.objects.create(
            user_map=UserOrganizationMap.objects.get(id=user_map.id), **ticket_v2_dump_data
        )

        sup_ticket_2 = SupportTicketV2.objects.create(
            user_map=UserOrganizationMap.objects.get(id=user_map.id), **ticket_v2_dump_data
        )

        resolutions = Resolution.objects.create(
            ticket_id=sup_ticket.id,
            user_map_id=user_map.id,
            resolution_text="Some resolution",

        )
        self.resolutions_id = resolutions.id
        self.ticket_id = sup_ticket.id
        resolutions_v2_valid_data["ticket"] = sup_ticket_2.id

        refresh = RefreshToken.for_user(user)
        refresh["org_id"] = str(user_map.organization_id) if user_map else None
        refresh["map_id"] = str(user_map.id) if user_map else None
        refresh["role"] = str(user.role_id)
        refresh["onboarded_by"] = str(user.on_boarded_by_id)

        refresh.access_token["org_id"] = str(user_map.organization_id) if user_map else None
        refresh.access_token["map_id"] = str(user_map.id) if user_map else None
        refresh.access_token["role"] = str(user.role_id)
        refresh.access_token["onboarded_by"] = str(user.on_boarded_by_id)
        auth["token"] = refresh.access_token

        self.client = Client()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth["token"]}'
        }
        self.client.defaults['HTTP_AUTHORIZATION'] = headers['Authorization']
        self.client.defaults['CONTENT_TYPE'] = headers['Content-Type']

    def test_participant_support_ticket_v2_invalid_data(self):
        api_response = self.client.post(self.support_url, ticket_v2_invalid_data, secure=True,
                                        content_type='application/json')
        assert api_response.status_code == 400
        if api_response.json().get("status"):
            assert api_response.json().get("status")[0].replace('"',
                                                                '') == f"{ticket_v2_invalid_data['status']} is not a valid choice."

        if api_response.json().get("category"):
            assert api_response.json().get("category")[0].replace('"',
                                                                  '') == f"{ticket_v2_invalid_data['category']} is not a valid choice."

        if api_response.json().get("user_map"):
            assert api_response.json().get("user_map")[0].replace('“', '').replace('”',
                                                                                   '') == f"{ticket_v2_invalid_data['user_map']} is not a valid UUID."

    def test_participant_support_ticket_v2_update(self):
        api_response = self.client.put(f"{self.support_url}{self.ticket_id}/", ticket_v2_valid_data, secure=True,
                                       content_type='application/json')
        if api_response.status_code == 404:
            assert api_response.json().get("message") == "Not found ticket"

        assert api_response.status_code == 200

    def test_participant_support_ticket_v2_list(self):
        del list_filter_params["status"]
        del list_filter_params["category"]
        del list_filter_params["updated_at__range"]
        del list_filter_params["others"]
        api_response = self.client.post(f"{self.support_url}list_tickets/", list_filter_params, secure=True,
                                        content_type='application/json')

        assert api_response.status_code == 200
        assert type(api_response.json().get("results")) == list

    def test_participant_support_ticket_v2_retrieve(self):

        api_response = self.client.get(f"{self.support_url}{self.ticket_id}/", secure=True)
        if api_response.status_code == 404:
            assert api_response.json().get("message") == "No ticket found for this id."

        elif api_response.status_code == 200:
            assert type(api_response.json().get("ticket")) == dict
            assert type(api_response.json().get("resolutions")) == list
            assert type(api_response.json().get("logged_in_organization")) == dict

    ############################################ Resolutions ###########################################################

    def test_participant_resolution_invalid_data_create(self):
        print(resolutions_v2_valid_data)
        api_response = self.client.post(self.resolutions_url, resolutions_v2_invalid_data, secure=True,
                                        content_type='application/json')
        assert api_response.status_code == 404

    def test_participant_resolution_valid_data_create(self):
        print(resolutions_v2_valid_data)
        api_response = self.client.post(self.resolutions_url, resolutions_v2_valid_data, secure=True,
                                        content_type='application/json')
        assert api_response.status_code == 201

    def test_participant_resolution_update(self):
        api_response = self.client.put(f"{self.resolutions_url}{self.resolutions_id}/", resolutions_v2_update_data,
                                       secure=True,
                                       content_type='application/json')
        assert api_response.status_code == 200