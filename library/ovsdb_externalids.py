#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import os
from typing import Any
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
import traceback

import_error: bool = False
try:
    import ovs.stream
    import ovs.jsonrpc
except ImportError:
    import_error = True
    import_traceback = traceback.format_exc()

Changed = bool
IS_CHANGED: Changed = True
IS_NOT_CHANGED: Changed = False

Err = str

def MakeTransaction(conn: ovs.jsonrpc.Connection, newState: dict[str, str], checkMode: bool) -> tuple[Changed, dict[str, Any] | None, Err | None]:
    state, err = preflight(conn)
    if err or state is None:
        return IS_NOT_CHANGED, None, err
    change = dict()
    for k, v in newState.items():
        if state.get(k) != v:
           change[k] = v

    if not change:
        return IS_NOT_CHANGED, {"msg": "Already up to date"}, None

    diff = {"before": {k: state.get(k, "") for k in change}, "after": change}

    if checkMode:
        return IS_CHANGED, {"msg": change, "diff": diff}, None

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
    for i in resp.result:
        if isinstance(i, dict) and "error" in i:
            return IS_NOT_CHANGED, None, f"Operational error: {i['error']}: {i.get('details')}"
    return IS_CHANGED, {"msg": f"Updated {len(change)} key(s)", "diff": diff}, None


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
    for i in resp.result:
        if isinstance(i, dict) and "error" in i:
            return None, f"Operational error: {i['error']}: {i.get('details')}"
        if isinstance(i, dict) and not i.get("rows"):
            return None, f"Request returned no rows: {resp.result}"
    return dict(resp.result[0]["rows"][0]["external_ids"][1]), None

def runModule(module: AnsibleModule) -> tuple[Changed, dict[str, Any] | None, str | None]:
    error, stream = ovs.stream.Stream.open_block(ovs.stream.Stream.open(module.params["remote"]))
    if error:
        return IS_NOT_CHANGED, None, os.strerror(error)
    rpc = ovs.jsonrpc.Connection(stream)
    newState = dict(i.split("=", 1) for i in module.params["ext_ids"])
    chg, resp, err = MakeTransaction(rpc, newState, module.check_mode)
    rpc.close()
    return chg, resp, err


def main():
    module_args = {
        "remote": {"type": "str", "required": True},
        "ext_ids": {"type": "list", "elements": "str", "required": True}
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if import_error:
        module.fail_json(msg=missing_required_lib("ovs"), details=import_traceback)

    try:
        chg, res, err = runModule(module)
        if err:
            module.fail_json(changed=chg, msg=err)

        module.exit_json(changed=chg, **(res or {}))
    except Exception as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc())

if __name__ == '__main__':
    main()
