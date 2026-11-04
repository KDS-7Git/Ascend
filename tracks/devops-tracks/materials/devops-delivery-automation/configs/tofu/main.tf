terraform {
  required_version = ">= 1.6.0"
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}
provider "docker" {}
variable "relay_image_id" { type = string }
variable "release" {
  type = string
  default = "tofu-v1"
}
resource "docker_network" "lab" { name = "ascend-relay-tofu" }
resource "docker_volume" "data" { name = "ascend-relay-tofu-data" }
resource "docker_container" "relay" {
  name = "ascend-relay-tofu"
  image = var.relay_image_id
  memory = 192
  command = ["python", "/app/relay.py", "--host", "0.0.0.0", "--port", "8000", "--data", "/data/relay.sqlite", "--release", var.release]
  ports {
    internal = 8000
    external = 18000
    ip = "127.0.0.1"
  }
  networks_advanced { name = docker_network.lab.name }
  volumes {
    volume_name = docker_volume.data.name
    container_path = "/data"
  }
}
output "service_url" { value = "http://127.0.0.1:18000" }
