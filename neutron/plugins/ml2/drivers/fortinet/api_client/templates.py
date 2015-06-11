# Copyright (c) 2015 Fortinet, Inc.
# All Rights Reserved.
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


#    FortiOS API request format templates.

# Login
LOGIN = """
{
    "path": "/logincheck",
    "method": "POST",
    "body": {
        "username": "$username",
        "secretkey": "$secretkey"
    }
}
"""

# Create VLAN
CREATE_VLAN_INTERFACE = """
{
    "path": "/api/v2/cmdb/system/interface/",
    "method": "POST",
    "body": {
        "name": "interface",
        "json": {
            #if $varExists('name')
            "name": "$name",
            #else
            "name": "os_vid_$vlanid",
            #end if
            "vlanid": $vlanid,
            "interface": "$interface",
            "vdom": "$vdom",
            "type": "vlan",
            #if $varExists('alias')
            "alias": "$alias",
            #end if
            "ipv6": {
                "dhcp6-relay-service": "disable",
                "ip6-address": "::/0",
                "ip6-max-interval": 600,
                "dhcp6-relay-type": "regular",
                "ip6-min-interval": 198,
                "dhcp6-client-options": "ianadns",
                "ip6-allowaccess": "",
                "ip6-reachable-time": 30000,
                "dhcp6-relay-ip": "",
                "autoconf": "disable",
                "ip6-link-mt": 0,
                "ip6-retrans-time": 1000,
                "ip6-mode": "static",
                "ip6-hop-limit": 64,
                "ip6-other-flag": "disable",
                "ip6-prefix-list": [],
                "ip6-send-adv": "disable",
                "ip6-manage-flag": "disable",
                "ip6-dns-server-override": "enable",
                "ip6-extra-addr": [],
                "ip6-default-life": 1800
            }
        }
    }
}
"""

# Delete VLAN (vlan_id)
DELETE_VLAN_INTERFACE = """
{
    "path": "/api/v2/cmdb/system/interface/",
    "method": "DELETE",
    "body": {
        "name": "interface",
        "json": {
            "name": "$name"
        }
    }
}
"""

CREATE_DHCP_SERVER = """
{
    "path":"/api/v2/cmdb/system.dhcp/server/",
    "method": "POST",
    "body": {
        "name": "server",
        "json": {
            "status":"enable",
            "dns-service":"local",
            "default-gateway":"$gateway",
            "netmask":"$netmask",
            "interface":"$interface",
            "ip-range":[
                {
                    "start-ip":"$start_ip",
                    "end-ip":"$end_ip"
                }
            ]
        }
    }
}
"""

# TODO: need to verify the format DELETE_DHCP_SERVER
DELETE_DHCP_SERVER = """
{
    "path":"/api/v2/cmdb/system.dhcp/server/",
    "method": "DELETE",
    "body": {
        "name": "server",
        "json": {
            "status":"enable",
            "dns-service":"local",
            "default-gateway":"$gateway",
            "netmask":"$netmask",
            "interface":"$interface",
            "ip-range":[
                {
                    "start-ip":"$start_ip",
                    "end-ip":"$end_ip"
                }
            ]
        }
    }
}
"""

ADD_VDOM = """
{
    "path":"/api/v2/cmdb/system/vdom/",
    "method": "POST",
    "body": {
        "name": "vdom",
        "json": {
            "name":"$name"
        }
    }
}
"""

DELETE_VDOM = """
{
    "path":"/api/v2/cmdb/system/vdom/$name",
    "method": "DELETE",
    "body": {
        "name": "vdom"
    }
}
"""

GET_VDOM = """
{
    "path":"/api/v2/cmdb/system/vdom/$name",
    "method": "GET",
    "body": {
    }
}
"""

ADD_VDOM_LNK = """
{
    "path":"/api/v2/cmdb/system/vdom-link/",
    "method": "POST",
    "body": {
        "name": "vdom-link",
        "json": {
            "name":"$name"
        }
    }
}
"""

DELETE_VDOM_LNK = """
{
    "path": "/api/v2/cmdb/system/vdom-link/$name",
    "method": "DELETE",
    "body": {
    }
}
"""

GET_VDOM_LNK = """
{
    "path":"/api/v2/cmdb/system/vdom-link/$name",
    "method": "GET",
    "body": {
    }
}
"""

SET_VDOM_LNK_INTERFACE = """
{
    "path":"/api/v2/cmdb/system/interface/",
    "method": "POST",
    "body": {
        "name": "vdom-link",
        "json": {
            "name":"$name"
        }
    }
}
"""