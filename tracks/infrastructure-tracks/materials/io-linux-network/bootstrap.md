# Environment bootstrap

Local processes first; one disposable Linux VM for services and networking.

Start with your own PC, Python 3.11+, an editor and a few hundred MiB of free space. The portable exercises, Relay service and local HTTP checks need no account, domain, paid service or Raspberry Pi. The ZIP is a set of readable files: nothing launches merely because it is downloaded. Keep work/ and notes/ in the extracted directory so outputs are easy to find.

```sh
python3 --version
mkdir -p work notes
python3 shared/selfcheck.py
```

The selfcheck uses temporary loopback endpoints and synthetic data, then cleans its own resources. It checks the supplied teaching tools, not your knowledge. Stop the persistent practice service before another exercise reuses its port.

## A Linux environment before full VM administration

An existing owned Linux PC or an assigned Linux guest is sufficient to start. Record its hostname, OS and account rights. Use the assigned guest console/SSH instructions; guest sudo does not grant rights to the host hypervisor. Linux networking and systemd lessons require a disposable guest/host with the named tools, not just an online code editor.

For a new learner PC, an optional bootstrap is [Multipass](https://documentation.ubuntu.com/multipass/latest/how-to-guides/install-multipass/), after installing the supported host application from its official instructions and checking virtualization support. On your PC, this creates only a specifically named starter guest:

```sh
multipass version
multipass launch 24.04 --name ascend-linux --cpus 1 --memory 1G --disk 12G
multipass info ascend-linux
multipass shell ascend-linux
```

Inside the guest run `hostname`, `cat /etc/os-release` and `id`. Transfer this extracted folder using the documented Multipass transfer/mount workflow, then open a guest terminal in it. The VM track teaches the underlying host, guest, image, network and administration mechanics explicitly. An Ubuntu/WSL shell is another route for early shell practice; it does not substitute for demonstrating a separate VM kernel/control plane. If the host cannot expose virtualization, use an eligible existing guest or another host and record the limitation.

At teardown preserve evidence and stop only `ascend-linux`. Remove it only when no longer needed; avoid a global purge that might remove unrelated deleted guests. Never format physical storage or change your main network while following a guest recipe.

## Resource choices

- Learner PC baseline: 16 GB RAM and about 200 GB free SSD. Begin with one 1–2 GiB guest, then run multi-guest exercises sequentially with a starting total lab allowance near 8 GiB. Inspect actual CPU topology, free RAM, image growth and host reserve. A sparse disk's declared capacity is not current storage use.
- Ascend server baseline: approximately 4 cores, 4–8 GB RAM and 100–120 GB microSD storage. These downloads do not run guests, Docker builds or load generators on it. Its separately authorized hosted-runner limit remains two simultaneous labs.
- Hardware route: a Raspberry Pi, spare laptop, mini-PC or eligible VPS can be a later owned target. Check architecture, firmware/virtualization support, power, cooling, storage and tool compatibility. Build/load-test on the PC and deploy measured artifacts to the smaller machine. The VM/software route remains available without buying a device.
- Advanced route: run additional physical hosts or larger guests when available. Keep the same backup, identity, workload and recovery evidence. Multiple guests on one PC share its power, disk and network failures; they do not prove physical high availability.
- Public DNS, mail, free hosting, tunnels and provider accounts have current eligibility/usage conditions. Start with the local variant, inspect the provider's current official terms, and initiate public actions only in your own chosen account. Public access needs an actual external client observation. Mail capture is not internet delivery.

## Machine and file boundaries

HOST means the machine administering guest definitions/disks. GUEST means the particular disposable Linux instance. CLIENT means the machine issuing a request; its 127.0.0.1 is its own loopback. EDGE means the intended reverse proxy. An address inside a sample file is a placeholder until verified against your actual environment. Keep tokens, private keys, real messages, cloud state and private inventories out of public reports.

Read `shared/README.md` for the synthetic service and portable helper interfaces. Native tools such as Caddy, QEMU/libvirt, Incus, WireGuard, Postfix, Dovecot, OpenTofu, Ansible, Docker and k6 are separate installations named by their lessons. Their recipes are authored drafts; record versions and keep untested variants explicit.
