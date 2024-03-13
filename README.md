<!--
SPDX-FileCopyrightText: 2024 Max Mehl <https://mehl.mx>

SPDX-License-Identifier: GPL-3.0-only
-->

# INWX DNS Recordmaster

[![Test suites](https://github.com/mxmehl/inwx-dns-recordmaster/actions/workflows/test.yaml/badge.svg)](https://github.com/mxmehl/inwx-dns-recordmaster/actions/workflows/test.yaml)
[![REUSE status](https://api.reuse.software/badge/github.com/mxmehl/inwx-dns-recordmaster)](https://api.reuse.software/info/github.com/mxmehl/inwx-dns-recordmaster)
[![The latest version of INWX DNS recordmaster can be found on PyPI.](https://img.shields.io/pypi/v/inwx-dns-recordmaster.svg)](https://pypi.org/project/inwx-dns-recordmaster/)
[![Information on what versions of Python INWX DNS Recordmaster supports can be found on PyPI.](https://img.shields.io/pypi/pyversions/inwx-dns-recordmaster.svg)](https://pypi.org/project/inwx-dns-recordmaster/)

Manage DNS nameserver records of INWX domains via YAML files and API requests. Lightweight, version-control ready


## Overview

This tool enables customers of [INWX](https://www.inwx.de) (formerly known as InterNetworX) to manage the DNS entries/records of their domains via files. This has multiple advantages:

* Version-control of nameserver entries, therefore a good record of what has changed over time.
* Very simple copy/paste of existing entries for new domains, e.g. when a new alias domain has been added.
* Enables search/replace, e.g. of IP addresses.
* Work can be done offline and quicker, and pushed once it's done. No waiting times for the sometimes slow web interface.

Configuration of the DNS records is done in YAML files with a quite simple structure. It is compared against the "remote" state, pulled via the INWX API. If necessary, minimal API requests will be issues to align the remote state with the local configuration.


## Install

The tool depends on the following applications:

* Python 3

You can install the latest release via `pip3 install inwx-dns-recordmaster`

The tool is executable with `inwx-dnsrm`. The `--help` flag informs you about the required and available commands.


## Configuration

There are two types of configuration:

1. App configuration: INWX API login data
1. DNS records configuration: the desired state for each configured domain


### App/API configuration

You need to add your credentials for the API authentication. The file will be created automatically on first run if it doesn't exist. On Linux systems, it will be located in `~/.config/inwx-dns-recordmaster/config.toml`.

In any case, you will need to add your INWX username and password, be it of the main or a sub-account. If you use two-factor-authentication you may add the shared secret as well, although this may weaken your security. You may also want to ask the INWX support to limit the login to specific IP addresses.


### DNS records configuration

DNS records are configured in YAML files. If you have multiple domains, you can either put all definitions in one big file, or create multiple ones. The `--dns-config` flag of the program just needs to point to a directory in which at least one such file is present. Only files ending with `.yaml` or `.yml` are considered.

You can find an example DNS records configuration in the file [`records/example.com.yaml.sample`](records/example.com.yaml.sample). Here is a much shorter example:

```yaml
example.com:
  # Records configuring example.com
  .:
    - type: A
      content: "192.168.13.37"
    - type: MX
      content: "my.mailhost.tld"
      prio: 10  # priority of MX record, relevant with multiple MX
  # *.example.com
  "*":
    - type: A
      content: "192.168.13.37"
  # cloud.example.com
  cloud:
    - type: CNAME
      content: cloudprovider.tld
      ttl: 86400  # long TTL
```

Please note that the general idea of this program is that ALL records are managed locally. In the above example, it would delete the `NS` records of the domain which is a bad idea.

However, there are default and extendable exceptions:

* By default, records of the type `SOA` are not considered as they change upon each change and are handled well by INWX. You can add additional record types with the `--ignore-types` argument if you don't want to handle them.
* You can also blatantly ignore records that exist at INWX but not in your local configuration, using the `--preserve-remote` flag. This way, you only *update existing* and *add new* records, but don't *delete unconfigured* records at INWX.


## Run the program

You can execute the program using the command `inwx-dnsrm`. `inwx-dnsrm --help` shows all available arguments and options.

Some examples:

* `inwx-dnsrm -c records/`: read the DNS records from the `records/` directory, match them with the remote, and call the API to add, update, and delete entries for each locally configured domain.
* `inwx-dnsrm -c records/ -d example.com`: like the above, but only check the domain `example.com` and ignore all other locally configured. If you have many domains, this may speed up operations.
* `inwx-dnsrm -c records/ -p`: run normally, but do not delete nameserver entries at INWX which are not configured locally.
* `inwx-dnsrm -c records/ --dry`: run the whole program but do not make any changes at INWX. Very helpful if you just configure a new domain.


## Contribute and Develop

Contributions are welcome! The development is easiest with `poetry`: `poetry install` and `poetry run inwx-dnsrm` will get you started.


## Troubleshooting


### Debug and dry-run

The `--debug` flag will bring you a long way. If you want to create an issue with this project, please provide a debug log, it will be of great help!

Also, `--dry` is recommended to play around with the program and avoid breaking your productive configuration.


### Simulate API response

If you want to work locally or want to modify the INWX API response, you can simulate it. The `--api-response` flag takes a JSON file as argument that basically contains the reponse of the INWX API about the remote state of a domain's nameserver entries.

This could look like the following:

```json
{
  "roId": 123456,
  "domain": "example.com",
  "type": "MASTER",
  "cleanup": {
    "status": "OK",
    "tstamp": 1513779810
  },
  "count": 4,
  "record": [
    {
      "id": 1402323103,
      "name": "example.com",
      "type": "A",
      "content": "185.26.156.148",
      "ttl": 3600,
      "prio": 0
    },
    {
      "id": 1404343107,
      "name": "www.example.com",
      "type": "A",
      "content": "185.26.156.148",
      "ttl": 3600,
      "prio": 0
    },
    {
      "id": 209645684,
      "name": "example.com",
      "type": "NS",
      "content": "ns.inwx.de",
      "ttl": 86400,
      "prio": 0
    },
    {
      "id": 2094329683,
      "name": "example.com",
      "type": "SOA",
      "content": "ns.inwx.de hostmaster.inwx.de 2024030422 10800 3600 604800 3600",
      "ttl": 86400,
      "prio": 0
    }
  ]
}
```

In order to get this output from an existing domain, you can run the program with the `--debug` flag and search for the line starting with `Response (nameserver.info):`.


## License

The main license of this project is the GNU General Public License 3.0, no later version (`GPL-3.0-only`), Copyright Max Mehl.

There may be components under different, but compatible licenses and from different copyright holders. The project is [REUSE](https://reuse.software) compliant which makes these portions transparent. You will find all used licenses in the `LICENSES` directory.
