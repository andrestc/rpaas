# coding: utf-8

# Copyright 2016 rpaas authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import datetime
import unittest
import os

import freezegun

from rpaas import plan, storage, flavor


class MongoDBStorageTestCase(unittest.TestCase):

    def setUp(self):
        os.environ["MONGO_DATABASE"] = "storage_test"
        self.storage = storage.MongoDBStorage()
        colls = self.storage.db.collection_names(False)
        for coll in colls:
            self.storage.db.drop_collection(coll)
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
        self.storage.db[self.storage.flavors_collection].insert(
            {"_id": "vanilla",
             "description": "nginx 1.10",
             "config": {"nginx_version": "1.10"}}
        )
        self.storage.db[self.storage.flavors_collection].insert(
            {"_id": "orange",
             "description": "nginx 1.12",
             "config": {"nginx_version": "1.12"}}
        )

    def test_set_team_quota(self):
        q = self.storage.set_team_quota("myteam", 8)
        used, quota = self.storage.find_team_quota("myteam")
        self.assertEqual([], used)
        self.assertEqual(8, quota)
        self.assertEqual(used, q["used"])
        self.assertEqual(quota, q["quota"])

    def test_list_plans(self):
        plans = self.storage.list_plans()
        expected = [
            {"name": "small", "description": "some cool plan",
             "config": {"serviceofferingid": "abcdef123456"}},
            {"name": "huge", "description": "some cool huge plan",
             "config": {"serviceofferingid": "abcdef123459"}},
        ]
        self.assertEqual(expected, [p.to_dict() for p in plans])

    def test_find_plan(self):
        plan = self.storage.find_plan("small")
        expected = {"name": "small", "description": "some cool plan",
                    "config": {"serviceofferingid": "abcdef123456"}}
        self.assertEqual(expected, plan.to_dict())
        with self.assertRaises(storage.PlanNotFoundError):
            self.storage.find_plan("something that doesn't exist")

    def test_store_plan(self):
        p = plan.Plan(name="super_huge", description="very huge thing",
                      config={"serviceofferingid": "abcdef123"})
        self.storage.store_plan(p)
        got_plan = self.storage.find_plan(p.name)
        self.assertEqual(p.to_dict(), got_plan.to_dict())

    def test_store_plan_duplicate(self):
        p = plan.Plan(name="small", description="small thing",
                      config={"serviceofferingid": "abcdef123"})
        with self.assertRaises(storage.DuplicateError):
            self.storage.store_plan(p)

    def test_update_plan(self):
        p = plan.Plan(name="super_huge", description="very huge thing",
                      config={"serviceofferingid": "abcdef123"})
        self.storage.store_plan(p)
        self.storage.update_plan(p.name, description="wat?",
                                 config={"serviceofferingid": "abcdef123459"})
        p = self.storage.find_plan(p.name)
        self.assertEqual("super_huge", p.name)
        self.assertEqual("wat?", p.description)
        self.assertEqual({"serviceofferingid": "abcdef123459"}, p.config)

    def test_update_plan_partial(self):
        p = plan.Plan(name="super_huge", description="very huge thing",
                      config={"serviceofferingid": "abcdef123"})
        self.storage.store_plan(p)
        self.storage.update_plan(p.name, config={"serviceofferingid": "abcdef123459"})
        p = self.storage.find_plan(p.name)
        self.assertEqual("super_huge", p.name)
        self.assertEqual("very huge thing", p.description)
        self.assertEqual({"serviceofferingid": "abcdef123459"}, p.config)

    def test_update_plan_not_found(self):
        with self.assertRaises(storage.PlanNotFoundError):
            self.storage.update_plan("my_plan", description="woot")

    def test_delete_plan(self):
        p = plan.Plan(name="super_huge", description="very huge thing",
                      config={"serviceofferingid": "abcdef123"})
        self.storage.store_plan(p)
        self.storage.delete_plan(p.name)
        with self.assertRaises(storage.PlanNotFoundError):
            self.storage.find_plan(p.name)

    def test_delete_plan_not_found(self):
        with self.assertRaises(storage.PlanNotFoundError):
            self.storage.delete_plan("super_huge")

    def test_list_flavors(self):
        flavors = self.storage.list_flavors()
        expected = [
            {"name": "vanilla", "description": "nginx 1.10",
             "config": {"nginx_version": "1.10"}},
            {"name": "orange", "description": "nginx 1.12",
             "config": {"nginx_version": "1.12"}},
        ]
        self.assertEqual(expected, [f.to_dict() for f in flavors])

    def test_find_flavor(self):
        flavor = self.storage.find_flavor("vanilla")
        expected = {"name": "vanilla", "description": "nginx 1.10",
                    "config": {"nginx_version": "1.10"}}
        self.assertEqual(expected, flavor.to_dict())
        with self.assertRaises(storage.FlavorNotFoundError):
            self.storage.find_flavor("something that doesn't exist")

    def test_store_flavor(self):
        f = flavor.Flavor(name="lemon", description="nginx 1.13",
                          config={"nginx_version": "1.13"})
        self.storage.store_flavor(f)
        got_flavor = self.storage.find_flavor(f.name)
        self.assertEqual(f.to_dict(), got_flavor.to_dict())

    def test_store_flavor_duplicate(self):
        f = flavor.Flavor(name="vanilla", description="nginx 1.10",
                          config={"nginx_version": "1.10"})
        with self.assertRaises(storage.DuplicateError):
            self.storage.store_flavor(f)

    def test_update_flavor(self):
        f = flavor.Flavor(name="lemon", description="nginx 1.13",
                          config={"nginx_version": "1.13"})
        self.storage.store_flavor(f)
        self.storage.update_flavor(f.name, description="nginx 1.13.1",
                                   config={"nginx_version": "1.13.1"})
        f = self.storage.find_flavor(f.name)
        self.assertEqual("lemon", f.name)
        self.assertEqual("nginx 1.13.1", f.description)
        self.assertEqual({"nginx_version": "1.13.1"}, f.config)

    def test_update_flavor_partial(self):
        f = flavor.Flavor(name="lemon", description="nginx 1.13",
                          config={"nginx_version": "1.13"})
        self.storage.store_flavor(f)
        self.storage.update_flavor(f.name, config={"nginx_version": "1.13.1"})
        f = self.storage.find_flavor(f.name)
        self.assertEqual("lemon", f.name)
        self.assertEqual("nginx 1.13", f.description)
        self.assertEqual({"nginx_version": "1.13.1"}, f.config)

    def test_update_flavor_not_found(self):
        with self.assertRaises(storage.FlavorNotFoundError):
            self.storage.update_flavor("lemon", description="nginx 1.13")

    def test_delete_flavor(self):
        f = flavor.Flavor(name="lemon", description="nginx 1.13",
                          config={"nginx_version": "1.13"})
        self.storage.store_flavor(f)
        self.storage.delete_flavor(f.name)
        with self.assertRaises(storage.FlavorNotFoundError):
            self.storage.find_flavor(f.name)

    def test_delete_flavor_not_found(self):
        with self.assertRaises(storage.FlavorNotFoundError):
            self.storage.delete_flavor("lemon")

    def test_instance_metadata_storage(self):
        self.storage.store_instance_metadata("myinstance", plan="small")
        inst_metadata = self.storage.find_instance_metadata("myinstance")
        self.assertEqual({"_id": "myinstance",
                          "plan": "small"}, inst_metadata)
        self.storage.store_instance_metadata("myinstance", plan="medium")
        inst_metadata = self.storage.find_instance_metadata("myinstance")
        self.assertEqual({"_id": "myinstance", "plan": "medium"}, inst_metadata)
        self.storage.remove_instance_metadata("myinstance")
        inst_metadata = self.storage.find_instance_metadata("myinstance")
        self.assertIsNone(inst_metadata)

    @freezegun.freeze_time("2014-12-23 10:53:00", tz_offset=2)
    def test_store_le_certificate(self):
        self.storage.store_le_certificate("myinstance", "docs.tsuru.io")
        coll = self.storage.db[self.storage.le_certificates_collection]
        item = coll.find_one({"_id": "myinstance"})
        expected = {"_id": "myinstance", "domain": "docs.tsuru.io",
                    "created": datetime.datetime(2014, 12, 23, 10, 53, 0)}
        self.assertEqual(expected, item)

    @freezegun.freeze_time("2014-12-23 10:53:00", tz_offset=2)
    def test_store_le_certificate_overwrite(self):
        self.storage.store_le_certificate("myinstance", "docs.tsuru.io")
        self.storage.store_le_certificate("myinstance", "docs.tsuru.com")
        coll = self.storage.db[self.storage.le_certificates_collection]
        item = coll.find_one({"_id": "myinstance"})
        expected = {"_id": "myinstance", "domain": "docs.tsuru.com",
                    "created": datetime.datetime(2014, 12, 23, 10, 53, 0)}
        self.assertEqual(expected, item)

    def test_remove_le_certificate(self):
        self.storage.store_le_certificate("myinstance", "docs.tsuru.io")
        self.storage.remove_le_certificate("myinstance", "docs.tsuru.io")
        coll = self.storage.db[self.storage.le_certificates_collection]
        item = coll.find_one({"_id": "myinstance"})
        self.assertIsNone(item)

    def test_remove_le_certificate_wrong_domain(self):
        self.storage.store_le_certificate("myinstance", "docs.tsuru.io")
        self.storage.remove_le_certificate("myinstance", "docs.tsuru.com")
        coll = self.storage.db[self.storage.le_certificates_collection]
        item = coll.find_one({"_id": "myinstance"})
        self.assertIsNotNone(item)

    def test_find_le_certificates(self):
        self.storage.store_le_certificate("myinstance", "docs.tsuru.io")
        self.storage.store_le_certificate("myinstance", "docs.tsuru.com")
        certs_domain = list(self.storage.find_le_certificates({"domain": "docs.tsuru.com"}))
        certs_name = list(self.storage.find_le_certificates({"name": "myinstance"}))
        self.assertEqual(certs_name, certs_domain)
        self.assertEqual("myinstance", certs_name[0]["name"])

    @freezegun.freeze_time("2016-08-02 10:53:00", tz_offset=2)
    def test_store_update_retrieve_healing(self):
        healing_id = self.storage.store_healing("myinstance", "10.10.1.1")
        loop_time = datetime.datetime.utcnow()
        for x in range(2, 5):
            loop_time = loop_time + datetime.timedelta(minutes=5)
            with freezegun.freeze_time(loop_time, tz_offset=2):
                healing_tmp = self.storage.store_healing("myinstance", "10.10.1.{}".format(x))
                self.storage.update_healing(healing_tmp, "success")
        coll = self.storage.db[self.storage.healing_collection]
        item = coll.find_one({"_id": healing_id})
        expected = {"_id": healing_id, "instance": "myinstance", "machine": "10.10.1.1",
                    "start_time": datetime.datetime(2016, 8, 2, 10, 53, 0)}
        self.assertDictEqual(item, expected)
        with freezegun.freeze_time("2016-08-02 10:55:00", tz_offset=2):
            self.storage.update_healing(healing_id, "some random reason")
            item = coll.find_one({"_id": healing_id})
            expected = {"_id": healing_id, "instance": "myinstance", "machine": "10.10.1.1",
                        "start_time": datetime.datetime(2016, 8, 2, 10, 53, 0),
                        "end_time": datetime.datetime(2016, 8, 2, 10, 55, 0),
                        "status": "some random reason"}
            self.assertDictEqual(item, expected)
        loop_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        expected = []
        for x in range(2, 5):
            expected.append({"instance": "myinstance", "machine": "10.10.1.{}".format(x),
                             "start_time": loop_time, "end_time": loop_time, "status": "success"})
            loop_time = loop_time + datetime.timedelta(minutes=5)
        expected.reverse()
        healing_list = self.storage.list_healings(3)
        self.assertListEqual(healing_list, expected)
