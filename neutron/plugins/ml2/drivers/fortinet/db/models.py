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


"""Fortinet specific database schema/model."""

import sqlalchemy as sa

from neutron.db import model_base
from neutron.db import models_v2

## TODO: add log here temporarily
from neutron.openstack.common import log as logging
LOG = logging.getLogger(__name__)


class Fortinet_ML2_Namespace(model_base.BASEV2):
    """Schema for Fortinet network."""

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    tenant_id = sa.Column(sa.String(36))
    # For the name of vdom has the following restrictions:
    # only letters, numbers, "-" and "_" are allowed
    # no more than 11 characters are allowed
    # no spaces are allowed
    vdom_name = sa.Column(sa.String(11))


class ML2_FortinetPort(model_base.BASEV2, models_v2.HasId,
                      models_v2.HasTenant):
    """Schema for Fortinet port."""

    network_id = sa.Column(sa.String(36),
                           sa.ForeignKey("ml2_Fortinetnetworks.id"),
                           nullable=False)
    admin_state_up = sa.Column(sa.Boolean, nullable=False)
    physical_interface = sa.Column(sa.String(36))
    vlan_id = sa.Column(sa.String(36))

def create_namespace(context, tenant_id):
    """Create a Fortinet vdom associated with the Tenant."""
    session = context.session
    with session.begin(subtransactions=True):
        namespace = get_namespace(context, tenant_id)
        if not namespace:
            namespace = Fortinet_ML2_Namespace(tenant_id=tenant_id,
                                               vdom_name=None)
            session.add(namespace)
            id = get_namespace(context, tenant_id)["id"]
            vdom_name = "osvdm" + str(id)
            namespace.vdom_name = vdom_name
            session.add(namespace)
    return namespace

def delete_namespace(context, tenant_id):
    """Create a Fortinet vdom associated with the Tenant."""
    LOG.debug(_("!!!!!!! delete_namespace   "))
    session = context.session
    LOG.debug(_(" dir(session) = ", dir(session)))
    LOG.debug(_(" session = ", session))
    with session.begin(subtransactions=True):
        count = session.query(models_v2.Network).\
                     filter_by(tenant_id=tenant_id).count()
        LOG.debug(_("##### count = %s" % count))
        if count == 1:
            namespace = get_namespace(context, tenant_id)
            session.delete(namespace)
            LOG.debug(_("!!!!!!! namespace=", namespace))
            return namespace
    return None


def get_namespace(context, tenant_id):
    """Get Fortinet specific network, with vlan extension."""

    session = context.session
    namespace = session.query(Fortinet_ML2_Namespace).\
        filter_by(tenant_id=tenant_id).first()
    LOG.debug(_("!!!!!!! get_namespace namespace=", namespace))
    return namespace



def create_network(context, net_id, vlan, segment_id, network_type, tenant_id):
    """Create a Fortinet specific network/port-profiles."""

    # only network_type of vlan is supported
    session = context.session
    with session.begin(subtransactions=True):
        net = get_network(context, net_id, None)
        if not net:
            net = ML2_FortinetNetwork(id=net_id, vlan=vlan,
                                     segment_id=segment_id,
                                     network_type='vlan',
                                     tenant_id=tenant_id)
            session.add(net)
    return net


def delete_network(context, net_id):
    """Delete a Fortinet specific network/port-profiles."""

    session = context.session
    with session.begin(subtransactions=True):
        net = get_network(context, net_id, None)
        if net:
            session.delete(net)

def get_network(context, net_id, fields=None):
    """Get Fortinet specific network, with vlan extension."""

    session = context.session
    return session.query(ML2_FortinetNetwork).filter_by(id=net_id).first()


def get_networks(context, filters=None, fields=None):
    """Get all Fortinet specific networks."""

    session = context.session
    return session.query(ML2_FortinetNetwork).all()


def create_port(context, port_id, network_id, physical_interface,
                vlan_id, tenant_id, admin_state_up):
    """Create a Fortinet specific port, has policy like vlan."""

    session = context.session
    with session.begin(subtransactions=True):
        port = get_port(context, port_id)
        if not port:
            port = ML2_FortinetPort(id=port_id,
                                   network_id=network_id,
                                   physical_interface=physical_interface,
                                   vlan_id=vlan_id,
                                   admin_state_up=admin_state_up,
                                   tenant_id=tenant_id)
            session.add(port)

    return port


def get_port(context, port_id):
    """get a Fortinet specific port."""

    session = context.session
    return session.query(ML2_FortinetPort).filter_by(id=port_id).first()


def get_ports(context, network_id=None):
    """get a Fortinet specific port."""

    session = context.session
    return session.query(ML2_FortinetPort).filter_by(
        network_id=network_id).all()


def delete_port(context, port_id):
    """delete Fortinet specific port."""

    session = context.session
    with session.begin(subtransactions=True):
        port = get_port(context, port_id)
        if port:
            session.delete(port)


def update_port_state(context, port_id, admin_state_up):
    """Update port attributes."""

    session = context.session
    with session.begin(subtransactions=True):
        session.query(ML2_FortinetPort).filter_by(
            id=port_id).update({'admin_state_up': admin_state_up})
