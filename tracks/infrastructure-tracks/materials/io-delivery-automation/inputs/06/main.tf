terraform {
  required_providers {
    libvirt = { source = "dmacvicar/libvirt", version = "= 0.8.3" }
  }
}
provider "libvirt" { uri = "qemu:///system" }
variable "base_image" { type = string }
resource "libvirt_volume" "relay" {
  name = "ascend-tofu-relay.qcow2"
  pool = "default"
  source = var.base_image
  format = "qcow2"
}
resource "libvirt_domain" "relay" {
  name = "ascend-tofu-relay"
  memory = 1024
  vcpu = 1
  disk { volume_id = libvirt_volume.relay.id }
  network_interface { network_name = "default" }
  console {
    type = "pty"
    target_port = "0"
    target_type = "serial"
  }
}
