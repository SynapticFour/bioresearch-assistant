variable "instance_name" {
  description = "Name of OTC compute instance"
  type        = string
  default     = "bioresearch-assistant"
}

variable "flavor_name" {
  description = "OTC flavor for instance size"
  type        = string
  default     = "s3.xlarge.4"
}

variable "image_name" {
  description = "OTC image name"
  type        = string
  default     = "Standard_Ubuntu_22.04_latest"
}

variable "key_pair" {
  description = "Existing OTC keypair name"
  type        = string
  default     = "bioresearch-key"
}

variable "security_groups" {
  description = "Existing OTC security groups"
  type        = list(string)
  default     = ["bioresearch-sg"]
}

variable "network_name" {
  description = "Existing OTC network name"
  type        = string
  default     = "bioresearch-vpc"
}

variable "floating_ip_pool" {
  description = "Floating IP pool"
  type        = string
  default     = "admin_external_net"
}

variable "deploy_user" {
  description = "Linux user for deployment actions"
  type        = string
  default     = "ubuntu"
}

variable "repo_url" {
  description = "Git repository URL"
  type        = string
  default     = "https://github.com/SynapticFour/bioresearch-assistant.git"
}

variable "repo_ref" {
  description = "Git branch or tag to checkout"
  type        = string
  default     = "main"
}

variable "install_dir" {
  description = "Install directory on target host"
  type        = string
  default     = "/opt/bioresearch"
}

variable "backend_image" {
  description = "Backend image used by compose"
  type        = string
  default     = "ghcr.io/synapticfour/bioresearch-assistant-backend:latest"
}

variable "frontend_image" {
  description = "Frontend image used by compose"
  type        = string
  default     = "ghcr.io/synapticfour/bioresearch-assistant-frontend:latest"
}

variable "docker_platform" {
  description = "Docker platform for compose workloads"
  type        = string
  default     = "linux/amd64"
}

