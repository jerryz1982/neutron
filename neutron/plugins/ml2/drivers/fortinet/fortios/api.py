# Copyright 2015 Fortinet, Inc.
# All rights reserved.
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
#

from urllib import urlencode
from httplib2 import Http
from neutron.openstack.common import log as logging
import json

LOG = logging.getLogger(__name__)

class APIClient(object):
    def __init__(self, host, username = 'admin', password = ''):
        self.host = host
        self.username = username
        self.password = password

    def get_interface(self, interface):
        url




class Authentication(object):
    def __init__(self, host, username = 'admin', password = ''):
        self.url = "http://%s/logincheck" % host
        self.username = username
        self.password = password

    def _is_valid_url(self):
        pass

    def _is_auth_ok(self, response):
        LOG.debug(_("%s" % response['set-cookie'].split(';')))
        if 'APSCOOKIE_2630920337="0%260"'in response['set-cookie'].split(';'):
            LOG.error(_("Authentication failed, please check."))
            return False
        LOG.debug(_("The auth is successful"))
        return True

    def auth(self):
        params = urlencode({'username': self.username, 'secretkey': self.password})
        http = Http()
        response, content = http.request(self.url, 'POST', params)
        LOG.debug(_("%s" % response))
        if self._is_auth_ok(response):
            self.headers = {'Cookie': response['set-cookie']}
            return True
        return False

class Firewall(object):
    def __init__(self, ip, headers):
        self.url_fw_policy = "http://%s/api/v2/cmdb/firewall/policy/" % ip
        self.headers = headers
        self.fw_policies = {}

    def get_fw_policies(self, id = None):
        if id:
            self.url_fw_policy = "%s/%s" % (self.url_fw_policy, id)
        http = Http()
        response, content = http.request(self.url_fw_policy, 'GET',
                                         headers = self.headers)
        print content
        #print content, type(content)
        content = json.loads(content)
        if 200 != content['http_status']:
            logging.error("Fail to fetch firewall policies, please check.")
        for k in content:
            print k
        print content

        self.fw_policies
        #data = self.json2obj(content)
        #print data


if __name__ == "__main__":
    ip = "10.160.37.99"
    auth = Authentication(ip, 'admin', '')
    auth.auth()
    #print auth.headers
    fw = Firewall(ip, auth.headers)
    fw.get_fw_policies()
    #headers = {'Content-type': 'application/x-www-form-urlencoded'}
    #    print response, "++++++++++++", content
    #   headers = {'Cookie': response['set-cookie']}
    #url_fw_policy = "http://10.160.37.99/api/v2/cmdb/firewall/policy/"
    #response, content = http.request(url_fw_policy, 'GET', headers=headers)
    #
