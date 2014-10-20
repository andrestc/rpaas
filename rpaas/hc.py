# coding: utf-8
import json
import uuid

import requests
from requests import auth


class Dumb(object):

    def __init__(self, *args, **kwargs):
        self.hcs = {}

    def create(self, name):
        self.hcs[name] = []

    def destroy(self, name):
        if name in self.hcs:
            del self.hcs[name]

    def add_url(self, name, url):
        if name in self.hcs:
            self.hcs[name].append(url)

    def remove_url(self, name, url):
        if name in self.hcs:
            self.hcs[name].remove(url)


class HCAPI(object):

    def __init__(self, storage, url, user=None, password=None, hc_format=None):
        self.storage = storage
        self.url = url
        self.user = user
        self.password = password
        self.hc_format = hc_format

    def _issue_request(self, method, path, data=None):
        url = "/".join((self.url.rstrip("/"), path.lstrip("/")))
        kwargs = {"data": data}
        if self.user and self.password:
            kwargs["auth"] = auth.HTTPBasicAuth(self.user, self.password)
        return requests.request(method, url, **kwargs)

    def create(self, name):
        name = "rpaas_%s_%s" % (name, uuid.uuid4().hex)
        resp = self._issue_request("POST", "/resources", data={"name": name})
        if resp.status_code > 299:
            raise HCCreationError(resp.data)
        self.storage.store_hc({"name": name})

    def destroy(self, name):
        hc = self.storage.retrieve_hc(name)
        self._issue_request("DELETE", "/resources/" + hc["name"])
        self.storage.remove_hc(hc["name"])

    def add_url(self, name, url):
        hc = self.storage.retrieve_hc(name)
        if self.hc_format:
            url = self.hc_format.format(url)
        data = {"name": hc["name"], "url": url,
                "expected_string": "WORKING"}
        resp = self._issue_request("POST", "/url", data=json.dumps(data))
        if resp.status_code > 399:
            raise URLCreationError(resp.data)
        if "urls" not in hc:
            hc["urls"] = []
        hc["urls"].append(url)
        self.storage.store_hc(hc)

    def remove_url(self, name, url):
        hc = self.storage.retrieve_hc(name)
        if self.hc_format:
            url = self.hc_format.format(url)
        data = {"name": hc["name"], "url": url}
        self._issue_request("DELETE", "/url", data=json.dumps(data))
        hc["urls"].remove(url)
        self.storage.store_hc(hc)


class HCCreationError(Exception):
    pass


class URLCreationError(Exception):
    pass