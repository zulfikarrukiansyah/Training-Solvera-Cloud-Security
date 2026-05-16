# 📑 Progress Hari 09 — Compliance & Secure Access
## Lab: Teleport Zero Trust SSH & OpenSCAP Compliance Audit

**Tanggal:** 2026-05-15
**Durasi Target:** 8 Jam
**Status:** ✅ SELESAI

---

## 🎯 Checklist Hari Ini
- [x] **Fase 1:** Instalasi & Konfigurasi Teleport (Zero Trust Access) ✅
- [x] **Fase 2:** Aktivasi MFA (TOTP) untuk akses terminal ✅
- [x] **Fase 3:** OpenSCAP — Scan kepatuhan terhadap standar CIS ✅
- [x] **Fase 4:** Remediasi otomatis temuan audit kritis ✅
- [x] **Fase 5:** Demonstrasi Secure Access & Session Recording ✅

---

## 🏗️ Arsitektur Akses

```
[Analis/Admin]
      |
      | HTTPS + MFA (TOTP)
      ↓
[Teleport Proxy :3080]
      |
      | SSH via Short-Lived Certificates (bukan password/key)
      ↓
[Internal Server / WSL Node]
      |
      └─── Audit Log + Session Recording → Teleport Auth Server
```

**Catatan Teknis:**
- Lingkungan: WSL Ubuntu-22.04 (native)
- Teleport: Open Source Edition v12.3.1
- Compliance Standard: CIS Benchmark (via OpenSCAP / SSG)
- Target scan: `ssg-ubuntu2204-ds.xml`

---

## 🔬 FASE 1 — Instalasi & Konfigurasi Teleport

### Step 1 — Instalasi Teleport
```bash
# Install Teleport Open Source Edition v12.3.1
curl https://goteleport.com/static/install.sh | bash -s 12.3.1

# Verifikasi instalasi
teleport version
```

### Step 2 — Generate Konfigurasi Awal
```bash
# Inisialisasi config tanpa ACME (untuk pengujian lokal / non-domain)
sudo teleport configure --cluster-name=teleport.local | sudo tee /etc/teleport.yaml > /dev/null

# Cek isi konfigurasi
cat /etc/teleport.yaml | head -30
```

### Step 3 — Jalankan Teleport Service
```bash
# Jalankan di background (untuk lab/testing)
sudo teleport start --config=/etc/teleport.yaml &

# Verifikasi service berjalan
sleep 3 && teleport status
```

### Step 4 — Buat User Admin
```bash
# Buat user dengan role admin dan set MFA
sudo tctl users add admin --roles=editor,access --logins=ubuntu,root

# Salin URL invitation yang dihasilkan untuk langkah MFA
```

**✅ Hasil yang diharapkan:** Teleport service berjalan di port 3080, user `admin` berhasil dibuat.

### Isu yang Dihadapi & Solusi:
| Isu | Penyebab | Solusi |
|-----|----------|--------|
| Port 443 conflict | Port sudah dipakai HTTPS lain | Ubah `web_listen_addr` ke `:3080` di teleport.yaml |
| `certificate signed by unknown authority` | ACME tidak aktif / self-signed | Tambahkan `insecure_skip_verify: true` untuk lab, atau akses via `https://localhost:3080` |
| Service mati setelah terminal ditutup | Dijalankan tanpa daemon | Gunakan `nohup` atau `systemctl enable teleport` |

---

## 🔬 FASE 2 — Aktivasi MFA (TOTP)

### Step 1 — Registrasi MFA via Invite Link
- Buka URL invitation dari Step 4 Fase 1 di browser
- Scan QR Code dengan **Google Authenticator** atau **Authy**
- Set password + konfirmasi OTP 6-digit

### Step 2 — Login via tsh (Teleport CLI)
```bash
# Login ke cluster lokal
tsh login --proxy=localhost:3080 --insecure --user=admin

# Verifikasi session aktif
tsh status
```

### Step 3 — SSH ke Node via Teleport (Zero Trust)
```bash
# SSH tanpa menggunakan private key — menggunakan certificate sementara
tsh ssh ubuntu@localhost

# Verifikasi: port 22 tidak digunakan langsung
ss -tlnp | grep :22
```

**✅ Hasil:** Login berhasil menggunakan TOTP tanpa port 22 tradisional.

### Isu yang Dihadapi & Solusi:
| Isu | Penyebab | Solusi |
|-----|----------|--------|
| `tsh: command not found` | PATH belum di-set | `export PATH=$PATH:/usr/local/bin/tsh` atau install ulang via script |
| MFA tidak muncul saat login | TOTP belum dikonfigurasi di teleport.yaml | Tambahkan `second_factor: otp` di blok `auth_service.authentication` |

---

## 🔬 FASE 3 — Compliance Auditing dengan OpenSCAP

### Step 1 — Instalasi OpenSCAP Scanner
```bash
# Install hanya scanner-nya dulu (tersedia di repo utama)
sudo apt update && sudo apt install -y openscap-scanner

# Verifikasi
oscap --version
```

### Step 2 — Download SCAP Security Guide (SSG) Manual

> ⚠️ **Masalah yang Dihadapi:** Package `ssg-base`, `ssg-debian`, dll. dari Ubuntu universe repo **tidak tersedia / gagal install** via `apt`. Solusinya adalah download langsung dari GitHub ComplianceAsCode.

```bash
# Download SCAP Security Guide versi terbaru dari GitHub releases
# (Cek versi terbaru di https://github.com/ComplianceAsCode/content/releases)
SSG_VERSION="0.1.72"  # sesuaikan versi terbaru saat ini
wget -q "https://github.com/ComplianceAsCode/content/releases/download/v${SSG_VERSION}/scap-security-guide-${SSG_VERSION}.zip" \
  -O /tmp/ssg.zip

# Ekstrak ke direktori lokal
mkdir -p ~/ssg && unzip -q /tmp/ssg.zip -d ~/ssg

# Cek file benchmark Ubuntu 22.04 tersedia
ls ~/ssg/scap-security-guide-${SSG_VERSION}/ | grep ubuntu
# Output yang diharapkan: ssg-ubuntu2204-ds.xml
```

### Step 3 — Scanning terhadap Standar CIS (Profil Standard)
```bash
# Set path ke SSG yang sudah di-download manual
SSG_FILE=~/ssg/scap-security-guide-0.1.72/ssg-ubuntu2204-ds.xml

# Jalankan scan pertama — hasil disimpan ke XML dan HTML
oscap xccdf eval \
  --profile xccdf_org.ssgproject.content_profile_standard \
  --results /mnt/d/Downloads/Learning/scan-results.xml \
  --report /mnt/d/Downloads/Learning/scan-report.html \
  "$SSG_FILE"

echo "Scan selesai. Buka scan-report.html di browser untuk melihat laporan."
```

### Step 4 — Parse Skor Awal dari Hasil XML
```bash
# Cek skor kepatuhan awal
grep -oP 'score.*?</score>' /mnt/d/Downloads/Learning/scan-results.xml | head -5

# Atau gunakan parse_report.py jika tersedia
python3 /mnt/d/Downloads/Learning/parse_report.py /mnt/d/Downloads/Learning/scan-results.xml 2>/dev/null
```

**✅ Hasil:** Laporan HTML (`scan-report.html`) berhasil dibuat menggunakan SSG yang didownload manual. Skor awal didapatkan sebelum remediasi.

### Isu yang Dihadapi & Solusi:
| Isu | Penyebab | Solusi |
|-----|----------|--------|
| `ssg-base` tidak bisa diinstall via apt | Package `ssg-*` di Ubuntu universe repo **tidak tersedia** di WSL / versi repo ini | **Download manual** dari GitHub: `github.com/ComplianceAsCode/content/releases` |
| `ssg-ubuntu2204-ds.xml: No such file` | Path ke SSG salah setelah download manual | Gunakan path hasil ekstrak: `~/ssg/scap-security-guide-X.X.XX/ssg-ubuntu2204-ds.xml` |
| `oscap: command not found` | Package openscap-scanner belum ada | `sudo apt install -y openscap-scanner` |
| Scan sangat lama (20–40 menit) | Profil `standard` memiliki 200+ rule, file dump besar | Biarkan berjalan; gunakan `tee` untuk log jika perlu |
| `unzip: command not found` | Tool belum terinstall | `sudo apt install -y unzip` |

---

## 🔬 FASE 4 — Remediasi Otomatis

OpenSCAP bukan hanya alat audit — ia juga bisa menghasilkan skrip Bash atau Ansible Playbook untuk memperbaiki temuan secara otomatis.

### Step 1 — Generate Skrip Remediasi
```bash
# Generate Bash remediation script dari hasil scan
oscap xccdf generate fix \
  --fix-type bash \
  --result-id "" \
  scan-results.xml > remediation.sh

# Tinjau isinya sebelum dijalankan
head -50 remediation.sh
```

### Step 2 — Jalankan Remediasi dengan sudo
```bash
# Jalankan sebagai root untuk perbaikan parameter kernel & file sistem
sudo bash remediation.sh 2>&1 | tee remediation-log.txt

echo "Remediasi selesai. Cek log di remediation-log.txt"
```

### Step 3 — Scan Ulang untuk Verifikasi (Final Scan)
```bash
# Scan kedua setelah remediasi
oscap xccdf eval \
  --profile xccdf_org.ssgproject.content_profile_standard \
  --results final-results.xml \
  --report final-report.html \
  /usr/share/xml/scap/ssg/content/ssg-ubuntu2204-ds.xml

echo "Final scan selesai. Bandingkan skor di final-report.html"
```

### Step 4 — Verifikasi Akhir
- Skor akhir tervalidasi di `final-report.html`
- Temuan partisi diabaikan (batasan WSL — tidak ada `/boot` atau `/tmp` terpisah)
- Keamanan file sistem (`/etc/shadow`) dan SSH terverifikasi **aman**

### Isu yang Dihadapi & Solusi:
| Isu | Penyebab | Solusi |
|-----|----------|--------|
| `Operation not permitted` pada beberapa fix | WSL tidak support semua sysctl | Skip rule partisi — tandai sebagai `not applicable` untuk WSL environment |
| Skor tidak naik signifikan | Beberapa fix memerlukan reboot | Jalankan `sudo sysctl --system` untuk reload parameter kernel tanpa reboot |
| `remediation.sh` kosong | `--result-id ""` mungkin tidak match | Cek ID di scan-results.xml: `grep 'TestResult id' scan-results.xml` |

---

## 🔬 FASE 5 — Demonstrasi Secure Access (Studi Kasus)

### Step 1 — Akses Terminal via Web Proxy
```bash
# Buka Teleport Dashboard di browser
# URL: https://localhost:3080

# Login dengan admin + OTP → buka menu "Servers"
# Klik "Connect" pada node WSL → terminal terbuka di browser (tanpa SSH port 22)
```

### Step 2 — Simulasi Aktivitas (untuk Session Recording)
```bash
# Lakukan aktivitas yang akan terekam
cat /etc/shadow | head -3          # membaca file sensitif
ls -la /etc/ssh/sshd_config        # cek konfigurasi SSH
id && whoami                        # cek user aktif
```

### Step 3 — Verifikasi Session Recording & Audit Log
- Buka menu **Activity** di dashboard Teleport
- Temukan sesi yang baru dibuat → klik **Play** untuk memutar ulang rekaman
- Buka menu **Audit Log** → verifikasi event `session.start` dan `session.end` tercatat

**✅ Hasil:** Setiap aktivitas terminal terekam secara penuh dan dapat di-replay sebagai bukti forensik.

---

## 🧠 Konsep Kunci yang Dipelajari

| Konsep | Penjelasan |
|--------|------------|
| Zero Trust | Model keamanan: "Jangan percaya siapapun, verifikasi semua" — tidak ada implicit trust meski di dalam jaringan internal |
| Teleport | Platform akses Zero Trust — mengganti SSH tradisional dengan certificate-based + MFA |
| TOTP | Time-based One-Time Password — kode 6-digit yang berubah setiap 30 detik sebagai faktor kedua |
| Short-Lived Certificate | Teleport menerbitkan certificate sementara (bukan kunci permanen) — expired otomatis |
| Session Recording | Rekaman video dari setiap sesi terminal — wajib ada untuk audit forensik & compliance |
| OpenSCAP | Open-source scanner untuk audit kepatuhan konfigurasi sistem terhadap standar industri |
| SCAP | Security Content Automation Protocol — standar format untuk benchmark keamanan |
| CIS Benchmark | Panduan konfigurasi aman yang diterbitkan Center for Internet Security |
| SSG (SCAP Security Guide) | Koleksi rule dan remediation yang siap pakai untuk berbagai OS |
| Remediation | Proses otomatis perbaikan konfigurasi berdasarkan temuan audit |

---

## 📋 Rekomendasi Peningkatan (Production)
- [ ] Integrasikan Teleport dengan **LDAP/Active Directory** untuk manajemen user terpusat
- [ ] Konfigurasi **Role-Based Access Control (RBAC)** di Teleport — batasi akses per tim/role
- [ ] Simpan **Audit Log Teleport** ke SIEM (misal Wazuh) untuk real-time alerting
- [ ] Jadwalkan OpenSCAP scan otomatis via **cron** atau CI/CD pipeline
- [ ] Gunakan **Ansible Playbook** untuk remediation massal di banyak server sekaligus
- [ ] Implementasi **Teleport Application Access** untuk melindungi web app internal

---

## 📊 Metrik Lab

| Metric | Nilai |
|--------|-------|
| Teleport Version | v12.3.1 OSS |
| MFA Method | TOTP (Google Authenticator) |
| Jumlah Rule Scan (CIS Standard) | 200+ rules |
| File Laporan HTML | `scan-report.html`, `final-report.html` |
| Temuan Partisi (WSL limitation) | Diabaikan / not applicable |
| Session Recording | ✅ Aktif & berhasil di-replay |
| Audit Log | ✅ event session.start & session.end tercatat |

---

## ✅ Status Penyelesaian
- [x] Fase 1 — Teleport terinstall & service berjalan ✅
- [x] Fase 2 — User admin dibuat + MFA (TOTP) aktif ✅
- [x] Fase 3 — Scan OpenSCAP pertama selesai ✅
- [x] Fase 4 — Laporan HTML (`scan-report.html`) dianalisis ✅
- [x] Fase 4 — Skrip remediasi dijalankan ✅
- [x] Fase 4 — Scan kedua (`final-report.html`) diverifikasi ✅
- [x] Fase 5 — Akses Web Terminal via Teleport (tanpa port 22) ✅
- [x] Fase 5 — Session Recording berhasil di-replay ✅
- [x] Fase 5 — Audit Log terverifikasi ✅

**🎯 KESIMPULAN HARI 09:**
Sistem kini memiliki dua lapis pertahanan tambahan:
1. **Teleport:** Mengamankan akses administratif dengan Zero Trust, MFA (TOTP), dan **Session Recording** sebagai bukti forensik yang dapat di-replay.
2. **OpenSCAP:** Memastikan konfigurasi sistem patuh terhadap standar CIS Benchmark, dengan kemampuan remediasi otomatis untuk memperbaiki temuan kritis.

---
*Progress Hari 9 | Open Source Security Lab | 2026-05-15 | Selesai 14:00 WIB*
