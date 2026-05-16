#!/usr/bin/env bash
# =============================================================================
# lab_recovery.sh — Recovery Script: Open Source Security Lab 10 Hari
# =============================================================================
# Usage:
#   bash lab_recovery.sh           -> recover semua layanan
#   bash lab_recovery.sh --day 3   -> recover layanan hari tertentu saja
#   bash lab_recovery.sh --check   -> cek status tanpa recovery (coming soon)
#
# Jalankan di WSL Ubuntu:
#   cd /mnt/d/Downloads/Learning
#   bash lab_recovery.sh
# =============================================================================

# NOTE: set -euo pipefail dihapus agar error 1 hari tidak menghentikan seluruh script
set -uo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
GREEN="\033[92m"; YELLOW="\033[93m"; RED="\033[91m"
CYAN="\033[96m";  BOLD="\033[1m";    RESET="\033[0m"
OK="${GREEN}[OK UP]${RESET}"
DOWN="${RED}[XX DOWN]${RESET}"
STARTING="${YELLOW}[>> STARTING]${RESET}"
SKIP="${CYAN}[-- SKIP]${RESET}"

# ── Args ─────────────────────────────────────────────────────────────────────
TARGET_DAY=""
CHECK_ONLY=false

# Fix: gunakan while loop bukan for loop agar shift bekerja benar
while [[ $# -gt 0 ]]; do
  case "$1" in
    --day)
      if [[ $# -ge 2 ]]; then
        TARGET_DAY="$2"
        shift 2
      else
        echo "Error: --day memerlukan argumen (misal: --day 3)" >&2
        shift
      fi
      ;;
    --check)
      CHECK_ONLY=true
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────
port_open() {
  nc -z 127.0.0.1 "$1" 2>/dev/null
}

container_running() {
  docker ps --filter "name=$1" --format '{{.Names}}' 2>/dev/null | grep -q "."
}

wait_for_port() {
  local port=$1 label=$2 max=30 i=0
  echo -ne "  Waiting for $label :$port "
  while ! port_open "$port" && [ $i -lt $max ]; do
    echo -n "."
    sleep 1
    i=$((i + 1))
  done
  if port_open "$port"; then
    echo -e " ${GREEN}OK${RESET}"
  else
    echo -e " ${YELLOW}timeout (service may still be starting)${RESET}"
  fi
}

section() {
  echo -e "\n${CYAN}${BOLD}-- Hari $1 -- $2 -----------------------------------------------${RESET}"
}

skip_if_target() {
  [[ -n "$TARGET_DAY" && "$TARGET_DAY" != "$1" ]]
}

# =============================================================================
# HARI 01 -- LocalStack IAM
# =============================================================================
recover_day1() {
  section 01 "LocalStack IAM"
  if skip_if_target 1; then echo -e "  ${SKIP} Skipped (--day $TARGET_DAY)"; return; fi

  if container_running localstack; then
    echo -e "  ${OK} LocalStack already running"
  else
    echo -e "  ${STARTING} Starting LocalStack..."
    docker start localstack 2>/dev/null || \
    docker run -d --name localstack \
      -p 4566:4566 -p 4510-4559:4510-4559 \
      --restart unless-stopped \
      localstack/localstack:3.8 2>/dev/null || \
    echo -e "  ${RED}[!] Could not start LocalStack -- check: docker logs localstack${RESET}"
    wait_for_port 4566 "LocalStack"
  fi
}

# =============================================================================
# HARI 02 -- Docker Networks
# =============================================================================
recover_day2() {
  section 02 "Network Security (Docker Networks + iptables)"
  if skip_if_target 2; then echo -e "  ${SKIP} Skipped"; return; fi

  for net in public-net private-app-net private-db-net waf-lab-net; do
    if docker network ls --format '{{.Name}}' 2>/dev/null | grep -q "^${net}$"; then
      echo -e "  ${OK} Network '$net' exists"
    else
      echo -e "  ${STARTING} Creating network '$net'..."
      if [[ "$net" == "public-net" || "$net" == "waf-lab-net" ]]; then
        docker network create --driver bridge "$net" 2>/dev/null && \
          echo -e "  ${GREEN}    -> Created $net${RESET}" || true
      else
        docker network create --driver bridge --internal "$net" 2>/dev/null && \
          echo -e "  ${GREEN}    -> Created $net (internal)${RESET}" || true
      fi
    fi
  done

  echo -e "\n  ${YELLOW}[!] Note: iptables rules TIDAK persisten setelah WSL restart.${RESET}"
  echo -e "  ${YELLOW}    Untuk persistensi, jalankan perintah berikut:${RESET}"
  echo -e "  ${CYAN}    sudo apt install -y iptables-persistent${RESET}"
  echo -e "  ${CYAN}    sudo iptables -P INPUT DROP${RESET}"
  echo -e "  ${CYAN}    sudo iptables -A INPUT -i lo -j ACCEPT${RESET}"
  echo -e "  ${CYAN}    sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT${RESET}"
  echo -e "  ${CYAN}    sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT${RESET}"
  echo -e "  ${CYAN}    sudo netfilter-persistent save${RESET}"
}

# =============================================================================
# HARI 03 -- MinIO + HashiCorp Vault
# =============================================================================
recover_day3() {
  section 03 "Data Security (MinIO + HashiCorp Vault)"
  if skip_if_target 3; then echo -e "  ${SKIP} Skipped"; return; fi

  # MinIO volumes
  for vol in d1 d2 d3 d4; do
    docker volume inspect "$vol" &>/dev/null || docker volume create "$vol" &>/dev/null
  done

  # MinIO
  if container_running minio; then
    echo -e "  ${OK} MinIO already running"
  else
    echo -e "  ${STARTING} Starting MinIO..."
    docker start minio 2>/dev/null || \
    docker run -d --name minio \
      -p 8010:9000 -p 8011:9001 \
      --restart unless-stopped \
      -e "MINIO_ROOT_USER=admin" \
      -e "MINIO_ROOT_PASSWORD=password123" \
      -v d1:/data1 -v d2:/data2 -v d3:/data3 -v d4:/data4 \
      --entrypoint sh minio/minio \
      -c "minio server /data1 /data2 /data3 /data4 --console-address :9001" 2>/dev/null || \
    echo -e "  ${RED}[!] MinIO start failed -- check docker logs minio${RESET}"
    wait_for_port 8010 "MinIO API"
  fi

  # Vault
  if container_running vault; then
    echo -e "  ${OK} HashiCorp Vault already running"
    SEALED=$(docker exec vault vault status -format=json 2>/dev/null | \
      python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sealed',True))" 2>/dev/null || echo "true")
    if [ "$SEALED" = "True" ] || [ "$SEALED" = "true" ]; then
      echo -e "  ${YELLOW}[!] Vault is SEALED. Dev mode: restart container untuk auto-unseal:${RESET}"
      echo -e "  ${CYAN}    docker restart vault${RESET}"
      echo -e "  ${CYAN}    (atau production) docker exec vault vault operator unseal <UNSEAL_KEY>${RESET}"
    else
      echo -e "  ${OK} Vault is UNSEALED"
    fi
  else
    echo -e "  ${STARTING} Starting HashiCorp Vault..."
    docker start vault 2>/dev/null || \
    docker run -d --name vault \
      --cap-add=IPC_LOCK \
      --restart unless-stopped \
      -e "VAULT_DEV_ROOT_TOKEN_ID=myroot" \
      -p 8200:8200 \
      hashicorp/vault 2>/dev/null || \
    echo -e "  ${RED}[!] Vault start failed -- check docker logs vault${RESET}"
    wait_for_port 8200 "Vault"
  fi
}

# =============================================================================
# HARI 04 -- Wazuh SIEM
# =============================================================================
recover_day4() {
  section 04 "Security Monitoring (Wazuh SIEM)"
  if skip_if_target 4; then echo -e "  ${SKIP} Skipped"; return; fi

  WAZUH_DIR=""
  for d in ~/wazuh-docker/single-node ~/wazuh-docker; do
    if [ -f "$d/docker-compose.yml" ]; then
      WAZUH_DIR="$d"
      break
    fi
  done

  if container_running wazuh.manager; then
    echo -e "  ${OK} Wazuh Manager already running"
    container_running wazuh.indexer  && echo -e "  ${OK} Wazuh Indexer running"
    container_running wazuh.dashboard && echo -e "  ${OK} Wazuh Dashboard running"
  else
    if [ -n "$WAZUH_DIR" ]; then
      echo -e "  ${STARTING} Starting Wazuh stack dari $WAZUH_DIR ..."
      (cd "$WAZUH_DIR" && docker-compose up -d 2>/dev/null) || \
        echo -e "  ${RED}[!] Wazuh compose up failed${RESET}"
      echo -e "  ${YELLOW}    Wazuh butuh ~2-3 menit untuk fully start...${RESET}"
      wait_for_port 443 "Wazuh Dashboard"
    else
      echo -e "  ${RED}[!] wazuh-docker directory tidak ditemukan.${RESET}"
      echo -e "  ${CYAN}    Clone: git clone https://github.com/wazuh/wazuh-docker.git -b v4.7.0 ~/wazuh-docker${RESET}"
      echo -e "  ${CYAN}    Setup: cd ~/wazuh-docker/single-node${RESET}"
      echo -e "  ${CYAN}           docker-compose -f generate-indexer-certs.yml run --rm generator${RESET}"
      echo -e "  ${CYAN}           docker-compose up -d${RESET}"
    fi
  fi
}

# =============================================================================
# HARI 05 -- Trivy + OpenSCAP (tools check)
# =============================================================================
recover_day5() {
  section 05 "Vulnerability Management (Trivy + OpenSCAP)"
  if skip_if_target 5; then echo -e "  ${SKIP} Skipped"; return; fi

  if command -v trivy &>/dev/null; then
    echo -e "  ${OK} Trivy installed ($(trivy --version 2>/dev/null | head -1))"
  else
    echo -e "  ${STARTING} Installing Trivy..."
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
      | sh -s -- -b /usr/local/bin 2>/dev/null && \
      echo -e "  ${GREEN}    -> Trivy installed${RESET}" || \
      echo -e "  ${RED}[!] Trivy install failed${RESET}"
  fi

  if command -v oscap &>/dev/null; then
    echo -e "  ${OK} OpenSCAP installed"
  else
    echo -e "  ${STARTING} Installing OpenSCAP..."
    sudo apt install -y openscap-scanner 2>/dev/null && \
      echo -e "  ${GREEN}    -> OpenSCAP installed${RESET}" || \
      echo -e "  ${RED}[!] OpenSCAP install failed${RESET}"
  fi

  # Cek scan results
  BASE="/mnt/d/Downloads/Learning"
  [ -f "$BASE/scan-results.xml" ] && \
    echo -e "  ${OK} scan-results.xml ada ($(du -h "$BASE/scan-results.xml" | cut -f1))" || \
    echo -e "  ${YELLOW}[!] scan-results.xml tidak ada -- jalankan OpenSCAP scan${RESET}"

  echo -e "  ${CYAN}  Scan results adalah static file -- tidak perlu recovery service.${RESET}"
}

# =============================================================================
# HARI 06 -- WAF ModSecurity + Fail2ban
# =============================================================================
recover_day6() {
  section 06 "WAF ModSecurity + Fail2ban"
  if skip_if_target 6; then echo -e "  ${SKIP} Skipped"; return; fi

  # backend-app
  if container_running backend-app; then
    echo -e "  ${OK} backend-app already running"
  else
    echo -e "  ${STARTING} Starting backend-app..."
    docker start backend-app 2>/dev/null || \
    docker run -d --name backend-app \
      --network waf-lab-net \
      --restart unless-stopped \
      nginx:alpine 2>/dev/null || \
    echo -e "  ${RED}[!] backend-app start failed${RESET}"
  fi

  # waf-server
  if container_running waf-server; then
    echo -e "  ${OK} WAF (waf-server) already running"
  else
    echo -e "  ${STARTING} Starting WAF server..."
    docker start waf-server 2>/dev/null || \
    docker run -d --name waf-server \
      --network waf-lab-net \
      --restart unless-stopped \
      -p 8081:8080 -p 8443:8443 \
      -e PROXY_UPSTREAM=http://backend-app:80 \
      -e PORT=8080 \
      owasp/modsecurity-crs:nginx 2>/dev/null || \
    echo -e "  ${RED}[!] WAF start failed${RESET}"
    wait_for_port 8081 "WAF"
  fi

  # Fail2ban
  if sudo fail2ban-client status &>/dev/null; then
    echo -e "  ${OK} Fail2ban already running"
  else
    echo -e "  ${STARTING} Starting Fail2ban..."
    sudo service fail2ban start 2>/dev/null && \
      echo -e "  ${GREEN}    -> Fail2ban started${RESET}" || \
      echo -e "  ${YELLOW}[!] Fail2ban belum terinstall atau butuh sudo${RESET}"
  fi
}

# =============================================================================
# HARI 07 -- Forensics (cek tools, tidak ada service yang perlu recover)
# =============================================================================
recover_day7() {
  section 07 "Incident Response & Forensics (Volatility 3)"
  if skip_if_target 7; then echo -e "  ${SKIP} Skipped"; return; fi

  if [ -f ~/volatility3/vol.py ]; then
    echo -e "  ${OK} Volatility 3 installed (~/volatility3/vol.py)"
  else
    echo -e "  ${YELLOW}[!] Volatility 3 tidak ditemukan${RESET}"
    echo -e "  ${CYAN}    Install: git clone https://github.com/volatilityfoundation/volatility3.git ~/volatility3${RESET}"
    echo -e "  ${CYAN}             pip3 install -r ~/volatility3/requirements.txt${RESET}"
  fi

  IR_DIR="/mnt/d/Downloads/Learning/IR-Evidence"
  if [ -d "$IR_DIR" ]; then
    echo -e "  ${OK} IR-Evidence folder exists"
    [ -f "$IR_DIR/chain-of-custody.txt" ] && \
      echo -e "  ${OK} Chain of custody file present" || \
      echo -e "  ${YELLOW}[!] chain-of-custody.txt tidak ada${RESET}"
  else
    echo -e "  ${STARTING} Creating IR-Evidence folder..."
    mkdir -p "$IR_DIR"
    echo -e "  ${GREEN}    -> Created $IR_DIR${RESET}"
  fi
  echo -e "  ${CYAN}  Forensics evidence adalah static file -- tidak ada service yang perlu di-recover.${RESET}"
}

# =============================================================================
# HARI 08 -- PostgreSQL HA
# =============================================================================
recover_day8() {
  section 08 "BCDR -- PostgreSQL Streaming Replication"
  if skip_if_target 8; then echo -e "  ${SKIP} Skipped"; return; fi

  BCDR_DIR=~/bcdr-lab

  if container_running pg_primary && container_running pg_standby; then
    echo -e "  ${OK} pg_primary running"
    echo -e "  ${OK} pg_standby running"
  else
    if [ -f "$BCDR_DIR/docker-compose.yml" ]; then
      echo -e "  ${STARTING} Starting PostgreSQL HA stack..."
      (cd "$BCDR_DIR" && docker-compose up -d 2>/dev/null) || \
        echo -e "  ${RED}[!] PostgreSQL compose up failed${RESET}"
      wait_for_port 5432 "pg_primary"
      wait_for_port 5433 "pg_standby"
    else
      echo -e "  ${RED}[!] ~/bcdr-lab/docker-compose.yml tidak ditemukan${RESET}"
      echo -e "  ${CYAN}    Lihat Progress_Hari_08_BCDR_Postgres.md untuk cara recreate${RESET}"
    fi
  fi

  # Verify replication
  sleep 2
  REPL=$(docker exec pg_primary psql -U postgres -tAc \
    "SELECT state FROM pg_stat_replication;" 2>/dev/null || echo "")
  if echo "$REPL" | grep -qi "streaming"; then
    echo -e "  ${OK} Streaming replication ACTIVE (state=streaming)"
  else
    echo -e "  ${YELLOW}[!] Replication belum streaming -- mungkin butuh waktu sync${RESET}"
    echo -e "  ${CYAN}    Check: docker exec pg_primary psql -U postgres -c 'SELECT state FROM pg_stat_replication;'${RESET}"
  fi
}

# =============================================================================
# HARI 09 -- Teleport + OpenSCAP
# =============================================================================
recover_day9() {
  section 09 "Zero Trust Access (Teleport) + OpenSCAP Compliance"
  if skip_if_target 9; then echo -e "  ${SKIP} Skipped"; return; fi

  # Teleport
  if port_open 3080; then
    echo -e "  ${OK} Teleport Proxy :3080 already listening"
  else
    if command -v teleport &>/dev/null && [ -f /etc/teleport.yaml ]; then
      echo -e "  ${STARTING} Starting Teleport..."
      sudo teleport start --config=/etc/teleport.yaml &>/tmp/teleport.log &
      disown
      wait_for_port 3080 "Teleport"
      echo -e "  ${YELLOW}    Tip: untuk auto-start: sudo systemctl enable teleport${RESET}"
    else
      echo -e "  ${RED}[!] Teleport tidak terinstall atau /etc/teleport.yaml tidak ada${RESET}"
      echo -e "  ${CYAN}    Install: curl https://goteleport.com/static/install.sh | bash -s 12.3.1${RESET}"
      echo -e "  ${CYAN}    Config:  sudo teleport configure --cluster-name=teleport.local | sudo tee /etc/teleport.yaml${RESET}"
    fi
  fi

  if command -v oscap &>/dev/null; then
    echo -e "  ${OK} OpenSCAP scanner installed"
  else
    echo -e "  ${YELLOW}[!] OpenSCAP tidak ditemukan -- jalankan: sudo apt install -y openscap-scanner${RESET}"
  fi
}

# =============================================================================
# HARI 10 -- Capstone Scripts check
# =============================================================================
recover_day10() {
  section 10 "SOC Operations Capstone (Scripts & Docs)"
  if skip_if_target 10; then echo -e "  ${SKIP} Skipped"; return; fi

  BASE="/mnt/d/Downloads/Learning"
  ALL_OK=true
  for f in \
    "lab_checker_10hari.py" \
    "capstone_final_audit.py" \
    "soc_health_check.py" \
    "parse_report.py" \
    "lab_recovery.sh" \
    "README.md" \
    "Progress_Hari_01_IAM_LocalStack.md" \
    "Progress_Hari_02_Network_Security.md" \
    "Progress_Hari_03_MinIO_Vault.md" \
    "Progress_Hari_04_Wazuh_SIEM.md" \
    "Progress_Hari_05_Vulnerability_Management.md" \
    "Progress_Hari_06_WAF_Fail2ban.md" \
    "Progress_Hari_07_IR_Forensik.md" \
    "Progress_Hari_08_BCDR_Postgres.md" \
    "Progress_Hari_09_Compliance_Access.md" \
    "Progress_Hari_10_Final_Capstone.md"; do
    if [ -f "$BASE/$f" ]; then
      echo -e "  ${OK} $f"
    else
      echo -e "  ${RED}[!] MISSING: $f${RESET}"
      ALL_OK=false
    fi
  done

  if $ALL_OK; then
    echo -e "\n  ${GREEN}${BOLD}Semua file Hari 10 tersedia!${RESET}"
  else
    echo -e "\n  ${YELLOW}[!] Beberapa file tidak ditemukan${RESET}"
  fi
}

# =============================================================================
# MAIN
# =============================================================================
print_header() {
  echo -e "\n${BOLD}${CYAN}+----------------------------------------------------------+${RESET}"
  echo -e "${BOLD}${CYAN}|     OPEN SOURCE SECURITY LAB -- RECOVERY SCRIPT          |${RESET}"
  echo -e "${BOLD}${CYAN}+----------------------------------------------------------+${RESET}"
  if $CHECK_ONLY; then
    echo -e "  ${CYAN}Time: $(date '+%Y-%m-%d %H:%M:%S') | Mode: CHECK-ONLY${RESET}"
  else
    echo -e "  ${CYAN}Time: $(date '+%Y-%m-%d %H:%M:%S') | Mode: RECOVERY${RESET}"
  fi
  [[ -n "$TARGET_DAY" ]] && echo -e "  ${YELLOW}Target: Hari $TARGET_DAY only${RESET}"
}

print_footer() {
  echo -e "\n${BOLD}${CYAN}----------------------------------------------------------${RESET}"
  echo -e "${BOLD}  Recovery selesai! Jalankan checker untuk verifikasi:${RESET}"
  echo -e "  ${CYAN}  python3 /mnt/d/Downloads/Learning/lab_checker_10hari.py${RESET}"
  echo -e "${BOLD}${CYAN}----------------------------------------------------------${RESET}\n"
}

print_header

recover_day1
recover_day2
recover_day3
recover_day4
recover_day5
recover_day6
recover_day7
recover_day8
recover_day9
recover_day10

print_footer
