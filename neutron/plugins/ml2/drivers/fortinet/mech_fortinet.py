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


"""Implentation of Fortinet ML2 Mechanism driver for ML2 Plugin."""

import netaddr
import json

import sys
import os

from oslo.config import cfg

from neutron.openstack.common import importutils
from neutron.openstack.common import log as logging
from neutron.plugins.ml2 import driver_api
from neutron.plugins.ml2 import db
from neutron.db import models_v2
from neutron.db import api as db_api
from neutron.common import constants as l3_constants

from neutron.plugins.ml2.drivers.fortinet.db import models as fortinet_db
from neutron.plugins.ml2.drivers.fortinet.api_client import client
from neutron.plugins.ml2.drivers.fortinet.api_client import exception
from neutron.plugins.ml2.drivers.fortinet.common import constants as const

from neutron.agent import securitygroups_rpc
from neutron.common import constants
from neutron.extensions import portbindings
#from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2.drivers import mech_agent


LOG = logging.getLogger(__name__)

cfg.CONF.import_group("ml2_fortinet",
                      "neutron.plugins.ml2.drivers.fortinet.common.config")


class FortinetMechanismDriver(mech_agent.SimpleAgentMechanismDriverBase):
    """ML2 Mechanism driver for Fortinet devices."""

    def __init__(self):
        sg_enabled = securitygroups_rpc.is_firewall_enabled()
        vif_details = {portbindings.CAP_PORT_FILTER: sg_enabled,
                       portbindings.OVS_HYBRID_PLUG: sg_enabled}
        super(FortinetMechanismDriver, self).__init__(
            constants.AGENT_TYPE_OVS,
            portbindings.VIF_TYPE_OVS,
            vif_details)

        self._driver = None
        self._fortigate = None

    def check_segment_for_agent(self, segment, agent):
            mappings = agent['configurations'].get('bridge_mappings', {})
            tunnel_types = agent['configurations'].get('tunnel_types', [])
            LOG.debug(_("Checking segment: %(segment)s "
                        "for mappings: %(mappings)s "
                        "with tunnel_types: %(tunnel_types)s"),
                      {'segment': segment, 'mappings': mappings,
                       'tunnel_types': tunnel_types})
            network_type = segment[driver_api.NETWORK_TYPE]
            if network_type == 'local':
                return True
            elif network_type in tunnel_types:
                return True
            elif network_type in ['flat', 'vlan']:
                return segment[driver_api.PHYSICAL_NETWORK] in mappings
            else:
                return False


    def initialize(self):
        """Initilize of variables needed by this class."""
        self.Fortinet_init()

    def Fortinet_init(self):
        """Fortinet specific initialization for this class."""
        LOG.debug(_("FortinetMechanismDriver_init"))
        self._fortigate = {
            "address": cfg.CONF.ml2_fortinet.address,
            "username": cfg.CONF.ml2_fortinet.username,
            "password": cfg.CONF.ml2_fortinet.password,
            "int_interface": cfg.CONF.ml2_fortinet.int_interface,
            "ext_interface": cfg.CONF.ml2_fortinet.ext_interface,
            "tenant_network_type": cfg.CONF.ml2_fortinet.tenant_network_type,
            "vlink_vlan_id_range": cfg.CONF.ml2_fortinet.vlink_vlan_id_range,
            "vlink_ip_range": cfg.CONF.ml2_fortinet.vlink_ip_range,
            "vip_mappedip_range": cfg.CONF.ml2_fortinet.vip_mappedip_range
        }

        for key in const.FORTINET_PARAMS:
            self.sync_conf_to_db(key)

        api_server = [(self._fortigate["address"], 80, False)]
        msg = {
            "username": self._fortigate["username"],
            "secretkey": self._fortigate["password"]
        }
        self._driver = client.FortiosApiClient(api_server,
                                               msg["username"],
                                               msg["secretkey"])


    def sync_conf_to_db(self, param):
        cls = getattr(fortinet_db, const.FORTINET_PARAMS[param]["cls"])
        conf_list = self.get_range(param)
        session = db_api.get_session()
        records = fortinet_db.get_records(session, cls)
        for record in records:
            for key in const.FORTINET_PARAMS[param]["keys"]:
                _element = const.FORTINET_PARAMS[param]["type"](record[key])
                if _element not in conf_list and not record.allocated:
                    kwargs = {key: record[key]}
                    fortinet_db.delete_record(session, cls, **kwargs)
        try:
            for i in range(0, len(conf_list),
                           len(const.FORTINET_PARAMS[param]["keys"])):
                kwargs = {}
                for key in const.FORTINET_PARAMS[param]["keys"]:
                    kwargs[key] = conf_list[i]
                    i += 1
                LOG.debug(_("!!!!!!! adding kwargs = %s" % kwargs))
                fortinet_db.add_record(session, cls, **kwargs)
        except IndexError:
            LOG.error(_("The number of the configure range is not even,"
                        "the last one of %(param)s can not be used"),
                      {'param': param})
            raise IndexError


    def get_range(self, param):
        _type = const.FORTINET_PARAMS[param]["type"]
        if const.FORTINET_PARAMS[param]["format"]:
            min, max = self._fortigate[param].split(const.FIELD_DELIMITER)
            if _type(min) > _type(max):
                min, max = max, min
            if _type == int:
                min, max =_type(min), _type(max) + 1
            result = const.FORTINET_PARAMS[param]["range"](min, max)
        else:
            result = const.FORTINET_PARAMS[param]["range"](
                                _type(self._fortigate[param]),
                                const.PREFIX["netmask"])
            LOG.debug(_("!!!!!!! result %s param_range = %s" % (param, result)))
        return result if isinstance(result, list) else list(result)



    def create_network_precommit(self, mech_context):
        """Create Network in the mechanism specific database table."""
        LOG.debug(_("++++++++++create_network_precommit+++++++++++++++++++++++++++++++++++"))
        network = mech_context.current
        context = mech_context._plugin_context
        tenant_id = network['tenant_id']
        LOG.debug(_("!!!!!!! mech_context.current = %s" % mech_context.current))
        LOG.debug(_("!!!!!!! context = %s" % context))
        if network["router:external"]:
            return
        # currently supports only one segment per network
        segment = mech_context.network_segments[0]
        network_type = segment['network_type']
        if network_type != 'vlan':
            raise Exception(
                _("Fortinet Mechanism: failed to create network, "
                  "only network type vlan is supported"))
        namespace = fortinet_db.get_namespace(context, tenant_id)
        if not namespace:
            try:
                namespace = fortinet_db.create_namespace(context, tenant_id)
                LOG.debug(_("!!!!!!! namespace = %s" % namespace))
                message = {
                    "name": namespace["vdom_name"],
                }
                LOG.debug(_("message = %s"), message)
                self._driver.request("ADD_VDOM", message)

            except Exception:
                LOG.exception(
                    _("Fortinet Mechanism: failed to create network in db"))
                self._driver.request("DELETE_VDOM", message)
                fortinet_db.delete_namespace(context, tenant_id)
                raise Exception(
                    _("Fortinet Mechanism: create_network_precommit failed"))

        self.fortinet_add_vlink(context, tenant_id)

        LOG.info(_("create network (precommit): "
                   "network type = %(network_type)s "
                   "for tenant %(tenant_id)s"),
                 {'network_type': network_type,
                  'tenant_id': tenant_id})

    def create_network_postcommit(self, mech_context):
        """Create Network as a portprofile on the switch."""
        LOG.debug(_("++++++++++create_network_postcommit+++++++++++++++++++++"))
        LOG.debug(_("create_network_postcommit: called"))

        network = mech_context.current
        LOG.debug(_("&&&&& mech_context.current = %s" % network))
        if network["router:external"]:
            # TODO
            return
        # use network_id to get the network attributes
        # ONLY depend on our db for getting back network attributes
        # this is so we can replay postcommit from db
        #context = mech_context._plugin_context

        network_id = network['id']
        #network_type = network['network_type']
        network_name = network["name"]
        tenant_id = network['tenant_id']
        #vlan_id = network['vlan']

        segments = mech_context.network_segments
        # currently supports only one segment per network
        segment = segments[0]
        network_type = segment['network_type']
        vlan_id = segment['segmentation_id']
        context = mech_context._plugin_context
        namespace = fortinet_db.get_namespace(context, tenant_id)
        try:
            message = {
                "name": const.PREFIX["inf"] + str(vlan_id),
                "vlanid": vlan_id,
                "interface": self._fortigate["int_interface"],
                "vdom": namespace["vdom_name"],
                "alias": network_name
            }
            LOG.debug(_("message = %s"), message)
            self._driver.request("ADD_VLAN_INTERFACE", message)
        except Exception:
            LOG.exception(_("Fortinet API client: failed in create network"))
            # TODO: DB
            pass
            #fortinet_db.delete_network(context, network_id)
            raise Exception(
                _("Fortinet Mechanism: create_network_postcommmit failed"))

        LOG.info(_("created network (postcommit): %(network_id)s"
                   " of network type = %(network_type)s"
                   " with vlan = %(vlan_id)s"
                   " for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'network_type': network_type,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})

    def delete_network_precommit(self, mech_context):
        """Delete Network from the plugin specific database table."""
        LOG.debug(_("delete_network_precommit: called"))

        network = mech_context.current
        network_id = network['id']
        context = mech_context._plugin_context
        ext_network = fortinet_db.get_ext_network(context, network_id)
        if ext_network:
            return

        tenant_id = network['tenant_id']
        vlan_id = network['provider:segmentation_id']
        try:
            message = {
                "name": const.PREFIX["inf"] + str(vlan_id)
            }
            self._driver.request("DELETE_VLAN_INTERFACE", message)

        except Exception:
            LOG.exception(
                _("Fortinet Mechanism: failed to delete network in db"))
            raise Exception(
                _("Fortinet Mechanism: delete_network_precommit failed"))

        LOG.info(_("delete network (precommit): %(network_id)s"
                   " with vlan = %(vlan_id)s"
                   " for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})


    def delete_network_postcommit(self, mech_context):
        """Delete network which translates to remove vlan interface
        and related vdom from the fortigate.
        """
        LOG.debug(_("delete_network_postcommit: called"))
        network = mech_context.current
        network_id = network['id']
        context = mech_context._plugin_context
        ext_network = fortinet_db.get_ext_network(context, network_id)
        if ext_network:
            return
        tenant_id = network['tenant_id']
        if not fortinet_db.tenant_network_count(context, tenant_id):
            try:
                self.fortinet_delete_vlink(context, tenant_id)
                namespace = fortinet_db.get_namespace(context, tenant_id)
                message = {
                        "name": namespace.vdom_name,
                }
                self._driver.request("DELETE_VDOM", message)
                fortinet_db.delete_namespace(context, tenant_id)
                LOG.info(_("delete network (postcommit): tenant %(tenant_id)s"
                       "vdom_name = %(vdom_name)s"),
                      {'tenant_id': tenant_id,
                       "vdom_name": namespace.vdom_name})
            except Exception:
                LOG.exception(_("Fortinet API client: failed to delete network"))
                raise Exception(
                    _("Fortinet switch exception, "
                      "delete_network_postcommit failed"))



    def update_network_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        pass

    def update_network_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        pass


    def create_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("create_subnetwork_precommit: called"))


    def create_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("create_subnetwork_postcommit: called"))
        LOG.debug(_("%%%%%%   mech_context = %s" % mech_context))
        LOG.debug(_("%%%%%%   dir(mech_context) = %s" % dir(mech_context)))
        LOG.debug(_("%%%%%%   mech_context.current = %s" % mech_context.current))
        gateway = mech_context.current["gateway_ip"]
        network_id = mech_context.current["network_id"]
        subnet_id = mech_context.current["id"]
        tenant_id = mech_context.current["tenant_id"]
        context = mech_context._plugin_context
        ext_network = fortinet_db.get_ext_network(context, network_id)
        if ext_network:
            try:
                message = {
                    "vdom": const.EXT_VDOM,
                    "dst": const.EXT_DEF_DST,
                    "device": self._fortigate["ext_interface"],
                    "gateway": gateway
                }
                response = self._driver.request("ADD_ROUTER_STATIC", message)
                LOG.debug(_("%%%%%%   response = %s" % response))
                mkey = response["results"]["mkey"]
                _test = fortinet_db.create_static_router(context,
                                                 subnet_id,
                                                 message["vdom"],
                                                 mkey)
                LOG.debug(_("$$$$$$ fortinet_db.create_static_router %s" % _test))
                LOG.debug(_("context %s, subnet_id %s, vdom %s, mkey %s" % (context, subnet_id, const.EXT_VDOM, mkey)))

            except Exception:
                LOG.exception(_("Fortinet API client: fail to "
                                "add the static router"))
                raise Exception(_("Fortinet API exception, "
                                  "delete_network_postcommit failed"))
        else:
            namespace = fortinet_db.get_namespace(context, tenant_id)
            vdom = namespace["vdom_name"]
            session = mech_context._plugin_context.session
            self._segments = db.get_network_segments(session, network_id)
            LOG.debug(_("  self._segments = %s" % self._segments))
            vlan_id = str(self._segments[0]["segmentation_id"])
            netmask = netaddr.IPNetwork(mech_context.current["cidr"]).netmask
            start_ip = mech_context.current["allocation_pools"][0]["start"]
            end_ip = mech_context.current["allocation_pools"][0]["end"]
            try:
                message = {
                    "vdom": vdom,
                    "interface": const.PREFIX["inf"] + vlan_id,
                    "gateway": gateway,
                    "netmask": netmask,
                    "start_ip": start_ip,
                    "end_ip": end_ip
                }
                response = self._driver.request("ADD_DHCP_SERVER", message)
                LOG.debug(_("%%%%%%   response1 = %s" % response))
                mkey = response["results"]["mkey"]
                fortinet_db.create_subnet(context, subnet_id, mkey)

                update_inf = {
                    "name": const.PREFIX["inf"] + str(vlan_id),
                    "vdom": vdom,
                    "ip": "%s %s" % (gateway, netmask)
                }
                response = self._driver.request("SET_VLAN_INTERFACE", update_inf)
                LOG.debug(_("%%%%%%   response2 = %s" % response))


            except Exception:
                # TODO: need to send delete_dhcp_server to fortigate in case of failed
                LOG.exception(_("Fortinet API client: failed to delete network"))
                raise Exception(_("Fortinet switch exception, "
                                  "delete_network_postcommit failed"))


    def delete_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("delete_subnetwork_precommit: called"))

    def delete_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("delete_subnetwork_postcommit: called"))
        LOG.debug(_("%%%%%% mech_context.current=%s" % mech_context.current))
        context = mech_context._plugin_context
        subnet_id = mech_context.current["id"]
        static_router = fortinet_db.get_static_router(context, subnet_id)
        LOG.debug(_("%%%%%% static_router=%s" % static_router))
        if static_router:
            try:
                message = {
                    "vdom": const.EXT_VDOM,
                    "id": static_router.edit_id
                }
                response = self._driver.request("DELETE_ROUTER_STATIC",
                                                message)
                LOG.debug(_("%%%%%%   response = %s" % response))
                fortinet_db.delete_static_router(context,
                                                 subnet_id)
            except Exception:
                LOG.exception(_("Fortinet API client: fail to "
                                "delete the static router"))
                raise Exception(_("Fortinet API exception, "
                                  "delete_network_postcommit failed"))

        else:
            subnet = fortinet_db.get_subnet(context, subnet_id)
            if subnet:
                try:
                    message = {
                        "vdom": subnet.vdom_name,
                        "id": subnet.mkey
                    }
                    self._driver.request("DELETE_DHCP_SERVER", message)
                    fortinet_db.delete_subnet(context, subnet_id)
                    if not fortinet_db.get_subnets(context, subnet.vdom_name):
                        message = {
                        "name": subnet.vdom_name
                        }
                        self._driver.request("DELETE_VDOM", message)

                except Exception:
                    LOG.exception(_("Failed to delete subnet"))
                    raise Exception(_("delete_network_postcommit failed"))


    def update_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("update_subnet_precommit(self: called"))

    def update_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("update_subnet_postcommit: called"))

    def _update_reserved_ips(self, context, subnet_id):
        reserved_addresses = []
        reserved_ips = fortinet_db.get_reserved_ips(context, subnet_id)
        subnet = fortinet_db.get_subnet(context, subnet_id)
        dhcp_server_id = subnet.mkey
        vdom = subnet.vdom_name
        for reserved_ip in reserved_ips:
            reserved_address = {
                "id": reserved_ip.edit_id,
                "ip": reserved_ip.ip,
                "mac": reserved_ip.mac
            }
            reserved_addresses.append(reserved_address)
        _reserved_address = json.dumps(reserved_addresses)
        if subnet:
            message = {
                "id": dhcp_server_id,
                "vdom": vdom,
                "reserved_address": _reserved_address
            }
            self._driver.request("SET_DHCP_SERVER_RSV_ADDR", message)

    def create_port_precommit(self, mech_context):
        """Create logical port on the switch (db update)."""
        LOG.debug(_("create_port_precommit: called"))
        #network = mech_context.current
        port = mech_context.current
        LOG.debug(_("!!!!! mech_context = %s" % mech_context))
        LOG.debug(_("!!!!! mech_context.current = %s" % port))
        context = mech_context._plugin_context
        tenant_id = port["tenant_id"]
        #vdom_name = fortinet_db.get_namespace(context, tenant_id).vdom_name
        port_id = port["id"]
        subnet_id = port["fixed_ips"][0]["subnet_id"]
        ip_address = port["fixed_ips"][0]["ip_address"]
        mac = port["mac_address"]
        kwargs = {'id': subnet_id}
        session = context.session
        subnet = fortinet_db.get_record(session, models_v2.Subnet, **kwargs)
        LOG.debug(_("!!!!! subnet = %s" % subnet))
        if (subnet.gateway_ip == ip_address) or \
           (port["device_owner"] in ["network:floatingip",
                                     "network:router_gateway"]):
            return

        fortinet_db.create_reserved_ip(context, port_id, subnet_id,
                                       tenant_id, ip_address, mac)
        self._update_reserved_ips(context, subnet_id)
        return



    def create_port_postcommit(self, mech_context):
        """Associate the assigned MAC address to the portprofile."""


    def delete_port_postcommit(self, mech_context):
        LOG.debug(_("delete_port_postcommit: called"))
        network = mech_context.current
        LOG.debug(_("!!!!! mech_context = %s" % mech_context))
        LOG.debug(_("!!!!! mech_context.current = %s" % network))
        context = mech_context._plugin_context
        port_id = network["id"]
        reserved_ip = fortinet_db.delete_reserved_ip(context, port_id)
        if reserved_ip:
            self._update_reserved_ips(context, reserved_ip.subnet_id)
        return

    def update_port_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("update_port_precommit"))
        _test = mech_context._plugin_context.session.query(models_v2.IPAllocation).filter_by(ip_address="192.168.22.254").first()
        LOG.debug(_("##### @@ _test=%s" % _test))

    def update_port_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("update_port_postcommit: called"))
        _test = mech_context._plugin_context.session.query(models_v2.IPAllocation).filter_by(ip_address="192.168.22.254").first()
        LOG.debug(_("##### @@ _test=%s" % _test))

    def _update_record(self, context, param, **kwargs):
        LOG.debug(_("_update_record: called"))
        kws = {
                "vdom_name": kwargs["vdom_name"],
                "allocated": kwargs["allocated"]
        }
        cls = getattr(fortinet_db, const.FORTINET_PARAMS[param]["cls"])
        record = fortinet_db.get_record(context, cls, **kws)
        LOG.debug(_("!!!!@@!! record: %s" % record))
        if not record:
            kws = {"allocated": False}
            record = fortinet_db.get_record(context, cls, **kws)
            for key, value in kwargs.iteritems():
                setattr(record, key, value)
            LOG.debug(_("!!!!! context.session= %(context.session)s,"
                    "cls=%(cls)s, record=%(record)s",
                    {'context.session': context.session,
                     'cls': cls, 'record': record}))
            fortinet_db.update_record(context, record)
            return record
        return None


    def fortinet_add_vlink(self, context, tenant_id):

        vdom_name = fortinet_db.get_namespace(context, tenant_id).vdom_name
        LOG.debug(_("!!!!! vdom_name = %s" % vdom_name))
        vlink_vlan = {
            "vdom_name": vdom_name,
            "allocated": True
        }
        LOG.debug(_("!!!!! vlink_vlan = %s" % vlink_vlan))
        vlink_vlan_allocation = self._update_record(context,
                                                    "vlink_vlan_id_range",
                                                    **vlink_vlan)
        LOG.debug(_("!!!!! vlink_vlan_allocation = %s" % vlink_vlan_allocation))
        if vlink_vlan_allocation:
            vlink_vlan_allocation.inf_name_int_vdom = const.PREFIX["vint"] + \
                                       str(vlink_vlan_allocation.vlan_id)
            vlink_vlan_allocation.inf_name_ext_vdom = const.PREFIX["vext"] + \
                                       str(vlink_vlan_allocation.vlan_id)
            fortinet_db.update_record(context, vlink_vlan_allocation)
            vlink_ip = {
                "vdom_name": vdom_name,
                "vlan_id": vlink_vlan_allocation.vlan_id,
                "allocated": True
            }
            LOG.debug(_("!!!!! vlink_vlan_allocation = %s" % vlink_vlan_allocation))
            vlink_ip_allocation = self._update_record(context,
                                                      "vlink_ip_range",
                                                      **vlink_ip)
            LOG.debug(_("!!!!! vlink_ip_allocation = %s" % vlink_ip_allocation))
            if vlink_ip_allocation:
                try:
                    ipsubnet = netaddr.IPNetwork(
                        vlink_ip_allocation.vlink_ip_subnet)
                    message = {
                        "name": vlink_vlan_allocation.inf_name_ext_vdom,
                        "vdom": const.EXT_VDOM
                    }
                    response = self._driver.request("GET_VLAN_INTERFACE", message)
                    if 200 == response["http_status"]:
                        LOG.debug(_("!!!!! response = %s" % response))
                except exception.ResourceNotFound:
                    message = {
                        "name": vlink_vlan_allocation.inf_name_ext_vdom,
                        "vlanid": vlink_vlan_allocation.vlan_id,
                        "vdom": const.EXT_VDOM,
                        "interface": "npu0_vlink0",
                        "ip": "%s %s" % (ipsubnet[1], ipsubnet.netmask)
                    }
                    self._driver.request("ADD_VLAN_INTERFACE", message)
                except:
                    raise Exception(_(sys.exc_info()[0]))

                try:
                    message = {
                        "name": vlink_vlan_allocation.inf_name_int_vdom,
                        "vdom": vdom_name
                    }
                    response = self._driver.request("GET_VLAN_INTERFACE", message)
                    if 200 == response["http_status"]:
                        LOG.debug(_("!!!!! response = %s" % response))
                except exception.ResourceNotFound:
                    message = {
                        "name": vlink_vlan_allocation.inf_name_int_vdom,
                        "vlanid": vlink_vlan_allocation.vlan_id,
                        "vdom": vdom_name,
                        "interface": "npu0_vlink1",
                        "ip": "%s %s" % (ipsubnet[2], ipsubnet.netmask)
                    }
                    self._driver.request("ADD_VLAN_INTERFACE", message)
                except Exception as e:
                    import traceback, os.path
                    top = traceback.extract_stack()[-1]
                    LOG.error(_("#####################################"))
                    LOG.error(_(', '.join([type(e).__name__, os.path.basename(top[0]), str(top[1])])))
                    LOG.error(_("#####################################"))
                    self.fortinet_reset_vlink(context,
                                              vlink_vlan_allocation,
                                              vlink_ip_allocation)
                    LOG.error(_("Failed to add vlink"))
                    raise Exception(_(sys.exc_info()[0]))
                return True
        return False


    def fortinet_delete_vlink(self, context, tenant_id):
        session = context.session
        vdom_name = fortinet_db.get_namespace(context, tenant_id)
        vlink_vlan = {
            "vdom_name": vdom_name,
            "allocated": True
        }
        vlink_vlan_allocation = fortinet_db.get_record(session,
                                    Fortinet_Vlink_Vlan_Allocation,
                                    **vlink_vlan)
        if not vlink_vlan_allocation:
            return False
        vlink_ip = {
            "vdom_name": vdom_name,
            "vlan_id": vlink_vlan_allocation.vlanid,
            "allocated": True
        }
        vlink_ip_allocation = fortinet_db.get_record(session,
                                  Fortinet_Vlink_IP_Allocation,
                                  **vlink_ip)
        if not vlink_ip_allocation:
            return False
        try:
            message = {
                "name": vlink_vlan_allocation.inf_name_ext_vdom
            }
            self._driver.request("DELETE_VLAN_INTERFACE", message)
            message = {
                "name": vlink_vlan_allocation.inf_name_int_vdom
            }
            self._driver.request("DELETE_VLAN_INTERFACE", message)
            self.fortinet_reset_vlink(context,
                                 vlink_vlan_allocation,
                                 vlink_ip_allocation)
        except:
            LOG.error(_("Failed to delete vlink"))
            raise Exception(_("Failed to delete vlink"))
        return True

    @staticmethod
    def fortinet_reset_vlink(context, vlink_vlan_allocation,
                             vlink_ip_allocation):
        vlink_vlan = {
            "vdom_name": None,
            "inf_name_int_vdom": None,
            "inf_name_ext_vdom": None,
            "allocated": False
        }
        if vlink_vlan_allocation:
            fortinet_db.update_record(context, vlink_vlan_allocation,
                                      **vlink_vlan)
        vlink_ip = {
            "vdom_name": None,
            "vlan_id": None,
            "allocated": False
        }
        if vlink_ip_allocation:
            fortinet_db.update_record(context, vlink_ip_allocation,
                                      **vlink_ip)


    def bind_port(self, context):
        """Marks ports as bound.

        Binds external ports and ports.
        Fabric configuration will occur on the subsequent port update.
        Currently only vlan segments are supported.
        """
        LOG.debug(_("bind_port() called"))
        LOG.debug(_("####context=%s" % context))
        LOG.debug(_("####context.current=%s" % context.current))
        if context.current['device_owner'] == \
                l3_constants.DEVICE_OWNER_ROUTER_INTF:
            # check controller to see if the port exists
            # so this driver can be run in parallel with others that add
            # support for external port bindings
            for segment in context.network.network_segments:
                if segment[api.NETWORK_TYPE] == const.TYPE_VLAN:
                    context.set_binding(
                        segment[api.ID], portbindings.VIF_TYPE_BRIDGE,
                        {portbindings.CAP_PORT_FILTER: False,
                         portbindings.OVS_HYBRID_PLUG: False})
                    return

        # IVS hosts will have a vswitch with the same name as the hostname
        if self.does_vswitch_exist(context.host):
            for segment in context.network.network_segments:
                if segment[api.NETWORK_TYPE] == pconst.TYPE_VLAN:
                    context.set_binding(
                        segment[api.ID], portbindings.VIF_TYPE_IVS,
                        {portbindings.CAP_PORT_FILTER: True,
                        portbindings.OVS_HYBRID_PLUG: False})