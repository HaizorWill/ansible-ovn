#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import os
import time
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
import traceback
import ovs.stream
import ovs.dirs
import ovs.poller
import ovs.jsonrpc

def checkKey(conn: ovs.jsonrpc.Connection, key: str):
    request = ovs.jsonrpc.Message.create_request("transact", [
        "Open_vSwitch",
        {"op": "select", "table": "Open_vSwitch", "where": [], "columns": ["external_ids"] }
        ])
    err, resp = conn.transact_block(request)
    if err:
        return False, os.strerror(err)
    if resp is None:
        return False, "OVSDB server did not reply"
    if resp.type == ovs.jsonrpc.Message.T_ERROR or resp.error is not None:
        return False, f"RPC error: {resp.error}"
    ids = dict(resp.result[0]["rows"][0]["external_ids"][1])
    if ids.get(key):
        print(ids)
        return True, None
    return False, None

def clearKey():
   return 

def runModule(module: AnsibleModule):
    error, stream = ovs.stream.Stream.open_block(ovs.stream.Stream.open(module.params["remote"]))
    if error:
        return True, False, os.strerror(error)
    rpc = ovs.jsonrpc.Connection(stream)
    for i in module.params["ext_ids"]:
        req = i.split("=")
        exist, err = checkKey(rpc, req[0])
        if module.check_mode:
            continue
        if err:
            return True, False, err
        if exist:
            clearKey()

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
