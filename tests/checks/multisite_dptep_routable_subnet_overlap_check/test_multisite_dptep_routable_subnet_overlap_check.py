import os
import pytest
import logging
import importlib
from helpers.utils import read_data

script = importlib.import_module("aci-preupgrade-validation-script")

log = logging.getLogger(__name__)
dir = os.path.dirname(os.path.abspath(__file__))

test_function = "multisite_dptep_routable_subnet_overlap_check"

# icurl queries
subnet_api = 'fabricExtRoutablePodSubnet.json'
ucast_api = 'fvIntersiteConnP.json'
mcast_api = 'fvIntersiteMcastConnP.json'
pod_api = "fvPodConnP.json?rsp-subtree=children"

pod_dptep_outside_pool = [
    {
        "fvPodConnP": {
            "children": [
                {
                    "fvRsCommToConn": {
                        "attributes": {
                            "dn": "uni/tn-infra/fabricExtConnP-1/podConnP-1/rscommToConn-[10.0.1.5]",
                            "addr": "10.0.1.5",
                        }
                    }
                }
            ]
        }
    }
]

pod_dptep_in_reserved = [
    {
        "fvPodConnP": {
            "children": [
                {
                    "fvRsCommToConn": {
                        "attributes": {
                            "dn": "uni/tn-infra/fabricExtConnP-1/podConnP-1/rscommToConn-[10.0.0.5]",
                            "addr": "10.0.0.5",
                        }
                    }
                }
            ]
        }
    }
]

pod_dptep_in_unreserved = [
    {
        "fvPodConnP": {
            "children": [
                {
                    "fvRsCommToConn": {
                        "attributes": {
                            "dn": "uni/tn-infra/fabricExtConnP-1/podConnP-1/rscommToConn-[10.0.0.50]",
                            "addr": "10.0.0.50",
                        }
                    }
                }
            ]
        }
    }
]

ipv6_only_routable_subnet = [
    {
        "fabricExtRoutablePodSubnet": {
            "attributes": {
                "dn": "uni/controller/setuppol/setupp-1/extrtpodsubnet-[2001:db8::/64]",
                "pool": "2001:db8::/64",
                "reserveAddressCount": "16",
            }
        }
    }
]

@pytest.mark.parametrize(
    "icurl_outputs, expected_result",
    [
        # No Routable TEP Pool configured -> PASS without querying DPTEPs
        ({subnet_api: read_data(dir, "no_routable_subnet.json")}, script.PASS),
        # Routable TEP Pool present, no DPTEPs -> PASS
        (
            {
                subnet_api: read_data(dir, "routable_subnet_only.json"),
                pod_api: read_data(dir, "no_dptep.json"),
                ucast_api: read_data(dir, "no_dptep.json"),
                mcast_api: read_data(dir, "no_dptep.json"),
            },
            script.PASS,
        ),
        # Unicast DPTEP outside of every Routable TEP Pool -> PASS
        (
            {
                subnet_api: read_data(dir, "routable_subnet_only.json"),
                pod_api: read_data(dir, "no_dptep.json"),
                ucast_api: read_data(dir, "ucast_dptep_outside_pool.json"),
                mcast_api: read_data(dir, "no_dptep.json"),
            },
            script.PASS,
        ),
        # Unicast DPTEP inside the reserved portion of a Routable TEP Pool -> PASS
        (
            {
                subnet_api: read_data(dir, "routable_subnet_only.json"),
                pod_api: read_data(dir, "no_dptep.json"),
                ucast_api: read_data(dir, "ucast_dptep_in_reserved.json"),
                mcast_api: read_data(dir, "no_dptep.json"),
            },
            script.PASS,
        ),
        # Unicast DPTEP overlapping the unreserved portion of a Routable TEP Pool -> FAIL
        (
            {
                subnet_api: read_data(dir, "routable_subnet_only.json"),
                pod_api: read_data(dir, "no_dptep.json"),
                ucast_api: read_data(dir, "ucast_dptep_in_unreserved.json"),
                mcast_api: read_data(dir, "no_dptep.json"),
            },
            script.FAIL_O,
        ),
        # Multicast DPTEP overlapping the unreserved portion of a Routable TEP Pool -> FAIL
        (
            {
                subnet_api: read_data(dir, "routable_subnet_only.json"),
                pod_api: read_data(dir, "no_dptep.json"),
                ucast_api: read_data(dir, "no_dptep.json"),
                mcast_api: read_data(dir, "mcast_dptep_in_unreserved.json"),
            },
            script.FAIL_O,
        ),
        # IPv6-only Routable TEP Pool present -> PASS (no IPv4 subnet ranges to evaluate)
        (
            {
                subnet_api: ipv6_only_routable_subnet,
            },
            script.PASS,
        ),
        # DPTEP child outside of every Routable TEP Pool -> PASS
        (
            {
                subnet_api: read_data(dir, "routable_subnet_only.json"),
                pod_api: pod_dptep_outside_pool,
                ucast_api: read_data(dir, "no_dptep.json"),
                mcast_api: read_data(dir, "no_dptep.json"),
            },
            script.PASS,
        ),

        # DPTEP child inside reserved portion -> PASS
        (
            {
                subnet_api: read_data(dir, "routable_subnet_only.json"),
                pod_api: pod_dptep_in_reserved,
                ucast_api: read_data(dir, "no_dptep.json"),
                mcast_api: read_data(dir, "no_dptep.json"),
            },
            script.PASS,
        ),

        # DPTEP child overlapping unreserved portion -> FAIL
        (
            {
                subnet_api: read_data(dir, "routable_subnet_only.json"),
                pod_api: pod_dptep_in_unreserved,
                ucast_api: read_data(dir, "no_dptep.json"),
                mcast_api: read_data(dir, "no_dptep.json"),
            },
            script.FAIL_O,
        ),
    ],
)
def test_logic(run_check, mock_icurl, expected_result):
    result = run_check()
    assert result.result == expected_result