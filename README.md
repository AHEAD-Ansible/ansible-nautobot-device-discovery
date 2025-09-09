Nautobot Discovery Ansible Role
Overview
The nautobot_discovery Ansible role automates the process of uploading device facts to a Nautobot instance, ensuring that devices, interfaces, IP addresses, and associated metadata are accurately represented in Nautobot. This role is designed to integrate with the networktocode.nautobot collection to interact with Nautobot's API, facilitating network automation tasks.
Features

Device Management: Creates or updates devices in Nautobot based on provided device facts, including serial number, model, platform, and location.
Interface Management: Manages device interfaces and assigns IP addresses to them.
IP Address Handling: Parses, validates, and assigns IP addresses, handling conflicts by either overwriting or allocating the next available IP.
Prefix Management: Ensures network prefixes exist in Nautobot and associates them with IP addresses.
Flexible Configuration: Supports customizable behavior for creating missing entities (locations, racks, tenants, software versions) and handling IP conflicts.
Error Handling: Configurable to continue on errors, ensuring robust execution in diverse environments.

Requirements

Ansible 2.9 or later
networktocode.nautobot collection
ansible.netcommon collection
Python with ipaddress module for IP parsing
Access to a Nautobot instance with API token

Role Variables
The role uses several variables defined in defaults/main.yml to control its behavior:

create_missing_locations: Create locations if they don't exist (default: true).
create_missing_racks: Create racks if they don't exist (default: true).
create_missing_tenants: Create tenants if they don't exist (default: true).
create_missing_software_versions: Create software versions if they don't exist (default: true).
continue_on_error: Continue execution on errors (default: true).
allow_ip_overwrite: Overwrite conflicting IP assignments (default: true).
use_next_available_on_conflict: Use the next available IP on conflict (default: false).
nautobot_namespace: Namespace for IP and prefix lookups (default: "Global").
nautobot_status: Default status for created objects (default: "Active").
nautobot_validate_certs: Validate Nautobot API certificates (default: false).
prefix_ids: Dictionary to store prefix IDs (default: {}).

Required variables:

nautobot_url: URL of the Nautobot API.
nautobot_token: API token for Nautobot authentication.
device_facts: List of device facts to process.

Dependencies

networktocode.nautobot collection
ansible.netcommon collection

Directory Structure

defaults/main.yml: Default configuration variables.
handlers/main.yml: Handlers for the role (currently empty).
meta/main.yml: Metadata for the role, including author and license.
tasks/: Core tasks for processing devices, interfaces, IPs, and prefixes.
main.yml: Entry point for the role, validates variables and loops over devices.
process_device.yml: Processes individual device facts.
process_interface.yml: Manages device interfaces and their IPs.
process_ip.yml: Handles IP address assignment and conflict resolution.
process_prefix.yml: Ensures prefixes exist in Nautobot.
parse_ip.yml: Parses IP addresses using Python's ipaddress module.
lookup_and_normalize.yml: Reusable task for looking up and normalizing API responses.
interface_ip_assignment.yml: Ensures IP addresses exist and are assigned correctly.


tests/test.yml: Test playbook for running the role on localhost.
vars/main.yml: Additional variables (currently empty).

Usage

Install Dependencies:
ansible-galaxy collection install networktocode.nautobot
ansible-galaxy collection install ansible.netcommon


Define Device Facts:Create a playbook or inventory with device_facts in the following format:
device_facts:
  - name: "device1"
    serial_number: "SN12345"
    vendor: "Cisco"
    model: "C9300"
    platform: "ios"
    location: "Site1"
    device_type: "switch"
    tenant: "Tenant1"
    software_version: "17.3.1"
    rack: "Rack1"
    position: 10
    face: "front"
    tags: ["core", "prod"]
    interfaces:
      - name: "GigabitEthernet0/1"
        type: "1000base-t"
        ip_addresses:
          - "10.0.0.1/24"
    primary_ip4: "10.0.0.1/24"


Run the Role:Include the role in your playbook:
- hosts: localhost
  roles:
    - role: nautobot_discovery
      vars:
        nautobot_url: "https://nautobot.example.com"
        nautobot_token: "your-api-token"
        device_facts: "{{ device_facts }}"


Execute the Playbook:
ansible-playbook playbook.yml



Example Playbook
- hosts: localhost
  roles:
    - role: nautobot_discovery
      vars:
        nautobot_url: "https://nautobot.example.com"
        nautobot_token: "your-api-token"
        device_facts:
          - name: "switch01"
            serial_number: "SN98765"
            vendor: "Juniper"
            model: "EX4300"
            platform: "junos"
            location: "DataCenter1"
            device_type: "switch"
            interfaces:
              - name: "ge-0/0/0"
                type: "1000base-t"
                ip_addresses:
                  - "192.168.1.1/24"
            primary_ip4: "192.168.1.1/24"

Notes

Ensure the Nautobot API is accessible and the provided token has sufficient permissions.
The role handles IP conflicts by either overwriting existing assignments or allocating the next available IP, based on allow_ip_overwrite and use_next_available_on_conflict.
Use continue_on_error to allow the role to process all devices even if some fail.
The role assumes the ipaddress Python module is available for IP parsing.

License
MIT
Author
Created by Grok, powered by xAI.