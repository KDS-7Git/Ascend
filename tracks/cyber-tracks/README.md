# Public cyber catalog, release 4

24 skill tracks cover foundations, offensive and defensive security, red teaming,
SOC, Active Directory, cloud, containers, DevSecOps, DFIR, threat hunting, malware,
mobile, APIs, cryptography, wireless/IoT, OT/ICS, architecture/GRC, vulnerability
management, bug bounty and AI application security. An eight-task verified practice
project and the public home lab (including Bandit) are also included.
These packs require the current Ascend release with `lab` and `ctf` verifiers;
copying TOML files does not upgrade an older server.
Individual pack versions are independent: the four original technical tracks and
Ethical Hacking Foundations are v4, defense is v5, the other specialist tracks are
v2, and the home lab/practice packs retain their versions. The guidance update
preserves task IDs while clarifying instructions and completion claims.

Browse the editable tracks by domain:

| Domain | Tracks |
| --- | ---: |
| [Cyber foundations](packs/community/foundations/) | 2 |
| [Offensive security](packs/community/offensive/) | 6 |
| [Defensive security](packs/community/defensive/) | 5 |
| [Security engineering](packs/community/engineering/) | 5 |
| [Specialist security](packs/community/specialist/) | 6 |
| [Hands-on labs](packs/community/practice/) | 1 |
| [Home lab project](packs/community/projects/) | 1 |

Use `handbook.pdf` and `deployment-guide.pdf` in the ZIP for the complete LaTeX-authored
assessment rubric, source register, catalog, installation, timers, lab proof bridge
and environment requirements. Source files and generated pack definitions live in
the repository. Every supplied curriculum remains an unreviewed draft. Alignment
with established courses and frameworks does not prove learner outcomes.

Concrete practice inputs are organized by track under [materials](materials/).
The web app offers one ZIP per track, including the report helper and license.
The public archive also includes those standalone ZIPs under `learning-materials/`
for offline use. Read setup requirements before timing: a synthetic fixture or
tabletop does not demonstrate a real cloud account, directory, device or cluster.
Optional reference links explain concepts; they are separate from actual lab files.

```sh
ascend pack install verified-security-lab
ascend mission start verified-security-lab
ascend lab start verified-security-lab:lab-readiness
```

On an existing profile, back up private edits and compare before installing:

```sh
ascend pack diff packs/community/projects/home-hack-lab.toml
ascend pack install packs/community/projects/home-hack-lab.toml
```

Earlier IDs and completions are preserved; they are not retroactively certified.
Changes reset review and execution trust. Native and CTF tasks need passing evidence;
file checks require review of the actual reasoning and result. Some environments
require Windows VMs, hosted tenants or mobile devices and cannot run on the Pi.
The old archives remain available for compatibility.
