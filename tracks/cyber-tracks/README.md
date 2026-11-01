# Public cyber catalog, release 4

24 skill tracks cover foundations, offensive and defensive security, red teaming,
SOC, Active Directory, cloud, containers, DevSecOps, DFIR, threat hunting, malware,
mobile, APIs, cryptography, wireless/IoT, OT/ICS, architecture/GRC, vulnerability
management, bug bounty and AI application security. An eight-task verified practice
project and the public home lab (including Bandit 0–12) are also included.
These packs require the current Ascend release with `lab` and `ctf` verifiers;
copying TOML files does not upgrade an older server.
Individual pack versions are independent: four original tracks remain v3, defense
and home lab are v4, and new specialist/practice packs are v1.

Use `handbook.pdf` and `deployment-guide.pdf` in the ZIP for the complete LaTeX-authored
assessment rubric, source register, catalog, installation, timers, lab proof bridge
and environment requirements. Source files and generated pack definitions live in
the repository. Every supplied curriculum remains an unreviewed draft. Alignment
with established courses and frameworks does not prove learner outcomes.

```sh
ascend pack install verified-security-lab
ascend mission start verified-security-lab
ascend lab start verified-security-lab:lab-readiness
```

On an existing profile, back up private edits and compare before installing:

```sh
ascend pack diff packs/community/home-hack-lab.toml
ascend pack install packs/community/home-hack-lab.toml
```

Earlier IDs and completions are preserved; they are not retroactively certified.
Changes reset review and execution trust. Native and CTF tasks need passing evidence;
file checks require review of the actual reasoning and result. Some environments
require Windows VMs, hosted tenants or mobile devices and cannot run on the Pi.
The old archives remain available for compatibility.
