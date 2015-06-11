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

from oslo.config import cfg

from neutron.openstack.common import importutils
from neutron.openstack.common import log as logging
from neutron.plugins.ml2 import driver_api
from neutron.plugins.ml2 import db
from neutron.plugins.ml2.drivers.fortinet.db import models as fortinet_db
from neutron.plugins.ml2.drivers.fortinet.api_client import client

LOG = logging.getLogger(__name__)

#FORTIOS_DRIVER = 'neutron.plugins.ml2.drivers.fortinet.api_client.client.FortiosApiClient'

ML2_FORTINET = [cfg.StrOpt('address', default='',
                          help=_('The address of fortigates to connect to')),
               cfg.StrOpt('username', default='admin',
                          help=_('The username used to login')),
               cfg.StrOpt('password', default='password', secret=True,
                          help=_('The password used to login')),
               cfg.StrOpt('data_port', default='internal',
                          help=_('The port to serve tenant network')),
               cfg.StrOpt('tenant_network_type', default='vlan',
                          help=_('tenant network type, default is vlan'))
               ]

cfg.CONF.register_opts(ML2_FORTINET, "ml2_fortinet")

_prefix = "os_vid_"

class FortinetMechanismDriver(driver_api.MechanismDriver):
    """ML2 Mechanism driver for Fortinet devices. This is the upper
    layer driver class that interfaces to lower layer (NETCONF) below.
    """
    def __init__(self):
        self._driver = None
        self._fortigate = None
        self.initialize()

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
            "data_port": cfg.CONF.ml2_fortinet.data_port,
            "tenant_network_type": cfg.CONF.ml2_fortinet.tenant_network_type
        }
        api_server = [(self._fortigate["address"], 80, False)]
        msg = {
            "username": self._fortigate["username"],
            "secretkey": self._fortigate["password"]
        }
        self._driver = client.FortiosApiClient(api_server,
                                               msg["username"],
                                               msg["secretkey"])


    def create_network_precommit(self, mech_context):
        """Create Network in the mechanism specific database table."""
        LOG.debug(_("++++++++++create_network_precommit+++++++++++++++++++++++++++++++++++"))
        network = mech_context.current
        context = mech_context._plugin_context
        tenant_id = network['tenant_id']

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

        LOG.info(_("create network (precommit): "
                   "network type = %(network_type)s "
                   "for tenant %(tenant_id)s"),
                 {'network_type': network_type,
                  'tenant_id': tenant_id})

    def create_network_postcommit(self, mech_context):
        """Create Network as a portprofile on the switch."""
        LOG.debug(_("++++++++++create_network_postcommit+++++++++++++++++++++++++++++++++++"))
        LOG.debug(_("create_network_postcommit: called"))

        network = mech_context.current
        LOG.debug(_("&&&&& mech_context.current = %s" % network))
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
                "name": _prefix + str(vlan_id),
                "vlanid": vlan_id,
                "interface": self._fortigate["data_port"],
                "vdom": namespace["vdom_name"],
                "alias": network_name
            }
            LOG.debug(_("message = %s"), message)
            self._driver.request("CREATE_VLAN_INTERFACE", message)
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
        tenant_id = network['tenant_id']
        context = mech_context._plugin_context
        try:
            deleted_namespace = fortinet_db.delete_namespace(context,
                                                             tenant_id)
            if deleted_namespace:
                message = {
                        "name": deleted_namespace["vdom_name"],
                }
                self._driver.request("DELETE_VDOM", message)
            LOG.info(_("delete network (precommit): tenant %(tenant_id)s"),
                 {'tenant_id': tenant_id})
        except Exception:
            LOG.exception(
                _("Fortinet Mechanism: failed to delete network in db"))
            raise Exception(
                _("Fortinet Mechanism: delete_network_precommit failed"))


    def delete_network_postcommit(self, mech_context):
        """Delete network which translates to removng portprofile
        from the switch.
        """
        LOG.debug(_("delete_network_postcommit: called"))
        network = mech_context.current
        network_id = network['id']
        vlan_id = network['provider:segmentation_id']
        tenant_id = network['tenant_id']

        try:
            message = {
                "name": _prefix + str(vlan_id)
            }
            self._driver.request("DELETE_VLAN_INTERFACE", message)

        except Exception:
            LOG.exception(_("Fortinet API client: failed to delete network"))
            raise Exception(
                _("Fortinet switch exception, "
                  "delete_network_postcommit failed"))

        LOG.info(_("delete network (postcommit): %(network_id)s"
                   " with vlan = %(vlan_id)s"
                   " for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})

    def update_network_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        pass

    def update_network_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        pass

    def create_port_precommit(self, mech_context):
        """Create logical port on the switch (db update)."""

        LOG.debug(_("create_port_precommit: called"))

        port = mech_context.current
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        admin_state_up = port['admin_state_up']

        context = mech_context._plugin_context

        network = fortinet_db.get_network(context, network_id)
        vlan_id = network['vlan']

        try:
            fortinet_db.create_port(context, port_id, network_id,
                                   None,
                                   vlan_id, tenant_id, admin_state_up)
        except Exception:
            LOG.exception(_("Fortinet Mechanism: failed to create port in db"))
            raise Exception(
                _("Fortinet Mechanism: create_port_precommit failed"))

    def create_port_postcommit(self, mech_context):
        """Associate the assigned MAC address to the portprofile."""

        LOG.debug(_("create_port_postcommit: called"))

        port = mech_context.current
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']

        context = mech_context._plugin_context

        network = fortinet_db.get_network(context, network_id)
        vlan_id = network['vlan']

        interface_mac = port['mac_address']

        # convert mac format: xx:xx:xx:xx:xx:xx -> xxxx.xxxx.xxxx
        mac = self.mac_reformat_62to34(interface_mac)
        try:
            self._driver.associate_mac_to_network(self._fortigate['address'],
                                                  self._fortigate['username'],
                                                  self._fortigate['password'],
                                                  vlan_id,
                                                  mac)
        except Exception:
            LOG.exception(
                _("Fortinet API client: failed to associate mac %s")
                % interface_mac)
            raise Exception(
                _("Fortinet switch exception: create_port_postcommit failed"))

        LOG.info(
            _("created port (postcommit): port_id=%(port_id)s"
              " network_id=%(network_id)s tenant_id=%(tenant_id)s"),
            {'port_id': port_id,
             'network_id': network_id, 'tenant_id': tenant_id})

    def delete_port_precommit(self, mech_context):
        """Delete logical port on the switch (db update)."""

        LOG.debug(_("delete_port_precommit: called"))
        port = mech_context.current
        port_id = port['id']

        context = mech_context._plugin_context

        try:
            pass
            #fortinet_db.delete_port(context, port_id)
        except Exception:
            LOG.exception(_("Fortinet Mechanism: failed to delete port in db"))
            raise Exception(
                _("Fortinet Mechanism: delete_port_precommit failed"))

    def delete_port_postcommit(self, mech_context):
        """Dissociate MAC address from the portprofile."""

        LOG.debug(_("delete_port_postcommit: called"))
        port = mech_context.current
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']

        context = mech_context._plugin_context

        network = fortinet_db.get_network(context, network_id)
        vlan_id = network['vlan']

        interface_mac = port['mac_address']

        # convert mac format: xx:xx:xx:xx:xx:xx -> xxxx.xxxx.xxxx
        mac = self.mac_reformat_62to34(interface_mac)
        try:
            self._driver.dissociate_mac_from_network(
                self._fortigate['address'],
                self._fortigate['username'],
                self._fortigate['password'],
                vlan_id,
                mac)
        except Exception:
            LOG.exception(
                _("Fortinet API client: failed to dissociate MAC %s") %
                interface_mac)
            raise Exception(
                _("Fortinet switch exception, delete_port_postcommit failed"))

        LOG.info(
            _("delete port (postcommit): port_id=%(port_id)s"
              " network_id=%(network_id)s tenant_id=%(tenant_id)s"),
            {'port_id': port_id,
             'network_id': network_id, 'tenant_id': tenant_id})

    def update_port_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("update_port_precommit(self: called"))

    def update_port_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("update_port_postcommit: called"))

    def create_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("create_subnetwork_precommit: called"))


    def create_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("create_subnetwork_postcommit: called"))
        LOG.debug(_("%%%%%%   mech_context = %s" % mech_context))
        LOG.debug(_("%%%%%%   dir(mech_context) = %s" % dir(mech_context)))
        LOG.debug(_("%%%%%%   mech_context.current = %s" % mech_context.current))

        info = self._get_subnet_info(mech_context, mech_context.current)
        LOG.debug(_("  tenant_id, network_id, gateway_ip =", info))
        if info:
            tenant_id, network_id, gateway_ip = info
            #self.apic_manager.ensure_subnet_created_on_apic(
            #    tenant_id, network_id, gateway_ip)
        #get_network_segments
        gateway = mech_context.current["gateway_ip"]
        network_id = mech_context.current["network_id"]
        session = mech_context._plugin_context.session
        self._segments = db.get_network_segments(session, network_id)
        LOG.debug(_("  self._segments = %s" % self._segments))
        vlan_id = str(self._segments[0]["segmentation_id"])
        netmask = "255.255.255.0"
        start_ip = mech_context.current["allocation_pools"][0]["start"]
        end_ip = mech_context.current["allocation_pools"][0]["end"]
        try:
            message = {
                "interface": _prefix + vlan_id,
                "gateway": gateway,
                "netmask": netmask,
                "start_ip": start_ip,
                "end_ip": end_ip
            }
            self._driver.request("CREATE_DHCP_SERVER", message)

        except Exception:
            LOG.exception(_("Fortinet API client: failed to delete network"))
            raise Exception(_("Fortinet switch exception, "
                              "delete_network_postcommit failed"))


    def delete_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("delete_subnetwork_precommit: called"))

    def delete_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("delete_subnetwork_postcommit: called"))

    def update_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("update_subnet_precommit(self: called"))

    def update_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug(_("update_subnet_postcommit: called"))

    def _get_subnet_info(self, context, subnet):
        if subnet['gateway_ip']:
            tenant_id = subnet['tenant_id']
            network_id = subnet['network_id']
            network = context._plugin.get_network(context._plugin_context,
                                                  network_id)
            if not network.get('router:external'):
                cidr = netaddr.IPNetwork(subnet['cidr'])
                gateway_ip = '%s/%s' % (subnet['gateway_ip'],
                                        str(cidr.prefixlen))
                return tenant_id, network_id, gateway_ip

    @staticmethod
    def mac_reformat_62to34(interface_mac):
        """Transform MAC address format.

        Transforms from 6 groups of 2 hexadecimal numbers delimited by ":"
        to 3 groups of 4 hexadecimals numbers delimited by ".".

        :param interface_mac: MAC address in the format xx:xx:xx:xx:xx:xx
        :type interface_mac: string
        :returns: MAC address in the format xxxx.xxxx.xxxx
        :rtype: string
        """

        mac = interface_mac.replace(":", "")
        mac = mac[0:4] + "." + mac[4:8] + "." + mac[8:12]
        return mac
