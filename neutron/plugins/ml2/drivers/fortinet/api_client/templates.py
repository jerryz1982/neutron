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

# About api request message naming regulations:
# Prefix         HTTP method
# ADD_XXX    -->    POST
# SET_XXX    -->    PUT
# DELETE_XXX -->    DELETE
# GET_XXX    -->    GET

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

LOGOUT = """
{
    "path": "/logout",
    "method": "POST"
}
"""


# Create VLAN
ADD_VLAN_INTERFACE = """
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
            #if $varExists('ip')
            "ip": "$ip",
            "allowaccess": "ping",
            #end if
            "secondary-IP":"enable",
            #if $varExists('alias')
            "alias": "$alias",
            #end if
            "ipv6": {
                "ip6-extra-addr": []
            }
        }
    }
}
"""

SET_VLAN_INTERFACE = """
{
    "path": "/api/v2/cmdb/system/interface/$name",
    "method": "PUT",
    "body": {
        "name": "interface",
        "json": {
            #if $varExists('ip')
                "ip": "$ip",
                "allowaccess": "ping https ssh snmp http fgfm capwap",
            #end if
            #if $varExists('secondaryips')
                #if $secondaryips
                    "secondary-IP": "enable",
                    "secondaryip": [
                    #for $secondaryip in $secondaryips[:-1]
                        {
                            "ip": "$secondaryip"
                        },
                    #end for
                        {
                            "ip": "$secondaryips[-1]"
                        }
                    ],
                #else
                    "secondary-IP": "disable",
                #end if
            #end if
            #if $varExists('vdom')
                "vdom": "$vdom"
            #else
                "vdom": "root"
            #end if
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
            #if $varExists('vdom')
            "vdom": "$vdom",
            #end if
            "name": "$name"
        }
    }
}
"""

# Get VLAN interface info
GET_VLAN_INTERFACE = """
{
    #if $varExists('name')
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/system/interface/$name/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/system/interface/$name/",
        #end if
    #else
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/system/interface/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/system/interface/",
        #end if
    #end if
    "method": "GET"
}
"""


ADD_DHCP_SERVER = """
{
    "path":"/api/v2/cmdb/system.dhcp/server/",
    "method": "POST",
    "body": {
        "name": "server",
        #if $varExists('vdom')
        "vdom": "$vdom",
        #end if
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

DELETE_DHCP_SERVER = """
{
    "path":"/api/v2/cmdb/system.dhcp/server/$id/",
    "method": "DELETE",
    "body": {
        "name": "server",
        #if $varExists('vdom')
        "vdom": "$vdom",
        #end if
        "id": "$id",
        "json": {
        }
    }
}
"""

GET_DHCP_SERVER = """
{
    #if $varExists('id')
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/system.dhcp/server/$id/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/system.dhcp/server/$id/",
        #end if
    #else
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/system.dhcp/server/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/system.dhcp/server/",
        #end if
    #end if
    "method": "GET"
}
"""

## api not supported yet, abandoned
_SET_DHCP_SERVER_RSV_ADDR_ = """
{
    "path":"/api/v2/cmdb/system.dhcp/server/1/",
    "method": "POST",
    "body": {
        #if $varExists('vdom')
        "vdom": "$vdom",
        #end if
        "json": {
            "id": $id,
            "reserved-address":[
                {
                    #if $varExists('rid')
                    "id": "$rid",
                    #end if
                    "ip":"$ip",
                    "mac":"$mac"
                }
            ]
        }
    }
}
"""

SET_DHCP_SERVER_RSV_ADDR = """
{
    "path":"/api/v2/cmdb/system.dhcp/server/$id/reserved-address",
    "method": "PUT",
    "body": {
        #if $varExists('vdom')
        "vdom": "$vdom",
        #end if
        "json": {
            "reserved-address":$reserved_address
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
    }
}
"""

GET_VDOM = """
{
    "path":"/api/v2/cmdb/system/vdom/$name",
    "method": "GET"
}
"""

ADD_VDOM_LINK = """
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

DELETE_VDOM_LINK = """
{
    "path": "/api/v2/cmdb/system/vdom-link/$name",
    "method": "DELETE",
    "body": {
    }
}
"""

GET_VDOM_LINK = """
{
    "path":"/api/v2/cmdb/system/vdom-link/$name",
    "method": "GET"
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


ADD_ROUTER_STATIC = """
{
    "path": "/api/v2/cmdb/router/static/",
    "method": "POST",
    "body": {
        #if $varExists('vdom')
            "vdom": "$vdom",
        #else
            "vdom": "root",
        #end if
        "json": {
            "dst": "$dst",
            "device": "$device",
            "gateway": "$gateway"
        }
    }
}
"""


DELETE_ROUTER_STATIC = """
{
    "path": "/api/v2/cmdb/router/static/$id/",
    "method": "DELETE",
    "body": {
        #if $varExists('vdom')
            "vdom": "$vdom",
        #else
            "vdom": "root",
        #end if
        "json": {
        }
    }
}
"""


GET_ROUTER_STATIC = """
{
    #if $varExists('id')
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/router/static/$id/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/router/static/$id/",
        #end if
    #else
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/router/static/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/router/static/",
        #end if
    #end if
    "method": "GET"
}
"""


ADD_FIREWALL_POLICY = """
{
    "path": "/api/v2/cmdb/firewall/policy/",
    "method": "POST",
    "body": {
        #if $varExists('vdom')
            "vdom": "$vdom",
        #else
            "vdom": "root",
        #end if
        "json": {
            "srcintf": [
                {
                    "name": "$srcintf"
                }
            ],
            "dstintf": [
                {
                    "name": "$dstintf"
                }
            ],
            "srcaddr":  [
                {
                    #if $varExists('srcaddr')
                        "name": "$srcaddr"
                    #else
                        "name": "all"
                    #end if
                }
            ],
            "dstaddr":  [
                {
                    #if $varExists('dstaddr')
                        "name": "$dstaddr"
                    #else
                        "name": "all"
                    #end if
                }
            ],
            "action": "accept",
            "schedule": "always",
            "service":  [
                {
                    "name": "ALL"
                }
            ]
        }
    }
}
"""

DELETE_FIREWALL_POLICY = """
{
    "path": "/api/v2/cmdb/firewall/policy/$id/",
    "method": "DELETE",
    "body": {
        #if $varExists('vdom')
            "vdom": "$vdom",
        #else
            "vdom": "root",
        #end if
        "json": {
        }
    }
}
"""


GET_FIREWALL_POLICY = """
{
    #if $varExists('id')
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/firewall/policy/$id/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/firewall/policy/$id/",
        #end if
    #else
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/firewall/policy/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/firewall/policy/",
        #end if
    #end if
    "method": "GET"
}
"""

ADD_FIREWALL_VIP = """
{
    "path":"/api/v2/cmdb/firewall/vip/",
    "method": "POST",
    "body": {
        #if $varExists('vdom')
            "vdom": "$vdom",
        #else
            "vdom": "root",
        #end if
        "name": "vip",
        "json": {
            "name": "$name",
            "extip": "$extip",
            "extintf": "$extintf",
            "mappedip": [
                {
                    "range": "$mappedip"
                }
            ]
        }
    }
}
"""

DELETE_FIREWALL_VIP = """
{
    "path":"/api/v2/cmdb/firewall/vip/$name",
    "method": "DELETE",
    "body": {
        #if $varExists('vdom')
            "vdom": "$vdom",
        #else
            "vdom": "root",
        #end if
        "name": "vip"
    }
}
"""

GET_FIREWALL_VIP = """
{
    #if $varExists('name')
        #if $varExists('vdom')
            "path":"/api/v2/cmdb/firewall/vip/$name/?vdom=$vdom",
        #else
            "path":"/api/v2/cmdb/firewall/vip/$name/",
        #end if
    #else
        #if $varExists('vdom')
            "path/api/v2/cmdb/firewall/vip/?vdom=$vdom",
        #else
            "path/api/v2/cmdb/firewall/vip/",
        #end if
    #end if
    "method": "GET"
}
"""

