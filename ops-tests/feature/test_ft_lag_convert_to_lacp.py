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
# Name:        test_ft_lag_convert_to_lacp.py
#
# Description: Tests that a previously configured static Link Aggregation can
#              be converted to a dynamic one
#
# Author:      Jose Hernandez
#
# Topology:  |Host| ----- |Switch| ---------------------- |Switch| ----- |Host|
#                                   (Static LAG - 2 links)
#
# Success Criteria:  PASS -> LAGs is converted from static to dynamic
#
#                    FAILED -> LAG cannot be converted from static to dynamic
#
###############################################################################

from lacp_lib import create_lag
from lacp_lib import turn_on_interface
from lacp_lib import turn_off_interface
from lacp_lib import validate_turn_on_interfaces
from lacp_lib import validate_turn_off_interfaces
from lacp_lib import associate_interface_to_lag
from lacp_lib import verify_lag_config
from lacp_lib import create_vlan
from lacp_lib import verify_vlan_full_state
from lacp_lib import check_connectivity_between_hosts
from lacp_lib import create_lag_passive
from lacp_lib import create_lag_active
from lacp_lib import set_lag_rate
from lacp_lib import associate_vlan_to_l2_interface
from lacp_lib import associate_vlan_to_lag
from lacp_lib import verify_lag_interface_key
from lacp_lib import verify_lag_interface_priority
from lacp_lib import verify_lag_interface_id
from lacp_lib import verify_lag_interface_system_id
from lacp_lib import verify_lag_interface_system_priority
from lacp_lib import verify_lag_interface_lag_id
from lacp_lib import validate_lag_state_sync
from lacp_lib import validate_lag_state_static
from lacp_lib import LOCAL_STATE
from lacp_lib import REMOTE_STATE
from lacp_lib import retry_wrapper
import pytest

TOPOLOGY = """
#            +-----------------+
#            |                 |
#            |      Host 1     |
#            |                 |
#            +-----------------+
#                     |
#                     |
#     +-------------------------------+
#     |                               |
#     |                               |
#     |            Switch 1           |
#     |                               |
#     +-------------------------------+
#          |         |        |
#          |         |        |
#          |         |        |
#     +-------------------------------+
#     |                               |
#     |                               |
#     |            Switch 2           |
#     |                               |
#     +-------------------------------+
#                     |
#                     |
#            +-----------------+
#            |                 |
#            |     Host 2      |
#            |                 |
#            +-----------------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2
[type=host name="Host 1"] hs1
[type=host name="Host 2"] hs2

# Links

sw1:1 -- hs1:1
sw2:1 -- hs2:1
sw1:2 -- sw2:2
sw1:3 -- sw2:3
sw1:4 -- sw2:4
"""

# Global variables
SW_LBL_PORTS = ['1', '2', '3', '4']
LAG_ID = '1'
LAG_VLAN = 900
NETWORK = '10.90.0.'
NETMASK = '24'
NUMBER_PINGS = 5


def verify_lacp_state(
    sw1,
    sw2,
    sw1_lacp_mode='off',
    sw2_lacp_mode='active',
):
    sw1_lacp_config = sw1.libs.vtysh.show_lacp_configuration()
    sw2_lacp_config = sw2.libs.vtysh.show_lacp_configuration()
    print('Verify LACP state on LAG members')
    for port in SW_LBL_PORTS[1:]:
        sw1_lacp_state = sw1.libs.vtysh.show_lacp_interface(port)
        sw2_lacp_state = sw2.libs.vtysh.show_lacp_interface(port)
        sw_lacp_states = [sw1_lacp_state, sw2_lacp_state]
        sw_lacp_configs = [sw1_lacp_config, sw2_lacp_config]
        sw_lacp_modes = [sw1_lacp_mode, sw2_lacp_mode]
        if sw1_lacp_mode == 'off':
            lacp_def_value = ''
            lacp_def_priority = ''
        else:
            lacp_def_value = '1'
            lacp_def_priority = '65534'
        for (
            sw_lacp_state,
            sw_lacp_config,
            sw_lacp_mode,
            rev_sw_lacp_state,
        ) in zip(
            sw_lacp_states,
            sw_lacp_configs,
            sw_lacp_modes,
            reversed(sw_lacp_states)
        ):
            verify_lag_interface_lag_id(sw_lacp_state)
            verify_lag_interface_key(
                sw_lacp_state,
                rev_sw_lacp_state,
                key=lacp_def_value,
                value_check=True,
                cross_check=True
            )
            verify_lag_interface_priority(
                sw_lacp_state,
                rev_sw_lacp_state,
                priority=lacp_def_value,
                value_check=True,
                cross_check=True
            )
            verify_lag_interface_system_priority(
                sw_lacp_state,
                sw2_int_map_lacp=rev_sw_lacp_state,
                system_priority=lacp_def_priority,
                value_check=True,
                cross_check=True
            )
            if sw_lacp_mode != 'off':
                sys_id = sw_lacp_config['id']
            else:
                sys_id = ''
            verify_lag_interface_system_id(
                sw_lacp_state,
                sw2_int_map_lacp=rev_sw_lacp_state,
                system_id=sys_id,
                value_check=True,
                cross_check=True
            )
            if sw_lacp_mode != 'off':
                verify_lag_interface_id(
                    sw_lacp_state,
                    rev_sw_lacp_state,
                    value_check=False,
                    cross_check=True
                )
                validate_lag_state_sync(
                    sw_lacp_state,
                    LOCAL_STATE,
                    lacp_mode=sw_lacp_mode
                )
                validate_lag_state_sync(
                    rev_sw_lacp_state,
                    REMOTE_STATE,
                    lacp_mode=sw_lacp_mode
                )
            else:
                verify_lag_interface_id(
                    sw_lacp_state,
                    rev_sw_lacp_state,
                    id='',
                    value_check=True,
                    cross_check=True
                )
                validate_lag_state_static(sw_lacp_state, LOCAL_STATE)
                validate_lag_state_static(sw_lacp_state, REMOTE_STATE)


def enable_switches_interfaces(sw_list, step):
    step('Enable switches interfaces')
    for sw in sw_list:
        for port in SW_LBL_PORTS:
            turn_on_interface(sw, port)
    # Defining internal method to use decorator

    @retry_wrapper(
        'Ensure interfaces are turned on',
        'Interfaces not yet ready',
        5,
        60)
    def internal_check_interfaces(sw_list):
        for sw in sw_list:
            validate_turn_on_interfaces(sw, SW_LBL_PORTS)
    internal_check_interfaces(sw_list)


def disable_switches_interfaces(sw_list, step):
    step('Disable switches interfaces')
    for sw in sw_list:
        for port in SW_LBL_PORTS:
            turn_off_interface(sw, port)
    # Defining internal method to use decorator

    @retry_wrapper(
        'Ensure interfaces are turned off',
        'Interfaces not yet ready',
        5,
        60)
    def internal_check_interfaces(sw_list):
        for sw in sw_list:
            validate_turn_off_interfaces(sw, SW_LBL_PORTS)
    internal_check_interfaces(sw_list)


def configure_lags(sw_list, sw_real_ports, step):
    step('Create LAGs')
    for sw in sw_list:
        create_lag(sw, LAG_ID, 'off')
        # Set LACP rate to fast
        set_lag_rate(sw, LAG_ID, 'fast')
        for port in sw_real_ports[sw][1:]:
            associate_interface_to_lag(sw, port, LAG_ID)
        verify_lag_config(
            sw,
            LAG_ID,
            sw_real_ports[sw][1:],
            heartbeat_rate='fast'
        )
    check_func = retry_wrapper(
        'Verify LACP status on both devices',
        'Configuration not yet applied',
        2,
        4
    )(verify_lacp_state)
    check_func(
        sw_list[0],
        sw_list[1],
        sw1_lacp_mode='off',
        sw2_lacp_mode='off'
    )


def configure_vlans(sw_list, sw_real_ports, step):
    step('Configure VLANs on devices')
    for sw in sw_list:
        # Create VLAN
        create_vlan(sw, LAG_VLAN)
        # Associate VLAN to LAG

        associate_vlan_to_lag(sw, str(LAG_VLAN), LAG_ID)
        # Associate VLAN to host interface
        associate_vlan_to_l2_interface(
            sw,
            str(LAG_VLAN),
            sw_real_ports[sw][0]
        )
        # Verify VLAN configuration was successfully applied
        verify_vlan_full_state(
            sw,
            LAG_VLAN, interfaces=[
                sw_real_ports[sw][0],
                'lag{}'.format(LAG_ID)
            ]
        )


def configure_workstations(hs_list, step):
    step('Configure workstations')
    for hs_num, hs in enumerate(hs_list):
        hs.libs.ip.interface(
            SW_LBL_PORTS[0],
            addr='{}{}/{}'.format(NETWORK, hs_num + 1, NETMASK),
            up=True
        )


def validate_connectivity(hs_list, wait, step, time_steps=5, timeout=15):
    step('Check workstations connectivity')
    if wait is False:
        check_connectivity_between_hosts(
            hs_list[0],
            '{}{}'.format(NETWORK, 1),
            hs_list[1],
            '{}{}'.format(NETWORK, 2),
            NUMBER_PINGS,
            True
        )
    else:
        check_func = retry_wrapper(
            'Verifying workstations connectivity',
            'Configuration not yet applied',
            time_steps,
            timeout
        )(check_connectivity_between_hosts)
        check_func(
            hs_list[0],
            '{}{}'.format(NETWORK, 1),
            hs_list[1],
            '{}{}'.format(NETWORK, 2),
            NUMBER_PINGS,
            True
        )


def change_lacp_mode(sw_list, sw_real_ports, step):
    step('Change LAGs to dynamic')
    create_lag_active(sw_list[0], LAG_ID)
    create_lag_passive(sw_list[1], LAG_ID)
    # Verify configuration was successfully applied
    for sw, mode in zip(sw_list, ['active', 'passive']):
        verify_lag_config(
            sw,
            LAG_ID,
            sw_real_ports[sw][1:],
            heartbeat_rate='fast',
            mode=mode
        )
    check_func = retry_wrapper(
        'Verify LACP status on both devices',
        'Retry to make sure negotiation took place',
        5,
        15
    )(verify_lacp_state)
    check_func(
        sw_list[0],
        sw_list[1],
        sw1_lacp_mode='active',
        sw2_lacp_mode='passive'
    )


@pytest.mark.skipif(True, reason="Skipping due to instability")
def test_ft_lag_convert_to_lacp(topology, step):
    hs1 = topology.get('hs1')
    hs2 = topology.get('hs2')
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')

    assert hs1 is not None, 'hs1 was not initialized'
    assert hs2 is not None, 'hs2 was not initialized'
    assert sw1 is not None, 'sw1 was not initialized'
    assert sw2 is not None, 'sw2 was not initialized'

    sw_real_ports = {
        sw1: [sw1.ports[port] for port in SW_LBL_PORTS],
        sw2: [sw2.ports[port] for port in SW_LBL_PORTS]
    }

    # Enable switches interfaces
    enable_switches_interfaces([sw1, sw2], step)

    # Configure static LAGs with members
    configure_lags([sw1, sw2], sw_real_ports, step)

    # Add VLAN configuration to LAGs and workstation interfaces
    configure_vlans([sw1, sw2], sw_real_ports, step)

    # Configure workstations
    configure_workstations([hs1, hs2], step)

    # Validate workstations can communicate
    validate_connectivity([hs1, hs2], True, step)

    # Change LACP mode on LAGs from static to dynamic
    change_lacp_mode([sw1, sw2], sw_real_ports, step)

    # Validate workstations can communicate
    validate_connectivity([hs1, hs2], False, step)

    # Disable switches interfaces
    disable_switches_interfaces([sw1, sw2], step)

    # Enable switches interfaces
    enable_switches_interfaces([sw1, sw2], step)

    # Validate workstations can communicate
    validate_connectivity([hs1, hs2], True, step, time_steps=2, timeout=4)
