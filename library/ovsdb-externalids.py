#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import os
from re import split
import time
from typing import Any
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from typing import NewType

Exists = NewType("Exists", bool)
EXISTS: Exists = Exists(True)
NOT_EXISTS: Exists = Exists(False)

Changed = NewType("Changed", bool)
IS_CHANGED: Changed = Changed(True)
IS_NOT_CHANGED: Changed = Changed(False)

import traceback
import ovs.stream
import ovs.dirs
import ovs.poller
import ovs.jsonrpc

def checkKey(conn: ovs.jsonrpc.Connection, key: str) -> tuple[Any, Exists, str | None]:
    request = ovs.jsonrpc.Message.create_request("transact", [
        "Open_vSwitch",
        {"op": "select", "table": "Open_vSwitch", "where": [], "columns": ["external_ids"] }
        ])
    err, resp = conn.transact_block(request)
    if err:
        return None, NOT_EXISTS, os.strerror(err)
    if resp is None:
        return None, NOT_EXISTS, "OVSDB server did not reply"
    if resp.type == ovs.jsonrpc.Message.T_ERROR or resp.error is not None:
        return None, NOT_EXISTS, f"RPC error: {resp.error}"
    ids = dict(resp.result[0]["rows"][0]["external_ids"][1])
    if ids.get(key):
        return ids.get(key), EXISTS, None
    return None, NOT_EXISTS, None

def clearKey(conn: ovs.jsonrpc.Connection, key: str, val: Any) -> tuple[Changed, str | None]:
    request = ovs.jsonrpc.Message.create_request("transact", [
        "Open_vSwitch",
        {"op": "mutate", "table": "Open_vSwitch", "where": [], "mutations": [["external_ids", "delete", ["map", [[key, val]]] ]] }
        ])
    err, resp = conn.transact_block(request)
    if err:
        return IS_NOT_CHANGED, os.strerror(err)
    if resp is None:
        return IS_NOT_CHANGED, "OVSDB server did not reply"
    if resp.type == ovs.jsonrpc.Message.T_ERROR or resp.error is not None:
        return IS_NOT_CHANGED, f"RPC error: {resp.error}"

    return IS_CHANGED, None

def createKey(conn: ovs.jsonrpc.Connection, key: str, val: Any) -> tuple[Changed, str | None]:
    request = ovs.jsonrpc.Message.create_request("transact", [
        "Open_vSwitch",
        {"op": "mutate", "table": "Open_vSwitch", "where": [], "mutations": [["external_ids", "insert", ["map", [[key, val]]] ]] }
        ])
    err, resp = conn.transact_block(request)
    if err:
        return IS_NOT_CHANGED, os.strerror(err)
    if resp is None:
        return IS_NOT_CHANGED, "OVSDB server did not reply"
    if resp.type == ovs.jsonrpc.Message.T_ERROR or resp.error is not None:
        return IS_NOT_CHANGED, f"RPC error: {resp.error}"

    return IS_CHANGED, None

def runModule(module: AnsibleModule):
    error, stream = ovs.stream.Stream.open_block(ovs.stream.Stream.open(module.params["remote"]))
    if error:
        return True, False, os.strerror(error)
    rpc = ovs.jsonrpc.Connection(stream)
    for i in module.params["ext_ids"]:
        req = i.split("=")
        res, exist, err = checkKey(rpc, req[0])
        if module.check_mode:
            continue
        if err:
            return True, False, err
        if exist:
            changed, err = clearKey(rpc, req[0], res)
            if err or not changed:
                return True, False, err
        changed, err = createKey(rpc, req[0], req[1])
        if err or not changed:
            return True, False, err

    return False, True, ''


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
        is_err, has_changed, result = runModule(module)
        if not is_err:
            module.exit_json(changed=has_changed, output=result)
        else:
            module.fail_json(msg=result)
    except Exception as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc())

if __name__ == '__main__':
    main()
