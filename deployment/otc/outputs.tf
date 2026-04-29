output "instance_id" {
  description = "OTC compute instance id"
  value       = opentelekomcloud_compute_instance_v2.bioresearch.id
}

output "instance_name" {
  description = "OTC compute instance name"
  value       = opentelekomcloud_compute_instance_v2.bioresearch.name
}

output "floating_ip" {
  description = "Public floating IP address"
  value       = opentelekomcloud_networking_floatingip_v2.bioresearch.address
}

