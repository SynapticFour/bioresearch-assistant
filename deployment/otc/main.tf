terraform {
  required_providers {
    opentelekomcloud = {
      source = "opentelekomcloud/opentelekomcloud"
      version = "~> 1.36"
    }
  }
}

resource "opentelekomcloud_compute_instance_v2" "bioresearch" {
  name            = var.instance_name
  flavor_name     = var.flavor_name
  image_name      = var.image_name
  key_pair        = var.key_pair
  security_groups = var.security_groups

  network {
    name = var.network_name
  }

  user_data = templatefile("${path.module}/cloud-init.sh.tftpl", {
    deploy_user    = var.deploy_user
    repo_url       = var.repo_url
    repo_ref       = var.repo_ref
    install_dir    = var.install_dir
    backend_image  = var.backend_image
    frontend_image = var.frontend_image
    docker_platform = var.docker_platform
  })
}

resource "opentelekomcloud_networking_floatingip_v2" "bioresearch" {
  pool = var.floating_ip_pool
}

resource "opentelekomcloud_compute_floatingip_associate_v2" "bioresearch" {
  floating_ip = opentelekomcloud_networking_floatingip_v2.bioresearch.address
  instance_id = opentelekomcloud_compute_instance_v2.bioresearch.id
}
