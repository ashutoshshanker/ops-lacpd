# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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
#

###############################################################################
# Name         test_ft_lag_static_nonconsecutive_interfaces.py
#
# Objective:  Verify that a static LAG can be configured using
#             non-consecutive interfaces
#
# Description: This test verifies that a static LAG can be configured using
#               non-consecutive interfaces.
#
# Topology:    |Host| ----- |Switch| ------------------ |Switch| ----- |Host|
#                                   (Static LAG - 2 links)
#
# Success Criteria:  PASS -> This test is effective if pinging between
#                            the workstations is successful.
#
#                    FAILED -> This test fails if the ping does not reach
#                              the other side.
#
###############################################################################

import pytest
from lacp_lib import (
    associate_interface_to_lag,
    associate_vlan_to_l2_interface,
    associate_vlan_to_lag,
    create_lag,
    create_vlan,
    turn_on_interface,
    verify_connectivity_between_hosts,
    verify_lag_config,
    verify_turn_on_interfaces
)

TOPOLOGY = """

# +-------+                            +-------+
# |       |                            |       |
# |  hs1  |                            |  hs2  |
# |       |                            |       |
# +---1---+                            +---1---+
#     |                                    |
#     |                                    |
#     |                                    |
#     |                                    |
# +---2---+                            +---2---+
# |       |                            |       |
# |       1----------------------------1       |
# |  sw1  3----------------------------3  sw2  |
# |       |                            |       |
# +-------+                            +-------+



# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2
[type=host name="Host 1"] hs1
[type=host name="Host 2"] hs2

# Links
sw1:2 -- hs1:1
sw1:1 -- sw2:1
sw1:3 -- sw2:3
sw2:2 -- hs2:1
"""


@pytest.mark.skipif(True, reason="Skipping due to instability")
def test_static_nonconsecutive_interfaces(topology, step):

    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    hs1 = topology.get('hs1')
    hs2 = topology.get('hs2')

    assert sw1 is not None
    assert sw2 is not None
    assert hs1 is not None
    assert hs2 is not None

    ports_sw1 = list()
    ports_sw2 = list()
    port_labels = ['1', '2', '3']

    lag_id = '1'
    vlan_id = '900'

    step("### Mapping interfaces ###")
    for port in port_labels:
        ports_sw1.append(sw1.ports[port])
        ports_sw2.append(sw2.ports[port])

    step("#### Turning on interfaces in sw1 ###")
    for port in ports_sw1:
        turn_on_interface(sw1, port)

    step("#### Turning on interfaces in sw2 ###")
    for port in ports_sw2:
        turn_on_interface(sw2, port)

    step("#### Validate interfaces are turn on ####")
    verify_turn_on_interfaces(sw1, ports_sw1)
    verify_turn_on_interfaces(sw2, ports_sw2)

    step("##### Create LAGs ####")
    create_lag(sw1, lag_id, 'off')
    create_lag(sw2, lag_id, 'off')

    step("#### Associate Interfaces to LAG ####")
    for intf in ports_sw1[::2]:
        associate_interface_to_lag(sw1, intf, lag_id)

    for intf in ports_sw2[::2]:
        associate_interface_to_lag(sw2, intf, lag_id)

    step("#### Verify LAG configuration ####")
    verify_lag_config(sw1, lag_id, ports_sw1[::2])
    verify_lag_config(sw2, lag_id, ports_sw2[::2])

    step("#### Configure VLANs on switches ####")
    create_vlan(sw1, vlan_id)
    create_vlan(sw2, vlan_id)

    associate_vlan_to_l2_interface(sw1, vlan_id, ports_sw1[1])
    associate_vlan_to_lag(sw1, vlan_id, lag_id)

    associate_vlan_to_l2_interface(sw2, vlan_id, ports_sw2[1])
    associate_vlan_to_lag(sw2, vlan_id, lag_id)

    step("#### Configure workstations ####")
    hs1.libs.ip.interface('1', addr='140.1.1.10/24', up=True)
    hs2.libs.ip.interface('1', addr='140.1.1.11/24', up=True)

    step("#### Test ping between clients work ####")
    verify_connectivity_between_hosts(hs1, '140.1.1.10',
                                      hs2, '140.1.1.11')
