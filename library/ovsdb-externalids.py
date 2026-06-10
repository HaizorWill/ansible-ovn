#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import os
from typing import Any
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

type Changed = bool
IS_CHANGED: Changed = True
IS_NOT_CHANGED: Changed = False

type Err = str

import traceback
import ovs.stream
import ovs.jsonrpc

def MakeTransaction(conn: ovs.jsonrpc.Connection, newState: dict[str, str], checkMode: bool) -> tuple[Changed, Any, Err | None]:
    state, err = preflight(conn)
    if err or state == None:
        return IS_NOT_CHANGED, None, err
    if not state.items():
        return IS_NOT_CHANGED, None, f"Database preflight returned nothing: {state.items()}"
    change = dict()
    for k, v in newState.items():
        if state.get(k) != v:
           change[k] = v

    if not change.items():
        return IS_NOT_CHANGED, "Already up to date", None

    if checkMode:
        return IS_CHANGED, str(change), None

    mutQuery = [
            ["external_ids", "delete", ["set", list(change)]],
            ["external_ids", "insert", ["map", list(change.items())]]
    ]

    request = ovs.jsonrpc.Message.create_request("transact", [
        "Open_vSwitch",
        {"op": "mutate", "table": "Open_vSwitch", "where": [], "mutations": mutQuery}
        ])
    err, resp = conn.transact_block(request)
    if err:
        return IS_NOT_CHANGED, None, os.strerror(err)
    if resp is None:
        return IS_NOT_CHANGED, None, 'OVSDB server did not reply'
    if resp.type == ovs.jsonrpc.Message.T_ERROR or resp.error is not None:
        return IS_NOT_CHANGED, None, f"RPC error: {resp.error}"

    return IS_CHANGED, resp, None


def preflight(conn: ovs.jsonrpc.Connection) -> tuple[dict[str, str] | None, Err | None]:
    request = ovs.jsonrpc.Message.create_request("transact", [
        "Open_vSwitch",
        {"op": "select", "table": "Open_vSwitch", "where": [], "columns": ["external_ids"] }
        ])
    err, resp = conn.transact_block(request)
    if err:
        return None, os.strerror(err)
    if resp is None:
        return None, "OVSDB server did not reply"
    if resp.type == ovs.jsonrpc.Message.T_ERROR or resp.error is not None:
        return None, f"RPC error: {resp.error}"
    return dict(resp.result[0]["rows"][0]["external_ids"][1]), None

def runModule(module: AnsibleModule):
    error, stream = ovs.stream.Stream.open_block(ovs.stream.Stream.open(module.params["remote"]))
    if error:
        return False, None, os.strerror(error)
    rpc = ovs.jsonrpc.Connection(stream)
    newState = dict(i.split("=", 1) for i in module.params["ext_ids"])
    return MakeTransaction(rpc, newState, module.check_mode)


def main():
    module_args = {
        "remote": {"type": "str", "required": True},
        "ext_ids": {"type": "list", "elements": "str", "required": True}
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    try:
        chg, res, err = runModule(module)
        if err:
            module.fail_json(changed=chg, msg=err)
        module.exit_json(changed=chg, msg=str(res))
    except Exception as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc())

if __name__ == '__main__':
    main()
