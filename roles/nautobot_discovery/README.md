# Ansible Role: Nautobot Discovery

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The `nautobot_discovery` role provides a comprehensive, idempotent solution for discovering and synchronizing network device information with [Nautobot](https://nautobot.readthedocs.io/) via its REST API. This role processes device facts collected from network infrastructure and automatically creates or updates Nautobot objects including devices, interfaces, IP addresses, prefixes, VLANs, VRFs, locations, and related entities.

### Key Features

- **Idempotent Operations**: Safe to run multiple times; only creates or updates when changes are detected
- **Bulk API Operations**: Intelligent chunking for URL length and payload size optimization
- **Zero External Dependencies**: Pure Ansible implementation using built-in `uri` module
- **Relationship Handling**: Automatic resolution of foreign key relationships (devices, locations, VRFs, etc.)
- **Schema Validation**: Comprehensive validation of input data before API operations
- **Error Handling**: Configurable error handling with retry logic and graceful failure modes
- **Hierarchical Support**: Handles hierarchical objects like location types with parent-child relationships
- **Custom Filter Plugins**: Python-based filters for complex data transformations

## Requirements

### Ansible

- **Ansible**: 2.10 or higher
- **Python**: 3.6+ (for filter plugins)

### Nautobot

- **Nautobot**: v2.0+ recommended
- **API Access**: Valid API token with appropriate permissions

### Collections

- `ansible.utils` (for `items2dict` filter)
- `community.general` (optional, for additional utilities)

### Network Access

- HTTPS access to Nautobot API endpoint
- Valid SSL certificate (or disable validation with `nautobot_validate_certs: false`)

## Installation

### Using Ansible Galaxy

```bash
ansible-galaxy install git+https://github.com/your-org/ansible_nautobot_discovery.git
```

### Manual Installation

```bash
cd /path/to/your/roles
git clone https://github.com/your-org/ansible_nautobot_discovery.git nautobot_discovery
```

## Role Variables

### Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `nautobot_url` | string | Base URL of Nautobot instance (e.g., `https://nautobot.example.com`) |
| `nautobot_token` | string | API token for authentication (store in Ansible Vault) |
| `device_facts` | list[dict] | List of device dictionaries with discovery facts (see [Device Facts Schema](#device-facts-schema)) |

### Optional Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `nautobot_namespace` | string | `"Global"` | Default namespace for IPAM objects (prefixes, IPs, VRFs) |
| `nautobot_status` | string | `"Active"` | Default status for newly created objects |
| `nautobot_validate_certs` | boolean | `false` | Validate SSL certificates for API requests |
| `create_missing_locations` | boolean | `true` | Automatically create locations if they don't exist |
| `create_missing_racks` | boolean | `true` | Automatically create racks if they don't exist |
| `create_missing_tenants` | boolean | `true` | Automatically create tenants if they don't exist |
| `create_missing_software_versions` | boolean | `true` | Automatically create software versions if they don't exist |
| `default_location_type` | string | `"Datacenter"` | Default location type name for new locations |
| `continue_on_error` | boolean | `false` | Continue execution even if individual tasks fail |
| `allow_ip_overwrite` | boolean | `true` | Allow overwriting existing IP address assignments |
| `use_next_available_on_conflict` | boolean | `false` | Use next available IP on conflict (future feature) |
| `rack_u_height` | integer | `42` | Default rack unit height |
| `rack_type` | string | `"4-post-frame"` | Default rack type |
| `rack_width` | integer | `19` | Default rack width (inches) |
| `nautobot_discovery_bulk_chunk_size` | integer | `10` | Number of objects per bulk operation chunk |
| `nautobot_discovery_retry_attempts` | integer | `0` | Number of retry attempts for failed API calls |
| `nautobot_discovery_continue_on_error` | boolean | `false` | Alias for `continue_on_error` |
| `nautobot_discovery_debug` | boolean | `false` | Enable debug output |

### Pre-populated ID Maps

These variables allow you to provide pre-resolved IDs to avoid lookups:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `prefix_ids` | dict | `{}` | Map of prefix strings to Nautobot IDs |
| `vrf_ids` | dict | `{}` | Map of VRF names to Nautobot IDs |
| `tenant_ids` | dict | `{}` | Map of tenant names to Nautobot IDs |
| `vlan_ids` | dict | `{}` | Map of VLAN names to Nautobot IDs |

## Device Facts Schema

The `device_facts` variable must be a list of dictionaries, each representing a network device. The schema is validated before processing.

### Required Fields

- `name` (string): Device hostname or identifier
- `interfaces` (list[dict]): List of interface dictionaries

### Interface Schema

Each interface dictionary must contain:

- `name` (string): Interface name (e.g., `GigabitEthernet0/0`)
- `ip_addresses` (list[string]): List of IP addresses in CIDR notation (e.g., `["192.168.1.1/24"]`)

### Optional Device Fields

| Field | Type | Description |
|-------|------|-------------|
| `location` | string | Location name (will be created if `create_missing_locations: true`) |
| `manufacturer` | string | Manufacturer name (e.g., `"Cisco"`) |
| `platform` | string | Platform/OS name (e.g., `"Cisco IOS"`) |
| `role` | string | Device role name (e.g., `"Router"`) |
| `device_type` | string | Device type/model (e.g., `"ASR1001"`) |
| `serial_number` | string | Device serial number |
| `software_version` | string | Software/firmware version |
| `primary_ip4` | string | Primary IPv4 address in CIDR notation |
| `primary_ip6` | string | Primary IPv6 address in CIDR notation |
| `vlans` | list[string] | List of VLAN names associated with device |
| `vrfs` | list[string] | List of VRF names associated with device |
| `tags` | list[string] | List of tags to apply to device |
| `custom_fields` | dict | Custom field values |

### Optional Interface Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Interface type (e.g., `"1000base-t"`, `"SFP+ (10GE)"`) |
| `enabled` | boolean | Interface enabled state (default: `true`) |
| `status` | string | Interface status (default: `"Active"`) |
| `description` | string | Interface description |
| `mac_address` | string | MAC address |
| `mtu` | integer | MTU value |
| `mode` | string | Interface mode (e.g., `"access"`, `"tagged"`) |
| `vrf` | string | VRF name for this interface |
| `vlan` | string | VLAN name for this interface |
| `tags` | list[string] | Interface-specific tags |

### Example Device Facts

```yaml
device_facts:
  - name: "router1.example.com"
    location: "Datacenter1"
    manufacturer: "Cisco"
    platform: "Cisco IOS XE"
    role: "Core Router"
    device_type: "ASR1001-X"
    serial_number: "ABC123456"
    software_version: "16.09.04"
    primary_ip4: "192.168.1.1/24"
    interfaces:
      - name: "GigabitEthernet0/0"
        type: "1000base-t"
        enabled: true
        status: "Active"
        description: "Uplink to ISP"
        ip_addresses:
          - "192.168.1.1/24"
        vrf: "global"
      - name: "GigabitEthernet0/1"
        type: "1000base-t"
        enabled: true
        status: "Active"
        description: "Internal network"
        ip_addresses:
          - "10.0.0.1/24"
        vrf: "internal"
    vlans:
      - "internal"
      - "guest"
    vrfs:
      - "global"
      - "internal"
    tags:
      - "production"
      - "core-network"
```

## Dependencies

None. This role is self-contained and uses only Ansible built-in modules and custom filter plugins.

## Architecture

### Design Principles

1. **Idempotency First**: All operations are designed to be safely repeatable
2. **Zero Variable Collisions**: Task includes use isolated variable namespaces
3. **Bulk Operations**: Intelligent chunking for optimal API performance
4. **Relationship Resolution**: Automatic handling of foreign key dependencies
5. **Error Resilience**: Configurable error handling with retry logic

### Task Flow

```
main.yml
├── Schema Validation
├── API Configuration (set_api_globals.yml)
├── Namespace Preparation (prepare_namespace.yml)
├── Location Type Preparation (prepare_location_types.yml)
├── Location Preparation (prepare_locations.yml)
└── [Future: Manufacturers, Tenants, Tags, Roles, Platforms, Device Types]
    └── [Future: Devices, VLANs, VRFs, Interfaces, Prefixes, IPs]
```

### Core Task Files

#### `api_upsert.yml`
The central upsert orchestration task that:
- Loads endpoint definitions from `vars/endpoints.yml`
- Performs lookup of existing objects
- Classifies objects as creates or updates
- Executes bulk POST (create) and PATCH (update) operations
- Merges results and cleans up temporary facts

**Input Variables:**
- `endpoint_name`: Key in `endpoints.yml` (e.g., `"namespaces"`)
- `desired_bodies`: List of desired object states
- `result_var`: Variable name to store final results
- `override_lookup_key`: (optional) Override default lookup key

#### `api_lookup.yml`
Performs efficient bulk lookups of existing Nautobot objects:
- Builds filter parameters from desired bodies
- Chunks filters to respect URL length limits (1500 chars)
- Executes GET requests with proper filtering
- Flattens and aggregates results

**Input Variables:**
- `lookup_endpoint`: Endpoint configuration dict
- `lookup_desired_bodies`: List of desired objects
- `lookup_unique_keys`: Keys to use for matching
- `lookup_result_var`: Variable name for results

#### `api_post_patch.yml`
Executes bulk POST or PATCH operations:
- Handles JSON serialization
- Manages status codes (201 for POST, 200 for PATCH)
- Extracts and normalizes response data
- Supports error handling with `continue_on_error`

**Input Variables:**
- `method`: `"POST"` or `"PATCH"`
- `api_endpoint`: Endpoint configuration dict
- `bodies`: List of objects to create/update
- `postpatch_result_var`: Variable name for results

## Filter Plugins

The role includes a comprehensive Python filter plugin (`filter_plugins/nautobot_filters.py`) with the following filters:

### Data Transformation

- `nautobot_extract_prefixes`: Extract unique prefixes from device interfaces
- `extract_parent_prefixes`: Extract parent networks from IP addresses
- `get_interface_for_ip`: Find interface owning a specific IP address

### Validation

- `nautobot_is_ip`: Validate IPv4/IPv6 addresses with optional CIDR notation

### API Query Building

- `build_lookup_filters`: Build filter parameters for GET requests
- `build_filter_param`: Build URL-encoded filter parameter string
- `resolve_unique_keys`: Resolve unique keys from endpoint configuration

### Object Matching

- `build_existing_map`: Index existing objects by unique key(s)
- `classify_upserts`: Classify objects as creates or updates
- `smart_dict_diff`: Compute diff with relationship ID comparison
- `dict_diff`: Simple field-level diff

### Body Building

- `build_prefix_bodies`: Build prefix API request bodies
- `build_ip_upsert_bodies_from_device`: Build IP address bodies from device facts
- `build_vlan_bodies`: Build VLAN API request bodies
- `build_vrf_bodies`: Build VRF API request bodies
- `build_hierarchical_bodies`: Build hierarchical object bodies (location types)
- `build_id_list`: Build list of `{'id': uuid}` for relationships

### Chunking

- `chunk_list`: Split list into fixed-size chunks
- `smart_chunk_for_lookup`: Chunk filters by URL length (default 1500 chars)
- `smart_chunk_for_payload`: Chunk bodies by JSON payload size (default 1MB)
- `chunk_prefix_bodies`: Chunk prefix bodies by GET URL length

### Result Merging

- `merge_upsert_results`: Merge existing, created, and updated objects

## Endpoint Configuration

Endpoint definitions are stored in `vars/endpoints.yml` and define:

- **API Path**: REST API endpoint path
- **Required/Optional Fields**: Field validation rules
- **Lookup Keys**: Keys used for object matching
- **Unique Constraints**: Composite unique keys (e.g., `[location, vid]` for VLANs)
- **Relationships**: Foreign key mappings to other object types
- **Object Type**: Nautobot content type identifier

### Supported Endpoints

- `namespaces` - IPAM namespaces
- `manufacturers` - Device manufacturers
- `platforms` - Device platforms
- `device_roles` - Device roles
- `device_types` - Device type models
- `tenants` - Tenancy tenants
- `software_versions` - Software/firmware versions
- `location_types` - Location type hierarchy
- `locations` - Physical locations
- `racks` - Equipment racks
- `tags` - Tags for object labeling
- `devices` - Network devices
- `interfaces` - Device interfaces
- `ip_addresses` - IP addresses
- `prefixes` - IP network prefixes
- `vrfs` - Virtual Routing and Forwarding instances
- `vlans` - VLANs
- `ip_address_to_interface` - IP-to-interface assignments
- `vrf_prefix_assignments` - VRF prefix assignments
- `vrf_device_assignments` - VRF device assignments

## Usage Examples

### Basic Usage

```yaml
---
- hosts: localhost
  gather_facts: false
  vars:
    nautobot_url: "https://nautobot.example.com"
    nautobot_token: "{{ vault_nautobot_token }}"
    device_facts:
      - name: "switch1"
        location: "Datacenter1"
        interfaces:
          - name: "GigabitEthernet0/1"
            ip_addresses:
              - "10.0.0.1/24"
  roles:
    - nautobot_discovery
```

### With Vault-Encrypted Token

```yaml
---
- hosts: localhost
  gather_facts: false
  vars_files:
    - vault.yml  # Contains nautobot_token
  vars:
    nautobot_url: "https://nautobot.example.com"
    device_facts: "{{ discovered_devices }}"
  roles:
    - nautobot_discovery
```

### Advanced Configuration

```yaml
---
- hosts: localhost
  gather_facts: false
  vars:
    nautobot_url: "https://nautobot.example.com"
    nautobot_token: "{{ vault_nautobot_token }}"
    nautobot_namespace: "Production"
    nautobot_status: "Active"
    nautobot_validate_certs: true
    create_missing_locations: true
    default_location_type: "Site"
    continue_on_error: false
    device_facts:
      - name: "router1"
        location: "HQ-Datacenter"
        manufacturer: "Cisco"
        platform: "Cisco IOS XE"
        role: "Core Router"
        device_type: "ASR1001-X"
        serial_number: "ABC123"
        software_version: "16.09.04"
        primary_ip4: "192.168.1.1/24"
        interfaces:
          - name: "GigabitEthernet0/0"
            type: "1000base-t"
            enabled: true
            status: "Active"
            description: "Uplink"
            ip_addresses:
              - "192.168.1.1/24"
            vrf: "global"
        vlans:
          - "internal"
          - "guest"
        tags:
          - "production"
          - "critical"
  roles:
    - nautobot_discovery
```

### Integration with Network Discovery

```yaml
---
- hosts: network_devices
  gather_facts: true
  tasks:
    - name: Collect device facts
      set_fact:
        discovered_devices: "{{ discovered_devices | default([]) + [{
          'name': inventory_hostname,
          'location': hostvars[inventory_hostname]['location'],
          'manufacturer': ansible_net_vendor,
          'platform': ansible_net_model,
          'serial_number': ansible_net_serialnum,
          'interfaces': ansible_net_interfaces | dict2items | map('combine', {
            'name': item.key,
            'ip_addresses': item.value.ipv4 | default([]) | map(attribute='address') | map('regex_replace', '^(.*)$', '\\1/24') | list
          }) | list
        }] }}"

- hosts: localhost
  gather_facts: false
  vars:
    nautobot_url: "https://nautobot.example.com"
    nautobot_token: "{{ vault_nautobot_token }}"
    device_facts: "{{ hostvars | dict2items | map(attribute='value.discovered_devices') | flatten | default([]) }}"
  roles:
    - nautobot_discovery
```

## Best Practices

### Security

1. **Store API Tokens in Vault**: Never hardcode tokens in playbooks
   ```yaml
   # vault.yml (encrypted with ansible-vault)
   vault_nautobot_token: "your-token-here"
   ```

2. **Use Least Privilege**: Grant API token only necessary permissions

3. **Validate Certificates in Production**: Set `nautobot_validate_certs: true` for production

4. **Use `no_log` for Sensitive Data**: When debugging, use `no_log: true` for tasks with tokens

### Performance

1. **Batch Operations**: The role automatically chunks operations, but you can tune `nautobot_discovery_bulk_chunk_size` if needed

2. **Pre-populate IDs**: Provide `prefix_ids`, `vrf_ids`, etc. to avoid lookups

3. **Filter Device Facts**: Only include devices that need updates

4. **Use Fact Caching**: Enable Ansible fact caching for repeated runs

### Idempotency

1. **Run in Check Mode First**: Use `--check` to preview changes
   ```bash
   ansible-playbook playbook.yml --check
   ```

2. **Use Tags for Selective Execution**: Tag specific tasks for targeted updates
   ```bash
   ansible-playbook playbook.yml --tags "devices,interfaces"
   ```

3. **Validate Input Data**: Ensure `device_facts` conforms to schema before running

### Error Handling

1. **Enable Retries**: Set `nautobot_discovery_retry_attempts: 3` for transient failures

2. **Use `continue_on_error` Carefully**: Only enable for non-critical operations

3. **Monitor API Rate Limits**: Adjust chunk sizes if hitting rate limits

4. **Review Failed Tasks**: Use `--verbose` to debug failures
   ```bash
   ansible-playbook playbook.yml -vvv
   ```

## Troubleshooting

### Common Issues

#### Schema Validation Failures

**Error**: `device_facts must be a list`

**Solution**: Ensure `device_facts` is a YAML list, not a dictionary:
```yaml
# Correct
device_facts:
  - name: "device1"
    interfaces: [...]

# Incorrect
device_facts:
  device1:
    interfaces: [...]
```

#### Invalid IP Addresses

**Error**: `has invalid IPs (must be valid IPv4 with optional /0-32 prefix)`

**Solution**: Ensure all IP addresses include CIDR notation:
```yaml
# Correct
ip_addresses:
  - "192.168.1.1/24"
  - "10.0.0.1/32"

# Incorrect
ip_addresses:
  - "192.168.1.1"  # Missing prefix
```

#### API Authentication Failures

**Error**: `401 Unauthorized`

**Solution**: 
- Verify `nautobot_token` is correct
- Check token permissions in Nautobot
- Ensure token hasn't expired

#### SSL Certificate Errors

**Error**: `SSL certificate verification failed`

**Solution**: 
- Set `nautobot_validate_certs: false` for testing (not recommended for production)
- Ensure Nautobot certificate is valid and trusted
- Add certificate to system trust store

#### URL Length Exceeded

**Error**: `414 URI Too Long`

**Solution**: The role automatically chunks lookups, but if issues persist:
- Reduce number of objects per lookup
- Check `smart_chunk_for_lookup` filter configuration

### Debugging

#### Enable Verbose Output

```bash
# Basic verbose
ansible-playbook playbook.yml -v

# More verbose (SSH debugging)
ansible-playbook playbook.yml -vvv

# Maximum verbosity
ansible-playbook playbook.yml -vvvv
```

#### Check Mode (Dry Run)

```bash
ansible-playbook playbook.yml --check --diff
```

#### Test Individual Tasks

```bash
# Start at specific task
ansible-playbook playbook.yml --start-at-task="Upsert namespace"

# Run specific tags
ansible-playbook playbook.yml --tags "prepare_namespace"
```

#### Inspect Variables

Add debug tasks to inspect variable values:

```yaml
- name: Debug device_facts
  debug:
    var: device_facts

- name: Debug API response
  debug:
    var: final_namespace
```

## Development

### Project Structure

```
nautobot_discovery/
├── defaults/
│   └── main.yml              # Default variables
├── filter_plugins/
│   └── nautobot_filters.py   # Custom Python filters
├── handlers/
│   └── main.yml              # Handlers (currently empty)
├── meta/
│   └── main.yml              # Galaxy metadata
├── tasks/
│   ├── main.yml              # Main entry point
│   ├── api_lookup.yml        # Bulk lookup logic
│   ├── api_post_patch.yml    # POST/PATCH operations
│   ├── api_upsert.yml        # Upsert orchestration
│   ├── prepare_namespace.yml # Namespace preparation
│   ├── prepare_location_types.yml # Location type hierarchy
│   ├── prepare_locations.yml # Location preparation
│   ├── set_api_globals.yml   # API configuration
│   └── upsert_vlans.yml      # VLAN upsert (example)
├── tests/
│   ├── inventory             # Test inventory
│   └── test.yml              # Test playbook
├── vars/
│   ├── endpoints.yml         # Endpoint definitions
│   └── main.yml              # Variable schemas
└── README.md                 # This file
```

### Adding New Endpoints

1. Add endpoint definition to `vars/endpoints.yml`
2. Create preparation task file (e.g., `prepare_manufacturers.yml`)
3. Include task in `tasks/main.yml`
4. Test with sample data

### Extending Filter Plugins

1. Add function to `filter_plugins/nautobot_filters.py`
2. Register in `FilterModule.filters()` method
3. Document function with docstring
4. Test with sample data

### Testing

```bash
# Syntax check
ansible-playbook tests/test.yml --syntax-check

# Lint
ansible-lint roles/nautobot_discovery/

# Test with sample inventory
ansible-playbook tests/test.yml -i tests/inventory
```

## License

MIT License - see LICENSE file for details.

## Author Information

**Brian Nelson**

- Role created for automated Nautobot discovery and synchronization
- Contributions welcome via pull requests

## Support

For issues, questions, or contributions:

1. Check existing [GitHub Issues](https://github.com/your-org/ansible_nautobot_discovery/issues)
2. Create a new issue with:
   - Ansible version
   - Nautobot version
   - Relevant playbook snippets (sanitized)
   - Error messages
3. Submit pull requests for improvements

## Changelog

### Version 1.0.0 (Current)

- Initial release
- Core upsert functionality
- Namespace, location type, and location support
- Comprehensive filter plugins
- Schema validation
- Bulk operation optimization

### Planned Features

- Device, interface, and IP address upsert
- VLAN and VRF management
- Prefix management
- Manufacturer, platform, and device type support
- Tenant and tag management
- Rack management
- Software version tracking
- Primary IP assignment
- Interface-to-IP assignments
- VRF assignments

---

**Note**: This role is actively developed. Some features referenced in task files may be commented out pending implementation. Check the task files for current status.
