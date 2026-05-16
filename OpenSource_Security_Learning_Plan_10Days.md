# 🛡️ Keamanan Sistem & IT Operasional Enterprise (Versi Open Source)
## Program Pelatihan 10 Hari — Praktik Implementasi Lokal & Open Source

> **Target Audience:** IT Professionals, Security Engineers, System Administrators, SOC Analysts
> **Platform Focus:** Open Source, Docker, Linux, Local Virtualization (LocalStack, MinIO, Wazuh, dll)
> **Study Method:** Accelerated Sprint Learning (Teori → Lab → Studi Kasus → Praktik)

---

## 📋 Ringkasan Program

| Metrik | Detail |
|--------|--------|
| Durasi | 10 Hari (8–10 jam/hari) |
| Format | 30% Teori, 70% Hands-On Labs (Lokal) |
| Lingkungan | Docker Desktop, Oracle VirtualBox, Linux CLI |
| Deliverable | Security Runbook Siap Produksi |
| Final Assessment | Review Arsitektur + Simulasi Insiden |

### Filosofi Sprint Belajar (Siklus 3-Langkah Harian)
```text
🔵 ABSORB (2j)  →  🟡 APPLY (4j)  →  🔴 CHALLENGE (2j)
Teori + Konsep     Lab + Konfigurasi   Studi Kasus + Kuis
```

---

## 🗓️ HARI 1 — Dasar Keamanan Cloud & IAM (LocalStack)

### 🎯 Tujuan Pembelajaran
- Memahami Model Tanggung Jawab Bersama (Shared Responsibility Model)
- Menguasai arsitektur Identity and Access Management (IAM)
- Mengonfigurasi kredensial akses dengan prinsip hak istimewa paling rendah (least-privilege)

### 📖 Teori (2 Jam)
**Konsep IAM:** Penggunaan User, Group, Role, dan Policy. Logika evaluasi (Deny mengesampingkan Allow).

### 🔬 Lab 1A — Konfigurasi IAM via LocalStack (3 Jam)

#### Langkah 1: Setup LocalStack dan Bikin Admin User
```bash
# Instal awslocal (LocalStack CLI)
pip install awscli awscli-local

# Jalankan LocalStack via Docker (Gunakan tag community :3.8)
docker run -d -p 4566:4566 -p 4510-4559:4510-4559 localstack/localstack:3.8

# Buat sub-account untuk operasi admin
awslocal iam create-user --user-name security-admin

# Buat akses login (simulasi)
awslocal iam create-login-profile \
  --user-name security-admin \
  --password "Str0ng!P@ss2024" \
  --password-reset-required
```

#### Langkah 2: Buat Least-Privilege Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": ["10.0.0.0/8", "192.168.1.0/24"]
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": "iam:*",
      "Resource": "*"
    }
  ]
}
```

```bash
# Terapkan kebijakan
awslocal iam create-policy \
  --policy-name ReadOnly-EC2-Internal \
  --policy-document file://policy.json
```

### 📚 Studi Kasus 1: Kebocoran Kredensial di Perusahaan E-Commerce
*(Skenario sama: Developer tak sengaja mem-push kredensial cloud ke GitHub publik. Penyerang menyewa instance GPU. Tagihan membengkak hingga $47,000)*
**Pencegahan Lokal:** Rotasi Kunci, Whitelist IP, Pemindaian Secret di Repositori (menggunakan Trivy/TruffleHog).

---

## 🗓️ HARI 2 — Arsitektur Keamanan Jaringan (Docker/iptables)

### 🎯 Tujuan Pembelajaran
- Mendesain arsitektur jaringan yang aman (Defense-in-depth)
- Mengonfigurasi firewall dan aturan akses (iptables/UFW)
- Menerapkan pola Bastion Host / Jump Server

### 🔬 Lab 2A — Arsitektur Tiga Tingkat (4 Jam)

#### Langkah 1: Setup Jaringan Terisolasi (Docker Networks)
```bash
# Jaringan Publik untuk Web
docker network create --driver bridge public-net

# Jaringan Privat untuk App
docker network create --driver bridge --internal private-app-net

# Jaringan Privat untuk DB
docker network create --driver bridge --internal private-db-net
```

#### Langkah 2: Simulasi Security Groups menggunakan iptables (pada Linux VM)
```bash
# Blokir semua koneksi masuk (Default Deny)
iptables -P INPUT DROP

# Izinkan lalu lintas lokal
iptables -A INPUT -i lo -j ACCEPT

# Izinkan koneksi HTTP/HTTPS dari internet ke Web Server (Port 80, 443)
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Izinkan SSH HANYA dari IP Bastion Host (misal 10.0.0.50)
iptables -A INPUT -p tcp -s 10.0.0.50 --dport 22 -j ACCEPT

# (Di Server DB) Izinkan port 3306 HANYA dari jaringan App (misal 10.0.1.0/24)
iptables -A INPUT -p tcp -s 10.0.1.0/24 --dport 3306 -j ACCEPT
```

### 📚 Studi Kasus 2: Database Terekspos ke Internet
*(Skenario sama: Database MySQL terekspos karena konfigurasi Firewall/Security Group 0.0.0.0/0. Dicuri via SQL Injection)*
**Penyelesaian:** Pastikan port database tidak memiliki IP publik, implementasikan enkripsi *in-transit*.

---

## 🗓️ HARI 3 — Keamanan Data & Enkripsi (MinIO & Vault)

### 🎯 Tujuan Pembelajaran
- Mengimplementasikan enkripsi saat diam (at rest) dan berpindah (in transit)
- Mengonfigurasi HashiCorp Vault sebagai Key Management System (KMS)
- Mengamankan object storage lokal dengan MinIO

### 🔬 Lab 3A — Implementasi MinIO & KMS

#### Langkah 1: Jalankan Vault & MinIO (dengan fitur KMS)
```bash
# Jalankan Vault dev server (Gunakan image resmi)
docker run -d --name vault --cap-add=IPC_LOCK -e 'VAULT_DEV_ROOT_TOKEN_ID=myroot' -p 8200:8200 hashicorp/vault:1.13.3

# Konfigurasi transit secret engine di Vault untuk MinIO KMS
docker exec -it <vault_container> sh
vault secrets enable transit
vault write -f transit/keys/minio-key

# Jalankan MinIO dengan KMS yang diarahkan ke Vault
docker run -d -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=password" \
  -e "MINIO_KMS_VAULT_ENDPOINT=http://<vault_ip>:8200" \
  -e "MINIO_KMS_VAULT_KEY_NAME=minio-key" \
  minio/minio server /data --console-address ":9001"
```

#### Langkah 2: Konfigurasi Object Lock & Versioning
```bash
# Gunakan MinIO Client (mc)
mc alias set myminio http://localhost:9000 admin password

# Buat bucket dengan fitur Object Lock (WORM)
mc mb --with-lock myminio/secure-financial-data

# Aktifkan versioning
mc version enable myminio/secure-financial-data

# Setel mode retention ke COMPLIANCE (data tidak bisa dihapus walau oleh admin selama 365 hari)
mc retention set --default compliance 365d myminio/secure-financial-data
```

### 📚 Studi Kasus 3: Serangan Ransomware pada Storage
*(Skenario sama: Ransomware mengakses dan menghapus seluruh log medis. Data hilang karena tidak ada backup).*
**Pencegahan:** Object Lock (WORM) dan Versioning di MinIO menyelamatkan file yang dienkripsi dengan merevert ke versi sebelumnya.

---

## 🗓️ HARI 4 — Security Monitoring & SIEM (Wazuh)

### 🎯 Tujuan Pembelajaran
- Mengonfigurasi log sentral dan audit trail
- Mengatur peringatan real-time menggunakan Wazuh SIEM
- Membangun dashboard Security Operations Center (SOC) lokal

### 🔬 Lab 4A — Implementasi SIEM & Alerting

#### Langkah 1: Instalasi Wazuh (Docker Compose)
```bash
git clone https://github.com/wazuh/wazuh-docker.git -b v4.7.0
cd wazuh-docker/single-node
docker-compose up -d

# Akses dashboard Wazuh di https://localhost
```

#### Langkah 2: Konfigurasi Peringatan Keamanan Kritis
*Wazuh secara bawaan sudah memiliki aturan (rules). Anda dapat menambahkannya di `local_rules.xml`.*
```xml
<!-- Deteksi >5 gagal login (Kemungkinan Brute Force SSH) -->
<rule id="100001" level="10" frequency="5" timeframe="60">
  <if_matched_sid>5716</if_matched_sid>
  <description>SSH Brute force attack detected (Multiple failed logins)</description>
  <group>authentication_failures,</group>
</rule>
```

---

## 🗓️ HARI 5 — Manajemen Kerentanan (OpenSCAP & Trivy)

### 🎯 Tujuan Pembelajaran
- Implementasi pemindaian kerentanan (vulnerability scanning) secara otomatis
- Menerapkan baseline kepatuhan konfigurasi (CIS Benchmarks)

### 🔬 Lab 5A — Konfigurasi Security Baseline

#### Langkah 1: Scanning Kerentanan dengan Trivy
```bash
# Instal Trivy
sudo apt-get install trivy

# Scan image container lokal (mencari Log4Shell, kerentanan package)
trivy image nginx:latest

# Scan filesystem proyek web
trivy fs /opt/my-app/
```

#### Langkah 2: Audit Kepatuhan dengan OpenSCAP (Linux)
```bash
# Instal OpenSCAP
sudo apt install -y libopenscap8 openscap-scanner unzip
wget https://github.com/ComplianceAsCode/content/releases/download/v0.1.73/scap-security-guide-0.1.73.zip
unzip scap-security-guide-0.1.73.zip
sudo mkdir -p /usr/share/xml/scap/ssg/content/
sudo cp scap-security-guide-0.1.73/ssg-ubuntu2204-ds.xml /usr/share/xml/scap/ssg/content/

# Jalankan audit berdasarkan CIS Ubuntu Baseline
oscap xccdf eval \
  --profile xccdf_org.ssgproject.content_profile_cis_level2_server \
  --results scan-results.xml \
  --report report.html \
  /usr/share/xml/scap/ssg/content/ssg-ubuntu2204-ds.xml
```

### 📚 Studi Kasus 5: Eksploitasi Kerentanan (Log4Shell) Belum Di-patch
*(Skenario sama: Perusahaan telat menambal Log4Shell, instance berhasil dibobol).*

---

## 🗓️ HARI 6 — Keamanan Aplikasi (ModSecurity & Fail2ban)

### 🎯 Tujuan Pembelajaran
- Melakukan deploy dan konfigurasi Web Application Firewall (WAF)
- Implementasi perlindungan DDoS dasar (Brute Force/Flood) pada level host

### 🔬 Lab 6A — Konfigurasi WAF & Fail2ban

#### Langkah 1: Deploy Nginx dengan ModSecurity (Docker)
```bash
# Jalankan container ModSecurity + OWASP Core Rule Set
docker run -d -p 80:80 -e PROXY_UPSTREAM=http://<app_ip>:8080 owasp/modsecurity-crs:nginx
```
*ModSecurity yang dilengkapi CRS (Core Rule Set) otomatis akan memblokir serangan SQL Injection, XSS, dan Local File Inclusion (LFI).*

#### Langkah 2: Setup Fail2ban untuk Mitigasi Serangan
```bash
# Instal Fail2ban di server
sudo apt install fail2ban

# Konfigurasi file jail (/etc/fail2ban/jail.local)
[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 3
bantime  = 3600
```

---

## 🗓️ HARI 7 — Respon Insiden & Forensik (VirtualBox + Volatility)

### 🎯 Tujuan Pembelajaran
- Membuat dan mengeksekusi Incident Response Plan (IRP)
- Melakukan investigasi forensik digital
- Mempraktikkan pengisolasian / karantina mesin lokal

### 🔬 Lab 7A — Simulasi Respon Insiden (IR)

#### Langkah 1: Isolasi & Forensik Mesin (VirtualBox)
```bash
# Skenario: VM Linux terdeteksi menginfeksi jaringan
# 1. Isolasi Mesin: Ubah adapter jaringan di VirtualBox ke 'Host-Only'
VBoxManage modifyvm "Ubuntu-Server" --nic1 hostonly

# 2. Ambil Snapshot (untuk pelestarian bukti Digital Forensics)
VBoxManage snapshot "Ubuntu-Server" take "IR-Snapshot-Incident-001"
```

#### Langkah 2: Analisis Forensik RAM dengan Volatility
```bash
# Dapatkan file memory dump dari VirtualBox (.sav file)
# Analisis dengan framework Volatility 3 (Install dengan: pip3 install .)
python3 vol.py -f dump.sav linux.pslist.PsList
python3 vol.py -f dump.sav linux.malfind.Malfind
```

### 📚 Studi Kasus 7: Advanced Persistent Threat (APT)
*(Skenario sama: Lingkungan disusupi via email phishing. Penyerang menanam kredensial persisten dan mengeksfiltrasi data).*

---

## 🗓️ HARI 8 — Kelangsungan Bisnis & Disaster Recovery

### 🎯 Tujuan Pembelajaran
- Merancang strategi pencadangan dan pemulihan (RTO & RPO)
- Mengonfigurasi replikasi otomatis antar lingkungan (Failover lokal)

### 🔬 Lab 8A — Replikasi Database Aktif-Pasif

```bash
# Gunakan PostgreSQL (Master & Replica) untuk mensimulasikan lingkungan DR (Disaster Recovery).
# Konfigurasi log streaming replikasi asinkron (WAL streaming).

# Script Otomasi Tes DR (dr-test.sh)
#!/bin/bash
echo "Mulai Pengujian DR - $(date)"

# 1. Simulasikan matinya server Primary
docker stop pg-master

# 2. Lakukan Failover: Promosikan Replica menjadi Primary
docker exec -it pg-replica su - postgres -c "/usr/lib/postgresql/13/bin/pg_ctl promote -D /var/lib/postgresql/data"

echo "Failover berhasil diselesaikan. Target RTO: < 15 menit."
```

---

## 🗓️ HARI 9 — Zero Trust Architecture (Teleport)

### 🎯 Tujuan Pembelajaran
- Menerapkan prinsip Zero Trust ("Never Trust, Always Verify") di arsitektur lokal
- Menghapus port publik seperti 22 (SSH) melalui konfigurasi VPN-less

### 🔬 Lab 9A — Implementasi Akses Jarak Jauh Aman dengan Teleport

```bash
# Menggunakan Teleport versi Open Source
# 1. Instalasi Agen
curl https://goteleport.com/static/install.sh | bash -s 12.3.1

# 2. Konfigurasi cluster Zero Trust
teleport configure --acme --acme-email=admin@example.com --cluster-name=tele.example.com > /etc/teleport.yaml

# 3. Jalankan service Teleport
systemctl start teleport
```
*Hasil:* Anda tidak perlu lagi login via port 22. Semua sesi SSH diakses langsung lewat peramban web dan diautentikasi dengan MFA (TOTP).

---

## 🗓️ HARI 10 — Operasional SOC & Tata Kelola Keamanan

### 🎯 Tujuan Pembelajaran
- Membangun checklist keamanan operasional untuk tim SOC
- Melakukan Review Arsitektur Akhir (Capstone)

### 🔬 Final Lab — Capstone Checklist Keamanan Enterprise
```text
IDENTITAS & AKSES (IAM)
☑ Kata sandi administrator aman + MFA selalu aktif
☑ Praktik Least Privilege diterapkan via LocalStack policy

JARINGAN & INFRASTRUKTUR
☑ Isolasi menggunakan iptables (Linux/VM) berhasil dites
☑ Tidak ada service management port (seperti port 22, 3389) yang terekspos langsung ke internet
☑ Aplikasi berjalan di belakang reverse proxy WAF (ModSecurity)

KEAMANAN DATA
☑ Object Lock (WORM) di MinIO aktif untuk file sensitif
☑ Vault digunakan untuk merotasi rahasia dan kunci enkripsi KMS

PEMANTAUAN (MONITORING)
☑ Agen Wazuh terhubung di semua server target
☑ Alarm kegagalan login dan peretasan dikonfigurasi masuk via webhook (Discord/Slack/DingTalk)
☑ OpenSCAP digunakan secara berkala untuk mengecek kepatuhan CIS (Compliance)

DISASTER RECOVERY
☑ Tes replikasi database (Failover) dan restorasi penyimpanan terbukti di bawah RTO limit
```

---
*Versi: 1.0 (Open Source Edition) | Klasifikasi: Public Learning Material*
