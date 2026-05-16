# 🛡️ Open Source Security Lab — 10 Hari

> **Laboratorium keamanan siber enterprise berbasis open-source tools, dibangun penuh di WSL2 Ubuntu + Docker + VirtualBox tanpa biaya cloud berbayar.**

[![Status](https://img.shields.io/badge/Status-COMPLETED-brightgreen)](.)
[![Days](https://img.shields.io/badge/Duration-10%20Days-blue)](.)
[![Tools](https://img.shields.io/badge/Tools-12%2B-orange)](.)
[![Environment](https://img.shields.io/badge/Env-WSL2%20%2B%20Docker-informational)](.)

---

## 📋 Daftar Isi
- [Gambaran Umum](#gambaran-umum)
- [Persiapan Environment](#persiapan-environment)
- [Arsitektur Lab](#arsitektur-lab)
- [Rekap 10 Hari Training](#rekap-10-hari-training)
- [Hasil & Metrik](#hasil--metrik)
- [Gap Findings](#gap-findings)
- [Tools yang Digunakan](#tools-yang-digunakan)
- [File Structure](#file-structure)
- [Cara Menjalankan Audit](#cara-menjalankan-audit)

---

## Gambaran Umum

Lab ini adalah implementasi praktis dari **5 pilar keamanan enterprise**:

| Pilar | Implementasi |
|-------|-------------|
| 🔑 **Identity & Access** | LocalStack IAM + Teleport Zero Trust MFA |
| 🌐 **Network Security** | iptables + Docker Network Segmentation |
| 🔐 **Data Security** | MinIO WORM + HashiCorp Vault KMS |
| 📊 **Monitoring & SIEM** | Wazuh + OpenSCAP CIS Compliance |
| 💾 **BCDR** | PostgreSQL Streaming Replication + Failover |

**Pendekatan:** Semua tools adalah **open-source** — pengganti langsung untuk layanan cloud berbayar (AWS IAM, AWS S3, AWS Secrets Manager, Splunk, dll).

---

## Persiapan Environment

### Prasyarat
- Windows 10/11 dengan WSL2 aktif
- Docker Desktop (dengan WSL2 backend)
- VirtualBox (untuk lab forensik Hari 07)
- RAM minimal 16 GB (untuk menjalankan semua stack bersamaan)
- Disk minimal 50 GB (Wazuh + Docker images besar)

### Setup WSL2 & Docker
```powershell
# Di PowerShell Windows (sebagai Administrator)
wsl --install -d Ubuntu-22.04
wsl --set-version Ubuntu-22.04 2
```

```bash
# Di WSL Ubuntu — Install Docker CLI
sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Install tools dasar
sudo apt install -y curl wget unzip git python3 python3-pip \
  openscap-scanner iptables fail2ban

# Install Teleport (Hari 09)
curl https://goteleport.com/static/install.sh | bash -s 12.3.1

# Install Trivy (Hari 05)
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Install Volatility 3 (Hari 07 — dari host Windows/WSL)
git clone https://github.com/volatilityfoundation/volatility3.git ~/volatility3
pip3 install -r ~/volatility3/requirements.txt
```

### Setup LocalStack (Simulasi AWS — Hari 01)
```bash
docker run -d --name localstack \
  -p 4566:4566 -p 4510-4559:4510-4559 \
  localstack/localstack:3.8

# Konfigurasi AWS CLI untuk LocalStack
aws configure set aws_access_key_id test
aws configure set aws_secret_access_key test
aws configure set region us-east-1
```

### Setup MinIO + Vault (Hari 03)
```bash
# MinIO — 4 volume cluster (wajib untuk Object Lock)
docker volume create d1 && docker volume create d2
docker volume create d3 && docker volume create d4

docker run -d --name minio \
  -p 8010:9000 -p 8011:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=password123" \
  -v d1:/data1 -v d2:/data2 -v d3:/data3 -v d4:/data4 \
  --entrypoint sh minio/minio \
  -c "minio server /data1 /data2 /data3 /data4 --console-address :9001"

# HashiCorp Vault — dev mode
docker run -d --name vault \
  --cap-add=IPC_LOCK \
  -e "VAULT_DEV_ROOT_TOKEN_ID=myroot" \
  -p 8200:8200 \
  hashicorp/vault
```

### Setup Wazuh SIEM (Hari 04)
```bash
git clone https://github.com/wazuh/wazuh-docker.git -b v4.7.0
cd wazuh-docker/single-node
docker-compose -f generate-indexer-certs.yml run --rm generator
docker-compose up -d
# Dashboard: https://localhost (admin / SecretPassword)
```

### Setup PostgreSQL HA (Hari 08)
```bash
mkdir -p ~/bcdr-lab/pg_primary_data ~/bcdr-lab/pg_standby_data
cd ~/bcdr-lab
# Buat docker-compose.yml (lihat Progress_Hari_08_BCDR_Postgres.md)
docker-compose up -d
```

### Setup WAF ModSecurity (Hari 06)
```bash
docker network create waf-lab-net
docker run -d --name backend-app --network waf-lab-net nginx:alpine
docker run -d --name waf-server \
  --network waf-lab-net \
  -p 8081:8080 -p 8443:8443 \
  -e PROXY_UPSTREAM=http://backend-app:80 \
  -e PORT=8080 \
  owasp/modsecurity-crs:nginx
```

### Setup Teleport (Hari 09)
```bash
sudo teleport configure --cluster-name=teleport.local | sudo tee /etc/teleport.yaml
sudo teleport start --config=/etc/teleport.yaml &
sudo tctl users add admin --roles=editor,access --logins=$USER,root
# Buka URL invitation → scan QR dengan Google Authenticator
```

---

## Arsitektur Lab

```
[ INTERNET / USER ]
      │
      │ HTTPS + MFA (TOTP)
      ▼
┌─────────────────────────────────┐
│  Teleport Zero Trust Proxy      │  ← Port 3080
│  (Short-Lived Certificate SSH)  │
└──────────────┬──────────────────┘
               │
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
┌───────┐  ┌──────┐  ┌─────────────────┐
│ WAF   │  │ IAM  │  │  Wazuh SIEM     │
│Mod-   │  │Local-│  │  (All Logs)     │
│Securi-│  │Stack │  │  + OpenSCAP     │
│ty CRS │  │+MFA  │  └────────┬────────┘
└───┬───┘  └──────┘           │
    │ Filtered Traffic         │ Alerts
    ▼                          ▼
┌──────────────────────────────────────┐
│         Internal Services            │
│                                      │
│  ┌─────────┐   ┌──────────────────┐  │
│  │ MinIO   │   │  HashiCorp Vault │  │
│  │ WORM    │   │  KMS/Secrets     │  │
│  │ :8010   │   │  :8200           │  │
│  └─────────┘   └──────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │  PostgreSQL HA Cluster         │  │
│  │  Primary(:5432) → Standby(:5433)│ │
│  │  Streaming WAL Replication     │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘

[ iptables / Docker Network Segmentation ]
  public-net | private-app-net | private-db-net
```

---

## Rekap 10 Hari Training

### Hari 01 — Identity & Access Management (IAM)
**Tanggal:** ~12 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Implementasi IAM dengan prinsip Least Privilege menggunakan LocalStack (simulasi AWS lokal)

**Yang Dikerjakan:**
- Setup LocalStack sebagai simulator AWS IAM
- Membuat user `security-admin` dengan Least Privilege Policy
- Menerapkan IP Whitelisting Policy (`RequireCorpIP`)
- Simulasi incident response kebocoran kredensial
- Scan repo dengan TruffleHog untuk deteksi secret

**Key Learning:**
- Explicit Deny selalu menang atas Allow
- IP Whitelisting membatasi penggunaan Access Key hanya dari IP terpercaya
- TruffleHog wajib dijalankan sebelum `git push`

**Tools:** LocalStack, AWS CLI, TruffleHog
**File:** `Progress_Hari_01_IAM_LocalStack.md`, `policy.json`, `strict-ip-policy.json`

---

### Hari 02 — Network Security Architecture
**Tanggal:** ~12 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Desain jaringan Defense-in-Depth dengan isolasi layer Web/App/DB

**Yang Dikerjakan:**
- Setup 3-tier Docker network (public-net, private-app-net, private-db-net)
- Implementasi iptables Default Deny policy
- Simulasi Security Groups (batasi SSH hanya dari Bastion)
- Studi kasus: isolasi database MySQL dari internet publik

**Key Learning:**
- Flag `--internal` di Docker mencegah container akses internet
- Default Deny: blokir semua, izinkan yang diperlukan saja
- Port database TIDAK boleh di-expose ke public interface

**Tools:** Docker Networks, iptables
**File:** `Progress_Hari_02_Network_Security.md`

---

### Hari 03 — Data Security & Encryption
**Tanggal:** ~12-13 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Implementasi enkripsi at-rest, WORM storage, dan Key Management System

**Yang Dikerjakan:**
- Setup MinIO 4-volume cluster dengan Object Lock (WORM)
- Setup HashiCorp Vault sebagai KMS lokal
- Konfigurasi Transit Secret Engine untuk enkripsi
- Aktivasi Versioning & Compliance Retention (365 hari)
- Simulasi serangan Ransomware → berhasil dipulihkan via versioning

**Key Learning:**
- Object Lock Compliance Mode: tidak ada yang bisa override, bahkan admin
- Versioning = anti-ransomware: versi lama selalu tersimpan
- Vault terpisah dari data = separation of concern

**Infrastruktur:** MinIO (:8010/:8011), Vault (:8200)
**File:** `Progress_Hari_03_MinIO_Vault.md`

---

### Hari 04 — Security Monitoring & SIEM (Wazuh)
**Tanggal:** 14 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Deploy SIEM terpusat dengan alert real-time untuk deteksi serangan

**Yang Dikerjakan:**
- Deploy Wazuh stack: Manager + Indexer + Dashboard via Docker Compose
- Install Wazuh Agent di host WSL (`Zul`) dan container (`web-server-lab`)
- Tulis custom rule Level 12 untuk SSH Brute Force detection
- Simulasi brute force SSH → alert Level 12 muncul di dashboard
- Troubleshoot sintaks rule: `<if_sid>` → `<if_matched_sid>`

**Hasil Nyata:**
- Alert muncul: *"CUSTOM ALERT: Multiple SSH failed logins detected"*
- Alert Level 12 dengan IP sumber, timestamp, dan jumlah percobaan

**Tools:** Wazuh 4.7.0 (Manager, Indexer, Dashboard)
**File:** `Progress_Hari_04_Wazuh_SIEM.md`, `local_rules.xml`

---

### Hari 05 — Vulnerability Management
**Tanggal:** 14 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Pemindaian kerentanan otomatis dan audit kepatuhan konfigurasi

**Yang Dikerjakan:**
- Scan container image dengan Trivy (nginx:latest)
- Audit kepatuhan CIS Ubuntu 22.04 Level 2 dengan OpenSCAP
- Generate laporan HTML (4.1 MB) dan XML (8.4 MB)
- Analisis hasil: 146 PASS, 92 FAIL, 131 Not Applicable (WSL)

**Hasil OpenSCAP:**
| Metrik | Nilai |
|--------|-------|
| Skor Kepatuhan | **43.80 / 100** |
| PASS | 146 rules |
| FAIL | 92 rules |
| Not Applicable (WSL) | 131 rules |

**Tools:** Trivy, OpenSCAP, SCAP Security Guide v0.1.73
**File:** `Progress_Hari_05_Vulnerability_Management.md`, `scan-results.xml`, `report.html`, `parse_report.py`

---

### Hari 06 — Web Application Firewall & Fail2ban
**Tanggal:** 14 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Deploy WAF dengan OWASP CRS dan auto-ban IP penyerang

**Yang Dikerjakan:**
- Deploy ModSecurity WAF dengan OWASP CRS (927 rules)
- Konfigurasi proxy: WAF(:8081) → Backend(:80)
- Test blokir: SQLi, XSS, Path Traversal, Log4Shell
- Implementasi Virtual Patch untuk CVE-2021-44228 (Log4Shell)
- Setup Fail2ban dengan jail `nginx-http-auth` dan `sshd`

**Hasil WAF Testing:**
| Serangan | Status |
|----------|--------|
| SQL Injection | ✅ Blocked |
| XSS | ✅ Blocked (403) |
| Path Traversal | ✅ Blocked (403) |
| Log4Shell | ✅ Virtual Patch (403) |

**Tools:** ModSecurity, OWASP CRS, Fail2ban, Nginx
**File:** `Progress_Hari_06_WAF_Fail2ban.md`

---

### Hari 07 — Incident Response & Digital Forensics
**Tanggal:** 15 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Forensik memori VM menggunakan Volatility 3 sesuai NIST IR Lifecycle

**Yang Dikerjakan:**
- Setup skenario APT (Advanced Persistent Threat) — suspected breach
- Snapshot & isolasi VM `Victim PC` ke Host-Only network
- Memory dump via VBoxManage: **4,117.87 MB**
- Chain of Custody SHA256: `DBD13C9...C06DE4`
- Analisis Volatility 3: PsList, PsTree, NetStat, Malfind, Bash History
- Strings hunting untuk artefak APT

**Hasil Forensik:**
| Aspek | Hasil |
|-------|-------|
| Proses Anomali | ❌ Tidak ditemukan |
| Koneksi ke C2 Server | ❌ Tidak ditemukan |
| Code Injection | ❌ False positive glibc ENDBR64 |
| APT Artifacts | ❌ Tidak ditemukan |
| **Verdict** | **✅ VM CLEAN** |

**Tools:** VirtualBox, VBoxManage, Volatility 3
**File:** `Progress_Hari_07_IR_Forensik.md`, `IR-Evidence/`

---

### Hari 08 — Business Continuity & Disaster Recovery
**Tanggal:** 15 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Implementasi PostgreSQL High Availability dengan automated streaming replication

**Yang Dikerjakan:**
- Deploy 2-node PostgreSQL cluster (Primary:5432, Standby:5433)
- Konfigurasi WAL streaming replication + replication slot
- Setup `pg_hba.conf` untuk user `repuser` (Least Privilege)
- Clone data via `pg_basebackup`
- Uji sinkronisasi: INSERT di Primary → SELECT di Standby (instan)
- Simulasi failover: promote Standby → Primary baru

**Hasil BCDR:**
| Metrik | Nilai |
|--------|-------|
| RTO (Recovery Time) | **< 1 Menit** |
| RPO (Data Loss) | **0** (sync streaming) |
| Failover Method | Manual promote via `pg_ctl` |

**Tools:** PostgreSQL 15, Docker Compose
**File:** `Progress_Hari_08_BCDR_Postgres.md`

---

### Hari 09 — Compliance & Zero Trust Access
**Tanggal:** 15 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Implementasi Zero Trust SSH dengan MFA dan audit compliance CIS Benchmark

**Yang Dikerjakan:**
- Install & konfigurasi Teleport v12.3.1 OSS
- Aktivasi MFA TOTP (Google Authenticator)
- SSH via Teleport certificate (tanpa private key permanen)
- OpenSCAP scan kedua dengan SCAP Security Guide 0.1.72
- Generate skrip remediasi otomatis (Bash)
- Jalankan remediasi dan scan ulang untuk verifikasi
- Demo Session Recording & Audit Log

**Key Results:**
- Login Zero Trust: TOTP wajib, tanpa password/key SSH biasa
- Session Recording: setiap aktivitas terminal dapat di-replay
- Audit Log: event `session.start` dan `session.end` tercatat

**Tools:** Teleport v12.3.1, OpenSCAP, SCAP Security Guide
**File:** `Progress_Hari_09_Compliance_Access.md`, `scan-report.html`, `final-report.html`

---

### Hari 10 — SOC Operations & Capstone Audit
**Tanggal:** 16 Mei 2026 | **Status:** ✅ SELESAI

**Tujuan:** Validasi penuh seluruh infrastruktur keamanan 10 hari secara end-to-end

**Yang Dikerjakan:**
- SOC Health Check otomatis: 2/7 layanan ONLINE awal
- Recovery semua layanan ke 7/7 ONLINE
- Validasi IAM: Teleport MFA + LocalStack Least Privilege
- Validasi Network: WAF blokir SQLi/XSS/Log4Shell + Fail2ban aktif
- Validasi Data: MinIO WORM + Vault Transit KMS
- Validasi Monitoring: Wazuh agent + brute force detection
- Validasi BCDR: PostgreSQL streaming + failover
- Dokumentasi 5 Gap Findings dengan rekomendasi produksi

**File:** `Progress_Hari_10_Final_Capstone.md`, `capstone_final_audit.py`, `lab_checker_10hari.py`

---

## Hasil & Metrik

| Metrik | Nilai |
|--------|-------|
| Total Hari | 10 Hari |
| Total Tools Dikuasai | 12+ tools |
| Kontainer Docker | 8+ containers |
| Health Check Final | 7/7 ONLINE ✅ |
| RTO PostgreSQL | < 1 Menit |
| RPO PostgreSQL | 0 (sync) |
| OpenSCAP Score (WSL) | 43.80 / 100 |
| WAF Attacks Blocked | SQLi, XSS, LFI, Log4Shell ✅ |
| Memory Dump Size | 4,117.87 MB |
| Forensics Verdict | VM CLEAN ✅ |
| Gap Findings | 5 (semua terdokumentasi) |

---

## Gap Findings

| # | Finding | Severity | Rekomendasi |
|---|---------|----------|-------------|
| 1 | iptables rules tidak persisten setelah WSL restart | MEDIUM | `sudo apt install iptables-persistent && sudo netfilter-persistent save` |
| 2 | Docker container tanpa `restart: unless-stopped` | LOW | Tambahkan restart policy di setiap docker-compose.yml |
| 3 | Teleport tidak auto-start setelah WSL restart | LOW | `sudo systemctl enable teleport` (enable systemd di WSL) |
| 4 | Vault berjalan dalam dev mode (in-memory) | HIGH | Gunakan production mode + Raft backend + proper unseal keys |
| 5 | Wazuh tanpa notifikasi eksternal (email/webhook) | LOW | Konfigurasi `<integration>` di `ossec.conf` untuk Slack/email |

---

## Tools yang Digunakan

| Tool | Kategori | Versi | Fungsi |
|------|----------|-------|--------|
| LocalStack | IAM Simulator | 3.8 | Simulasi AWS IAM lokal |
| TruffleHog | Secret Scanner | Latest | Deteksi kredensial di Git repo |
| iptables | Firewall | - | Network access control |
| Docker | Container | - | Isolasi layanan |
| MinIO | Object Storage | Latest | WORM storage anti-ransomware |
| HashiCorp Vault | KMS/Secrets | Latest | Key management & secret rotation |
| Wazuh | SIEM | 4.7.0 | Security monitoring & alerting |
| Trivy | Vuln Scanner | Latest | Container & filesystem scanning |
| OpenSCAP | Compliance | 1.3.x | CIS Benchmark audit |
| ModSecurity | WAF | OWASP CRS | Web application firewall |
| Fail2ban | IPS | - | Auto-ban IP penyerang |
| Volatility 3 | Forensics | 2.28.1 | Memory forensics & analysis |
| PostgreSQL | Database HA | 15 | Streaming replication & failover |
| Teleport | Zero Trust | 12.3.1 | MFA SSH + session recording |

---

## File Structure

```
Learning/
├── README.md                          # File ini
├── OpenSource_Security_Learning_Plan_10Days.md  # Rencana awal training
│
├── Progress_Hari_01_IAM_LocalStack.md     # Day 1: IAM & LocalStack
├── Progress_Hari_02_Network_Security.md   # Day 2: Network Security
├── Progress_Hari_03_MinIO_Vault.md        # Day 3: Data Encryption
├── Progress_Hari_04_Wazuh_SIEM.md         # Day 4: SIEM & Monitoring
├── Progress_Hari_05_Vulnerability_Management.md  # Day 5: Vuln Mgmt
├── Progress_Hari_06_WAF_Fail2ban.md       # Day 6: WAF & Fail2ban
├── Progress_Hari_07_IR_Forensik.md        # Day 7: IR & Forensics
├── Progress_Hari_08_BCDR_Postgres.md      # Day 8: BCDR & HA
├── Progress_Hari_09_Compliance_Access.md  # Day 9: ZTA & Compliance
├── Progress_Hari_10_Final_Capstone.md     # Day 10: Final Capstone
│
├── cek_lab_lengkap.py                 # 🆕 CEK SEMUA Hari 1-10 sekaligus (ringkas)
├── lab_checker_10hari.py              # Komprehensif checker detail Hari 1-10
├── lab_recovery.sh                    # 🆕 Recovery otomatis semua layanan
├── capstone_final_audit.py            # SOC infrastructure audit (5 pilar)
├── soc_health_check.py                # Quick health check
├── parse_report.py                    # Parser OpenSCAP XML
│
├── policy.json                        # LocalStack IAM policy
├── strict-ip-policy.json              # IP whitelist policy
├── local_rules.xml                    # Wazuh custom rules
│
├── scan-results.xml                   # OpenSCAP raw results (8.4 MB)
├── scan-report.html                   # OpenSCAP report HTML (650 KB)
├── report.html                        # OpenSCAP full report (4.1 MB)
│
└── IR-Evidence/                       # Forensics evidence folder
    ├── chain-of-custody.txt
    └── Incident-Report-INC-2026-001.md
```

---

## Cara Menjalankan Audit

### 1. Quick Health Check
```bash
cd /mnt/d/Downloads/Learning
python3 soc_health_check.py
```

### 2. Cek Semua Hari 1–10 Sekaligus (Ringkas)
```bash
# ✅ CARA TERCEPAT — cek semua hari 1-10 sekaligus
python3 cek_lab_lengkap.py

# Tampil perintah recovery untuk item yang FAIL
python3 cek_lab_lengkap.py --fix

# Cek 1 hari saja (misal Hari 8 — PostgreSQL)
python3 cek_lab_lengkap.py --day 8

# Verbose detail
python3 cek_lab_lengkap.py -v
```

### 3. Lab Checker Komprehensif (Detail)
```bash
# Checker versi lengkap dengan lebih banyak detail
python3 lab_checker_10hari.py
python3 lab_checker_10hari.py --verbose
python3 lab_checker_10hari.py --day 4
python3 lab_checker_10hari.py --report   # simpan ke file .txt
```

### 3. Full Capstone Audit (5 Pilar Enterprise)
```bash
python3 capstone_final_audit.py
```

### 4. Recovery Otomatis — Jika Layanan Offline ⚡
```bash
# ✅ CARA BARU: Recovery semua layanan Hari 1–10 sekaligus
cd /mnt/d/Downloads/Learning
bash lab_recovery.sh

# Recovery 1 hari saja (misal Hari 3 — MinIO + Vault)
bash lab_recovery.sh --day 3

# Contoh recovery per hari:
bash lab_recovery.sh --day 1   # LocalStack IAM
bash lab_recovery.sh --day 4   # Wazuh SIEM
bash lab_recovery.sh --day 8   # PostgreSQL HA
bash lab_recovery.sh --day 9   # Teleport ZTA
```

### 5. Manual Recovery (Per Stack)
```bash
# PostgreSQL HA
cd ~/bcdr-lab && docker-compose up -d

# Vault + MinIO
docker start vault minio

# Wazuh SIEM
cd ~/wazuh-docker/single-node && docker-compose up -d

# WAF
docker start waf-server backend-app

# Teleport
sudo teleport start --config=/etc/teleport.yaml &
```

---

## Lisensi & Kredit

- **Analyst:** Zulfikar
- **Environment:** WSL2 Ubuntu-22.04 + Docker Desktop + VirtualBox
- **Period:** 12–16 Mei 2026
- **Semua tools yang digunakan adalah open-source** dan bebas digunakan untuk tujuan edukasi

---

*🛡️ Open Source Security Lab | 10-Day Enterprise Security Training | 2026*
