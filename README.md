# Ansible Role for OVN

Heads up! This role is not finished and is subject to change.

This ansible role is meant to automate the process of deploying and configuring OVN installation, making it reproducible and easy.

## Using the role

### Variables

All of the variables are defined in `defaults/main.yml` and `vars/*.yml`, and can be overridden.

Variables that you are most likely to use:

```yaml
ovn_version: "latest"

# Control the role of the host, you want to set these in hostvars or groupvars
ovn_is_controller: false
ovn_is_leader: false
ovn_is_node: false

# OVN options that correspond to OVN_CTL_OPTS, merged with ovn_central_conf_default. Can contain any available OVN_CTL_OPTS, except for cluster remote address and northd nb/sb connection address
# man ovn-ctl for more information
ovn_central_conf:
  db_nb_addr: "0.0.0.0"
  db_nb_port: "6641"
  db_sb_addr: "0.0.0.0"
  db_sb_port: "6642"
  db_nb_create_insecure_remote: "yes"
  db_sb_create_insecure_remote: "yes"
ovn_host_conf:
  ovn_controller_ssl_key: ""
  ovn_controller_ssl_cert: ""
  ovn_controller_ssl_ca_cert: ""
  ovn_controller_system_id: ""

# Variables that are passed to default ovn_controller_external_ids, used to configure ovsdb entries for ovn-controller
ovn_encap_type: "geneve"
ovn_int_bridge: "br-int"
ovn_bridge_mappings: "external:br-ext"

# List of external_ids entries that are put locally into ovsdb on each node host
# man ovn-controller for more information
ovn_controller_external_ids:
  - "ovn-remote={{ ovn_remote }}"
  - "ovn-encap-type={{ ovn_encap_type }}"
  - "ovn-encap-ip={{ ovn_encap_ip }}"
```

### Example playbook

The role must have access to privileged command execution, i.e. become. It is used inside the role to run specific tasks as privileged user.

```yaml
---
- hosts: ovn-hosts
  remote_user: ansible_user
  roles:
    - role: ovn
---
all:
  children:
    ovn-controller:
      hosts:
        ovn1.example.com:
          ovn_is_leader: true
        ovn2.example.com:
        ovn3.example.com:
      vars:
        ovn_version: "latest"
        ovn_is_controller: true
        ovn_mgmt_cidr: 
          - "10.0.0.0/8"
        ovn_central_conf:
          db_nb_addr: "{{ ovn_addr }}"
          db_sb_addr: "{{ ovn_addr }}"
    ovn-chassis:
      hosts:
        ovn-node1.example.com:
        ovn-node2.example.com:
        ovn-node3.example.com:
      vars:
        ovn_version: "latest"
        ovn_is_node: true
        ovn_mgmt_cidr:
          - "10.0.0.0/8"
        ovn_encap_type: "vxlan"
        ovn_int_bridge: "br-in"
        ovn_bridge_mappings: "internet:br-ex"
```
