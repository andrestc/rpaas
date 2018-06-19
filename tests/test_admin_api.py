# Copyright 2016 rpaas authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import datetime
import json
import unittest
import os

from bson import json_util
from rpaas import api, storage, admin_api
from . import managers


class AdminAPITestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["MONGO_DATABASE"] = "api_admin_test"
        cls.storage = storage.MongoDBStorage()
        cls.manager = managers.FakeManager(storage=cls.storage)
        api.get_manager = lambda: cls.manager
        admin_api.get_manager = lambda: cls.manager
        cls.api = api.api.test_client()

    def setUp(self):
        self.manager.reset()
        colls = self.storage.db.collection_names(False)
        for coll in colls:
            self.storage.db.drop_collection(coll)

    def test_list_healings(self):
        resp = self.api.get("/admin/healings")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("[]", resp.data)
        loop_time = datetime.datetime(2016, 8, 2, 10, 53, 0)
        healing_list = []
        for x in range(1, 30):
            data = {"instance": "myinstance", "machine": "10.10.1.{}".format(x),
                    "start_time": loop_time, "end_time": loop_time, "status": "success"}
            healing_list.append(json.loads(json.dumps(data, default=json_util.default)))
            self.storage.db[self.storage.healing_collection].insert(data)
            loop_time = loop_time + datetime.timedelta(minutes=5)
        healing_list.reverse()
        resp = self.api.get("/admin/healings")
        self.assertEqual(200, resp.status_code)
        self.assertListEqual(healing_list[:20], json.loads(resp.data))
        resp = self.api.get("/admin/healings?quantity=10")
        self.assertEqual(200, resp.status_code)
        self.assertListEqual(healing_list[:10], json.loads(resp.data))
        resp = self.api.get("/admin/healings?quantity=aaaa")
        self.assertEqual(200, resp.status_code)
        self.assertListEqual(healing_list[:20], json.loads(resp.data))

    def test_list_plans(self):
        resp = self.api.get("/admin/plans")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("[]", resp.data)
        self.storage.db[self.storage.plans_collection].insert(
            {"_id": "small",
             "description": "some cool plan",
             "config": {"serviceofferingid": "abcdef123456"}}
        )
        self.storage.db[self.storage.plans_collection].insert(
            {"_id": "huge",
             "description": "some cool huge plan",
             "config": {"serviceofferingid": "abcdef123459"}}
        )
        resp = self.api.get("/resources/plans")
        self.assertEqual(200, resp.status_code)
        expected = [
            {"name": "small", "description": "some cool plan",
             "config": {"serviceofferingid": "abcdef123456"}},
            {"name": "huge", "description": "some cool huge plan",
             "config": {"serviceofferingid": "abcdef123459"}},
        ]
        self.assertEqual(expected, json.loads(resp.data))

    def test_create_plan(self):
        config = json.dumps({
            "serviceofferingid": "abcdef1234",
            "NAME": "super",
        })
        resp = self.api.post("/admin/plans", data={"name": "small",
                                                   "description": "small instance",
                                                   "config": config})
        self.assertEqual(201, resp.status_code)
        plan = self.storage.find_plan("small")
        self.assertEqual("small", plan.name)
        self.assertEqual("small instance", plan.description)
        self.assertEqual(json.loads(config), plan.config)

    def test_create_plan_duplicate(self):
        self.storage.db[self.storage.plans_collection].insert(
            {"_id": "small",
             "description": "some cool plan",
             "config": {"serviceofferingid": "abcdef123456"}}
        )
        config = json.dumps({
            "serviceofferingid": "abcdef1234",
            "NAME": "super",
        })
        resp = self.api.post("/admin/plans", data={"name": "small",
                                                   "description": "small instance",
                                                   "config": config})
        self.assertEqual(409, resp.status_code)

    def test_create_plan_invalid(self):
        config = json.dumps({
            "serviceofferingid": "abcdef1234",
            "NAME": "super",
        })
        resp = self.api.post("/admin/plans", data={"description": "small instance",
                                                   "config": config})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("invalid plan - name is required", resp.data)
        resp = self.api.post("/admin/plans", data={"name": "small",
                                                   "config": config})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("invalid plan - description is required", resp.data)
        resp = self.api.post("/admin/plans", data={"name": "small",
                                                   "description": "something small"})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("invalid plan - config is required", resp.data)

    def test_retrieve_plan(self):
        self.storage.db[self.storage.plans_collection].insert(
            {"_id": "small",
             "description": "some cool plan",
             "config": {"serviceofferingid": "abcdef123456"}}
        )
        plan = self.storage.find_plan("small")
        resp = self.api.get("/admin/plans/small")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(plan.to_dict(), json.loads(resp.data))

    def test_retrieve_plan_not_found(self):
        resp = self.api.get("/admin/plans/small")
        self.assertEqual(404, resp.status_code)
        self.assertEqual("plan not found", resp.data)

    def test_update_plan(self):
        self.storage.db[self.storage.plans_collection].insert(
            {"_id": "small",
             "description": "some cool plan",
             "config": {"serviceofferingid": "abcdef123456"}}
        )
        config = json.dumps({
            "serviceofferingid": "abcdef1234",
            "NAME": "super",
        })
        resp = self.api.put("/admin/plans/small", data={"description": "small instance",
                                                        "config": config})
        self.assertEqual(200, resp.status_code)
        plan = self.storage.find_plan("small")
        self.assertEqual("small", plan.name)
        self.assertEqual("small instance", plan.description)
        self.assertEqual(json.loads(config), plan.config)

    def test_update_plan_partial(self):
        self.storage.db[self.storage.plans_collection].insert(
            {"_id": "small",
             "description": "some cool plan",
             "config": {"serviceofferingid": "abcdef123456"}}
        )
        config = json.dumps({
            "serviceofferingid": "abcdef1234",
            "NAME": "super",
        })
        resp = self.api.put("/admin/plans/small", data={"config": config})
        self.assertEqual(200, resp.status_code)
        plan = self.storage.find_plan("small")
        self.assertEqual("small", plan.name)
        self.assertEqual("some cool plan", plan.description)
        self.assertEqual(json.loads(config), plan.config)

    def test_update_plan_not_found(self):
        config = json.dumps({
            "serviceofferingid": "abcdef1234",
            "NAME": "super",
        })
        resp = self.api.put("/admin/plans/small", data={"description": "small instance",
                                                        "config": config})
        self.assertEqual(404, resp.status_code)
        self.assertEqual("plan not found", resp.data)

    def test_delete_plan(self):
        self.storage.db[self.storage.plans_collection].insert(
            {"_id": "small",
             "description": "some cool plan",
             "config": {"serviceofferingid": "abcdef123456"}}
        )
        resp = self.api.delete("/admin/plans/small")
        self.assertEqual(200, resp.status_code)
        with self.assertRaises(storage.PlanNotFoundError):
            self.storage.find_plan("small")

    def test_delete_plan_not_found(self):
        resp = self.api.delete("/admin/plans/small")
        self.assertEqual(404, resp.status_code)
        self.assertEqual("plan not found", resp.data)

    def test_list_flavors(self):
        resp = self.api.get("/admin/flavors")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("[]", resp.data)
        self.storage.db[self.storage.flavors_collection].insert(
            {"_id": "orange",
             "description": "nginx 1.12",
             "config": {"nginx_version": "1.12"}}
        )
        self.storage.db[self.storage.flavors_collection].insert(
            {"_id": "vanilla",
             "description": "nginx 1.10",
             "config": {"nginx_version": "1.10"}}
        )
        resp = self.api.get("/resources/flavors")
        self.assertEqual(200, resp.status_code)
        expected = [
            {"name": "orange", "description": "nginx 1.12",
             "config": {"nginx_version": "1.12"}},
            {"name": "vanilla", "description": "nginx 1.10",
             "config": {"nginx_version": "1.10"}},
        ]
        self.assertEqual(expected, json.loads(resp.data))

    def test_create_flavor(self):
        config = json.dumps({
            "nginx_version": "1.12",
            "extra_config": "dsr",
        })
        resp = self.api.post("/admin/flavors", data={"name": "nginx_dsr",
                                                     "description": "nginx 1.12 + dsr",
                                                     "config": config})
        self.assertEqual(201, resp.status_code)
        flavor = self.storage.find_flavor("nginx_dsr")
        self.assertEqual("nginx_dsr", flavor.name)
        self.assertEqual("nginx 1.12 + dsr", flavor.description)
        self.assertEqual(json.loads(config), flavor.config)

    def test_create_flavor_duplicate(self):
        self.storage.db[self.storage.flavors_collection].insert(
            {"_id": "orange",
             "description": "nginx 1.12",
             "config": {"nginx_version": "1.12"}}
        )
        config = json.dumps({
            "nginx_version": "1.10"
        })
        resp = self.api.post("/admin/flavors", data={"name": "orange",
                                                     "description": "nginx 1.10",
                                                     "config": config})
        self.assertEqual(409, resp.status_code)

    def test_create_flavor_invalid(self):
        config = json.dumps({
            "nginx_version": "1.10"
        })
        resp = self.api.post("/admin/flavors", data={"description": "nginx 1.10",
                                                     "config": config})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("invalid rpaas flavor - name is required", resp.data)
        resp = self.api.post("/admin/flavors", data={"name": "orange",
                                                     "config": config})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("invalid rpaas flavor - description is required", resp.data)
        resp = self.api.post("/admin/flavors", data={"name": "orange",
                                                     "description": "nginx 1.10"})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("invalid rpaas flavor - config is required", resp.data)

    def test_retrieve_flavor(self):
        self.storage.db[self.storage.flavors_collection].insert(
            {"_id": "orange",
             "description": "nginx 1.10",
             "config": {"nginx_version": "1.10"}}
        )
        flavor = self.storage.find_flavor("orange")
        resp = self.api.get("/admin/flavors/orange")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(flavor.to_dict(), json.loads(resp.data))

    def test_retrieve_flavor_not_found(self):
        resp = self.api.get("/admin/flavors/vanilla")
        self.assertEqual(404, resp.status_code)
        self.assertEqual("flavor not found", resp.data)

    def test_update_flavor(self):
        self.storage.db[self.storage.flavors_collection].insert(
            {"_id": "orange",
             "description": "nginx 1.10",
             "config": {"nginx_version": "1.10"}}
        )
        config = json.dumps({
            "nginx_version": "1.10.1",
            "dsr": "true",
        })
        resp = self.api.put("/admin/flavors/orange", data={"description": "nginx 1.10",
                                                           "config": config})
        self.assertEqual(200, resp.status_code)
        flavor = self.storage.find_flavor("orange")
        self.assertEqual("orange", flavor.name)
        self.assertEqual("nginx 1.10", flavor.description)
        self.assertEqual(json.loads(config), flavor.config)

    def test_update_flavor_not_found(self):
        config = json.dumps({
            "nginx_version": "1.10"
        })
        resp = self.api.put("/admin/flavors/vanilla", data={"description": "nginx 1.10",
                                                            "config": config})
        self.assertEqual(404, resp.status_code)
        self.assertEqual("flavor not found", resp.data)

    def test_delete_flavor(self):
        self.storage.db[self.storage.flavors_collection].insert(
            {"_id": "vanilla",
             "description": "nginx version 1.10",
             "config": {"nginx_version": "1.10"}}
        )
        resp = self.api.delete("/admin/flavors/vanilla")
        self.assertEqual(200, resp.status_code)
        with self.assertRaises(storage.FlavorNotFoundError):
            self.storage.find_flavor("vanilla")

    def test_delete_flavor_not_found(self):
        resp = self.api.delete("/admin/flavors/vanilla")
        self.assertEqual(404, resp.status_code)
        self.assertEqual("flavor not found", resp.data)

    def test_view_team_quota(self):
        self.storage.db[self.storage.quota_collection].insert(
            {"_id": "myteam",
             "used": ["inst1", "inst2"],
             "quota": 10}
        )
        resp = self.api.get("/admin/quota/myteam")
        self.assertEqual(200, resp.status_code)
        self.assertEqual({"used": ["inst1", "inst2"], "quota": 10},
                         json.loads(resp.data))
        resp = self.api.get("/admin/quota/yourteam")
        self.assertEqual(200, resp.status_code)
        self.assertEqual({"used": [], "quota": 5}, json.loads(resp.data))

    def test_set_team_quota(self):
        self.storage.db[self.storage.quota_collection].insert(
            {"_id": "myteam",
             "used": ["inst1", "inst2"],
             "quota": 10}
        )
        resp = self.api.post("/admin/quota/myteam", data={"quota": 12})
        self.assertEqual(200, resp.status_code)
        used, quota = self.storage.find_team_quota("myteam")
        self.assertEqual(["inst1", "inst2"], used)
        self.assertEqual(12, quota)
        resp = self.api.post("/admin/quota/yourteam", data={"quota": 3})
        self.assertEqual(200, resp.status_code)
        used, quota = self.storage.find_team_quota("yourteam")
        self.assertEqual([], used)
        self.assertEqual(3, quota)

    def test_set_team_quota_invalid_value(self):
        resp = self.api.post("/admin/quota/myteam", data={})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("quota must be an integer value greather than 0", resp.data)
        resp = self.api.post("/admin/quota/myteam", data={"quota": "abc"})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("quota must be an integer value greather than 0", resp.data)
        resp = self.api.post("/admin/quota/myteam", data={"quota": "0"})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("quota must be an integer value greather than 0", resp.data)
        resp = self.api.post("/admin/quota/myteam", data={"quota": "-3"})
        self.assertEqual(400, resp.status_code)
        self.assertEqual("quota must be an integer value greather than 0", resp.data)

    def test_restore_instance_successfully(self):
        resp = self.api.post("/admin/restore", data={"instance_name": "blah"})
        self.assertEqual(200, resp.status_code)
        response = ["host a restored", "host b restored"]
        self.assertEqual("".join(response), resp.data)

    def test_restore_invalid_instance_name(self):
        resp = self.api.post("/admin/restore", data={"instance_name": "invalid"})
        self.assertEqual(200, resp.status_code)
        self.assertEqual("instance invalid not found", resp.data)

    def test_restore_instance_error_on_restore(self):
        resp = self.api.post("/admin/restore", data={"instance_name": "error"})
        self.assertEqual(200, resp.status_code)
        response = ["host a restored", "host b restored", "host c failed to restore"]
        self.assertEqual("".join(response), resp.data)
