terraform {
  required_providers {
    opentelekomcloud = {
      source = "opentelekomcloud/opentelekomcloud"
    }
  }
}

resource "opentelekomcloud_compute_instance_v2" "bioresearch" {
  name            = "bioresearch-assistant"
  flavor_name     = "s3.xlarge.4"
  image_name      = "Standard_Ubuntu_22.04_latest"
  key_pair        = "bioresearch-key"
  security_groups = ["bioresearch-sg"]

  network {
    name = "bioresearch-vpc"
  }

  user_data = file("${path.module}/cloud-init.sh")
}

resource "opentelekomcloud_networking_floatingip_v2" "bioresearch" {
  pool = "admin_external_net"
}

resource "opentelekomcloud_compute_floatingip_associate_v2" "bioresearch" {
  floating_ip = opentelekomcloud_networking_floatingip_v2.bioresearch.address
  instance_id = opentelekomcloud_compute_instance_v2.bioresearch.id
}
