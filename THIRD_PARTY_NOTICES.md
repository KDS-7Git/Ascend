# Third-party credits and notices

Ascend's [MIT license](LICENSE) covers the original Ascend code and materials.
Third-party fonts, lab content, software, and datasets retain their own copyrights
and licenses. Thank you to the authors and contributors of the projects below.
These credits do not imply their endorsement of Ascend.

## Bundled font

**Inter Variable**, by Rasmus Andersson and The Inter Project Authors, is bundled
unchanged at `web/fonts/InterVariable.woff2`.

- Source: <https://github.com/rsms/inter>
- Copyright (c) 2016 The Inter Project Authors.
- License: SIL Open Font License 1.1. The complete copyright and license notice
  is preserved in [web/fonts/OFL.txt](web/fonts/OFL.txt).
- The wheel also includes the font and its notice under `ascend/web/fonts/`.

Distribution metadata uses `MIT AND OFL-1.1` to account for the bundled font;
Ascend's original code and materials remain MIT licensed.

## Integrated lab projects

Ascend ships its adapters, recipe definitions, instructions, and synthetic
controls. The upstream applications, selected source files, datasets, and
container images described here are acquired from upstream when a lab is used.
Recipe manifests record the selected revisions, download sizes, and SHA-256
hashes. Original upstream MIT notices are also reproduced below.

### BGP Labs

- Author: Ivan Pepelnjak and BGP Labs contributors.
- Source: <https://github.com/bgplab/bgplab/tree/217fbef2cd5a2c200a3d5e56b3be5defaf1fbc67>
- License: MIT; see the complete pinned notice below.
- Use: the single-session, session-protection, and prefix-filter exercises inform
  Ascend's local FRR labs. The export-policy exercise uses the pinned prefix
  topology as a reference.
- Ascend changes: local container lifecycle, FRR configuration, checks, and
  evidence handling; the export-policy task uses Ascend's own declarative policy
  format, synthetic cases, and checker. These adaptations do not run the upstream
  netlab grader. The selected topology, validation files, and notice are fetched
  without modification where the recipe requires them.

**FRRouting (FRR)**, by the FRRouting contributors, supplies the routing software
for the local BGP containers. FRR 8.4.1 is GPL-2.0-or-later. The recipes fetch
[COPYING](https://github.com/FRRouting/frr/blob/70151e264bbb697a10fed711aa8c937d4f0009b1/COPYING)
and link the selected
[source revision](https://github.com/FRRouting/frr/tree/70151e264bbb697a10fed711aa8c937d4f0009b1).
Ascend configures the upstream image without bundling or modifying FRR binaries.
The image's other packages retain their individual licenses.

### VAmPI

- Author: erev0s and VAmPI contributors.
- Source: <https://github.com/erev0s/VAmPI/tree/f16052dce83f05847133ec98f01c5193a41de7d8>
- License: MIT; see the complete pinned notice below.
- Use: the upstream API runs in vulnerable and corrected configurations for the
  object-ownership comparison lab.
- Ascend changes: launch settings, a fixed-destination loopback proxy, resource
  bounds, persistence, and independent comparison probes. Ascend does not bundle
  or patch the upstream application source; its license is fetched into the lab
  directory as `UPSTREAM-LICENSE.txt`.

### OWASP WrongSecrets

- Authors: the OWASP WrongSecrets project team and contributors.
- Source: <https://github.com/OWASP/wrongsecrets/tree/7144c57fb15708f9486dab83d536448302d4e51b>
- License: [GNU AGPL version 3](https://github.com/OWASP/wrongsecrets/blob/7144c57fb15708f9486dab83d536448302d4e51b/LICENSE).
- Use: challenges 1, 2, and 3 from v1.14.2 and their selected Java sources,
  application configuration, and Dockerfile.
- Ascend changes: container settings, a proxy limiting the exposed routes, local
  answer checks, and evidence handling. The upstream application JAR and selected
  source files are not modified or bundled in Ascend. The lab fetches its full
  license alongside those source files; the local practice page links the pinned
  upstream source and license.

The source link identifies the upstream application. If you distribute its
image or a modified build, retain the AGPL notices and provide the corresponding
source required for that build; a credit link alone does not fulfill those
obligations.

### Security Datasets

- Authors: Open Threat Research Forge (OTRF), Roberto Rodriguez, and project
  contributors. The pinned copyright notice names Open Threat Research Forge.
- Source: <https://github.com/OTRF/Security-Datasets/tree/d9d40ef123d2c87d5d3df28c96bcab4f0faccc87>
- Use: `datasets/atomic/linux/discovery/host/sh_arp_cache.zip`, containing
  `sh_arp_cache_2020-11-10074812.log`, for the Linux audit discovery exercise.
- Ascend changes: the selected log is extracted unchanged as `evidence.log`;
  instructions, questions, the benign control, and checks are authored by Ascend.
  The original log is downloaded on demand and is not bundled in Ascend.
- License evidence: the pinned root `LICENSE` is MIT and is reproduced below.
  The upstream README also contains GPL language. Ascend discloses this unresolved
  inconsistency and retains the pinned notice as `UPSTREAM-LICENSE.txt`; the root
  MIT notice should not be treated as a determination of every dataset's terms.

## Other catalog references

These projects are credited as research references or planned integrations.
Their code, course content, VMs, datasets, APKs, and model weights are not bundled
in Ascend. The licenses below reflect the evidence recorded in the catalog;
artifact-specific terms still apply when obtaining material from upstream.

| Project and authors | Source | Recorded license / scope |
| --- | --- | --- |
| Linux Upskill Challenge — course authors and maintainers | [Repository](https://github.com/livialima/linuxupskillchallenge) | [CC BY 4.0](https://github.com/livialima/linuxupskillchallenge/blob/master/LICENSE); course content is linked. |
| Labtainers — Naval Postgraduate School and contributors | [Repository](https://github.com/mfthomps/Labtainers) | [NPS distribution notice](https://github.com/mfthomps/Labtainers/blob/26c13698619abb4c67fcf483e8720b6c6aa3d6b2/docs/license.md), plus separate third-party and SEED-derived lab terms. |
| Damn Vulnerable RESTaurant API Game — theowni and contributors | [Pinned source](https://github.com/theowni/Damn-Vulnerable-RESTaurant-API-Game/tree/d32d09972aec7830f5f1d4a5d274cac7aae7eb82) | [GPL version 3](https://github.com/theowni/Damn-Vulnerable-RESTaurant-API-Game/blob/d32d09972aec7830f5f1d4a5d274cac7aae7eb82/LICENSE). |
| StratoCyberLab — Stratosphere Laboratory and contributors | [Repository](https://github.com/stratosphereips/stratocyberlab) | GPL version 2, recorded from repository metadata; individual labs need review. |
| EVTX Attack Samples — sbousseaden and contributors | [Repository](https://github.com/sbousseaden/EVTX-ATTACK-SAMPLES) | [GPL version 3](https://github.com/sbousseaden/EVTX-ATTACK-SAMPLES/blob/master/LICENSE.GPL). |
| KC7 — KC7 Foundation and contributors | [Repository](https://github.com/KC7-Foundation/kc7) | Apache 2.0 recorded for generator code; this does not establish the terms of the separate `kc7_data` repository or hosted service. |
| Modern Binary Exploitation — RPISEC and contributors | [Pinned source](https://github.com/RPISEC/MBE/tree/200debfff3adf7beeff5e597e9ca9493b779a77e) | BSD 2-Clause for code; lecture slides have separate CC BY-NC 4.0 terms. |
| CloudFoxable — Bishop Fox and contributors | [Pinned source](https://github.com/BishopFox/cloudfoxable/tree/fc49b7f637268031515ced9fee4b643d3e68db67) | MIT for source; cloud providers have separate account terms and charges. |
| Kubernetes Goat — Madhu Akula and contributors | [Pinned source](https://github.com/madhuakula/kubernetes-goat/tree/723a0db478f050d173d23b4ce5044b65bce0bdd0) | MIT for source; images and dependencies retain their own notices. |
| MASTG Hacking Playground — OWASP Mobile Security project and contributors | [Pinned source](https://github.com/OWASP/MASTG-Hacking-Playground/tree/db219a1011e6735cf0c6c08ba929a27ef40e1873) | [GPL version 3](https://github.com/OWASP/MASTG-Hacking-Playground/blob/db219a1011e6735cf0c6c08ba929a27ef40e1873/LICENSE.md); bundled libraries have separate notices. |
| Damn Vulnerable LLM Agent — Reversec Labs and contributors | [Pinned source](https://github.com/ReversecLabs/damn-vulnerable-llm-agent/tree/c0cf9a14adad76e9d6a53c41741f625334bd9971) | Apache 2.0 for source; model weights and provider services have separate terms. |

## Dependencies and tools

Ascend's standalone CLI uses Python's standard library. Optional server, push,
and development dependencies are installed separately from their publishers.
The declared dependencies are credited here; transitive dependencies retain
the notices provided by their own distributions.

| Project | Authors / maintainers | License of the inspected dependency |
| --- | --- | --- |
| [FastAPI](https://github.com/fastapi/fastapi) | Sebastián Ramírez and contributors | MIT |
| [Uvicorn](https://github.com/Kludex/uvicorn) | Tom Christie and contributors | BSD 3-Clause |
| [python-multipart](https://github.com/Kludex/python-multipart) | Andrew Dunham and contributors | Apache 2.0 |
| [pywebpush](https://github.com/web-push-libs/pywebpush) | JR Conlin and contributors | MPL 2.0 |
| [pytest](https://github.com/pytest-dev/pytest) | pytest contributors | MIT |
| [HTTPX](https://github.com/encode/httpx) / [HTTPX2](https://github.com/pydantic/httpx2) | Tom Christie and contributors | BSD 3-Clause |
| [Playwright](https://github.com/microsoft/playwright-python) | Microsoft and contributors | Apache 2.0 |
| [Ruff](https://github.com/astral-sh/ruff) | Astral and contributors | MIT |
| [build](https://github.com/pypa/build), [setuptools](https://github.com/pypa/setuptools), [wheel](https://github.com/pypa/wheel) | Python Packaging Authority and contributors | MIT |

[CPython](https://github.com/python/cpython) and the
[official Python Docker images](https://github.com/docker-library/python) supply
the interpreter and container base. The interpreter, Debian/Alpine packages,
and installed dependencies retain their individual licenses. Container builds
keep the installed Python packages' license metadata. Preserve these notices
and any source obligations when redistributing a container or installation.

Learning and deployment instructions also use or reference tools such as
[Docker / Moby](https://github.com/moby/moby),
[Caddy](https://github.com/caddyserver/caddy),
[netlab](https://github.com/ipspace/netlab), and
[containerlab](https://github.com/srl-labs/containerlab). They are obtained
separately and retain their upstream terms.

## Learning and design references

Learning resources link to their original publishers, including OWASP,
PortSwigger Web Security Academy, Hack The Box Academy, pwn.college, and ROP
Emporium. The source records in
[`docs/curriculum/sources.json`](https://github.com/KDS-7Git/Ascend/blob/main/docs/curriculum/sources.json)
describe the reviewed material and its limits. Ascend's bundled training
fixtures and packet captures are authored synthetic examples.

The UI research credits
[React Bits](https://github.com/DavidHDev/react-bits),
[Aceternity UI](https://ui.aceternity.com/),
[Magic UI](https://magicui.design/), and
[Neobrutalism Components](https://www.neobrutalism.dev/), alongside the other
design and accessibility references recorded in
[`docs/design/ui-workspace-sources.json`](https://github.com/KDS-7Git/Ascend/blob/main/docs/design/ui-workspace-sources.json).
Those records describe design inspiration; their component code, shaders,
branding, and illustrations were not copied into Ascend.

## Complete pinned MIT notices

These texts are preserved verbatim from the revisions linked above. Keep each
notice with any redistributed copy or substantial portion of its material.

### BGP Labs — LICENSE.md

```text
Copyright (c) 2023–2024 Ivan Pepelnjak

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### VAmPI — LICENSE

```text
MIT License

Copyright (c) 2020 erev0s

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Security Datasets — LICENSE

```text
MIT License

Copyright (c) 2021 Open Threat Research Forge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
