# Learning tracks by domain

Browse a domain to find its editable TOML tracks. These folders match the domains
in the app's track picker. Track IDs stay the same when a file moves.

[Ethical Hacking Foundations](foundations/ethical-hacking-foundations.toml) is a
separate introductory track. The [offensive security folder](offensive/) contains
the focused web, API, network, directory, red-team, and research tracks.

| Domain | Tracks | Subjects |
| --- | ---: | --- |
| [Cyber foundations](foundations/) | 2 | Ethical hacking, networking |
| [Offensive security](offensive/) | 6 | Web, APIs, network penetration testing, Active Directory, red teaming, vulnerability research |
| [Defensive security](defensive/) | 5 | Detection, SOC, forensics and incident response, threat hunting, vulnerability management |
| [Security engineering](engineering/) | 5 | Cloud, containers, DevSecOps, architecture and governance, AI applications |
| [Specialist security](specialist/) | 6 | Reverse engineering, malware, mobile, cryptography, wireless and IoT, industrial systems |
| [Hands-on labs](practice/) | 1 | Verified security exercises |
| [Projects](projects/) | 3 | Home hack lab, Python file tool, Blender scene |

Install by ID from any directory:

```sh
ascend pack install api-security
ascend mission start api-security
```

To inspect or install an edited file from the repository root, use its domain path:

```sh
ascend pack diff packs/community/offensive/api-security.toml
ascend pack install packs/community/offensive/api-security.toml
```

`catalog.json` holds curriculum metadata. `registry.json` maps stable IDs to these
paths and records checksums; regenerate it with `python scripts/build_registry.py`
after changing a pack. See [the pack format](../../docs/pack-format.md) and
[contribution guide](../../CONTRIBUTING.md) for authoring details.

All supplied tracks remain drafts until reviewed. The matching editable cyber
export is in [tracks/cyber-tracks](../../tracks/cyber-tracks/).
