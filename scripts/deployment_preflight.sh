#!/usr/bin/env bash
set -euo pipefail

SCENARIO="bare-metal"
REQUIRE_INTERNET="auto"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deployment_preflight.sh --scenario <name> [--require-internet true|false|auto]

Scenarios:
  laptop        Local tests on small hardware
  workstation   Medium local deployment
  institute     GPU server (e.g., A100 / >=100 GB RAM)
  bare-metal    VM/server with internet
  kubernetes    AKS/on-prem Kubernetes
  offline       Air-gapped target system
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario) SCENARIO="$2"; shift 2 ;;
    --require-internet) REQUIRE_INTERNET="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

pass() { echo "PASS: $1"; }
warn() { echo "WARN: $1"; }
fail() { echo "FAIL: $1"; FAILED=1; }

FAILED=0

os_name="$(uname -s)"

get_ram_gb() {
  if [[ "${os_name}" == "Darwin" ]]; then
    bytes="$(sysctl -n hw.memsize)"
    echo $((bytes / 1024 / 1024 / 1024))
  else
    awk '/MemTotal/ {print int($2/1024/1024)}' /proc/meminfo
  fi
}

get_disk_free_gb() {
  df -Pk . | awk 'NR==2 {print int($4/1024/1024)}'
}

check_command() {
  local cmd="$1"
  if command -v "${cmd}" >/dev/null 2>&1; then
    pass "Command available: ${cmd}"
  else
    fail "Command missing: ${cmd}"
  fi
}

check_internet() {
  if curl -fsS --max-time 5 https://ghcr.io >/dev/null 2>&1; then
    pass "Internet/GHCR reachable"
  else
    fail "Internet/GHCR not reachable"
  fi
}

check_docker_running() {
  if docker info >/dev/null 2>&1; then
    pass "Docker daemon reachable"
  else
    fail "Docker daemon not reachable"
  fi
}

check_nvidia() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    pass "nvidia-smi available"
    gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || true)"
    [[ -n "${gpu_name}" ]] && pass "GPU detected: ${gpu_name}"
  else
    warn "nvidia-smi not found (GPU checks skipped)"
  fi
}

echo "Running preflight for scenario: ${SCENARIO}"
echo "OS: ${os_name}"

check_command docker
check_command curl
check_docker_running

ram_gb="$(get_ram_gb)"
disk_gb="$(get_disk_free_gb)"
echo "Detected RAM: ${ram_gb} GB"
echo "Free disk: ${disk_gb} GB"

internet_needed="false"
if [[ "${REQUIRE_INTERNET}" == "true" ]]; then
  internet_needed="true"
elif [[ "${REQUIRE_INTERNET}" == "false" ]]; then
  internet_needed="false"
else
  case "${SCENARIO}" in
    offline) internet_needed="false" ;;
    *) internet_needed="true" ;;
  esac
fi

if [[ "${internet_needed}" == "true" ]]; then
  check_internet
else
  warn "Internet check skipped for offline scenario"
fi

case "${SCENARIO}" in
  laptop)
    (( ram_gb >= 8 )) && pass "RAM >= 8 GB" || fail "RAM < 8 GB"
    (( disk_gb >= 20 )) && pass "Disk >= 20 GB" || fail "Disk < 20 GB"
    ;;
  workstation)
    (( ram_gb >= 24 )) && pass "RAM >= 24 GB" || fail "RAM < 24 GB"
    (( disk_gb >= 80 )) && pass "Disk >= 80 GB" || fail "Disk < 80 GB"
    ;;
  institute)
    (( ram_gb >= 100 )) && pass "RAM >= 100 GB" || fail "RAM < 100 GB"
    (( disk_gb >= 300 )) && pass "Disk >= 300 GB" || fail "Disk < 300 GB"
    check_nvidia
    ;;
  bare-metal)
    (( ram_gb >= 16 )) && pass "RAM >= 16 GB" || fail "RAM < 16 GB"
    (( disk_gb >= 50 )) && pass "Disk >= 50 GB" || fail "Disk < 50 GB"
    ;;
  kubernetes)
    check_command kubectl
    check_command helm
    if kubectl cluster-info >/dev/null 2>&1; then
      pass "kubectl can reach cluster"
    else
      fail "kubectl cannot reach cluster"
    fi
    ;;
  offline)
    (( ram_gb >= 16 )) && pass "RAM >= 16 GB" || fail "RAM < 16 GB"
    (( disk_gb >= 120 )) && pass "Disk >= 120 GB" || fail "Disk < 120 GB"
    ;;
  *)
    fail "Unknown scenario: ${SCENARIO}"
    ;;
esac

if [[ "${FAILED}" -eq 1 ]]; then
  echo "Preflight finished with failures."
  exit 1
fi

echo "Preflight finished successfully."

