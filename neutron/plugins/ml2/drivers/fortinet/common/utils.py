# Copyright 2015 Fortinet Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo.config import cfg
from neutron.agent.common import config
import re
import httplib
import sys
from neutron.plugins.ml2.drivers.fortinet.db import models as fortinet_db



OPS = ["ADD", "DELETE", "SET", "GET"]




class Base(object):
    def __init__(self):
        self.name = re.findall("[A-Z][^A-Z]*", self.__class__.__name__)
        self.name = "_" + "_".join(self.name).upper()
        self.exist = False

    @staticmethod
    def func_name():
        return sys._getframe(1).f_code.co_name

    def method(self, method):
        return str(method).upper() + self.name

    def is_exist(self, client, **kwargs):
        response = client.request(self.method("get"), kwargs)
        if httplib.OK == response["http_status"]:
            return True
        return False

    def sync2db(self, context, record):
        return

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class VdomLink(Base):
    pass

class RouterStatic(Base):
    def __enter__(self):
        pass

    def _check(self, client, record):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class Test(object):
    vdom_name = "Test class"


class FirewallPolicy(Base, Test):
    def __init__(self):
        super(FirewallPolicy, self).__init__()
        self.message = {
            "vdom": self.vdom_name,
            "srcintf": "any",
            "dstintf": "any",
            "srcaddr": "all",
            "dstaddr": "all"
        }
        self.a = self.vdom_name
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _firewall_policy(self, op, message):
        op = op.upper()
        if op not in OPS:
            raise "OP is invalid"
        op += self.name
        print op
        print self.func_name()
        pass

    def add_firewall_policy(self, message):
        op = op.upper()
        if op not in OPS:
            raise "OP is invalid"
        op += self.name
        print op
        print self.func_name()
        pass

if __name__ == "__main__":
    a = FirewallPolicy()
    a._firewall_policy("get", "test")
    print "FirewallPolicy.vdom_name=%s" % FirewallPolicy.vdom_name
    print "a.message=%s" % a.message
    print "a.a=%s" % a.a
    a.vdom_name = "test121"
    print "FirewallPolicy.vdom_name=%s" % FirewallPolicy.vdom_name
    print "a.message=%s" % a.message
    print "a.a=%s" % a.a

