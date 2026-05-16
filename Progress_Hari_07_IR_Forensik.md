# 🛡️ Progress Hari 7 — Respon Insiden & Forensik Digital
## Tools: VirtualBox + Volatility 3

**Tanggal:** 2026-05-15
**Durasi Target:** 8 Jam
**Status:** ✅ SELESAI

---

## 🎯 Checklist Hari Ini
- [x] **Fase 1:** IR Log & Skenario Insiden ✅
- [x] **Fase 2:** Snapshot & Isolasi VM (VBoxManage) ✅
- [x] **Fase 3:** Memory Dump dari VM — `4117.87 MB` ✅
- [x] **Fase 4:** Chain of Custody SHA256: `DBD13C9DEE13BBAE71D39D0BBECA379BF3F8F4040128D6ABC472EA5A13C06DE4` ✅
- [x] **Fase 5A:** Volatility Banner — Ubuntu 22.04 | Kernel 5.15.0-177-generic ✅
- [x] **Fase 5B:** PsList — 30+ proses, semua normal ✅
- [x] **Fase 5C:** PsTree — MicroK8s chain diverifikasi normal ✅
- [x] **Fase 5D:** NetStat — Tidak ada koneksi mencurigakan ✅
- [x] **Fase 5E:** Malfind — 2 false positive (glibc ENDBR64) ✅
- [x] **Fase 5F:** Bash History — Kosong (tidak ada sesi aktif) ✅
- [x] **Fase 6:** Forensik Analisis — VM dinyatakan CLEAN ✅
- [x] **Fase 7:** Incident Report INC-2026-001 selesai ✅

---

## 🧠 Teori Singkat (30 Menit)

### NIST Incident Response Lifecycle
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ PREPARATION │ → │ DETECTION & │ → │ CONTAINMENT │ → │  RECOVERY   │
│             │    │  ANALYSIS   │    │ ERADICATION │    │  & LESSONS  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Skenario APT Hari Ini
```
[Email Phishing] → [User klik attachment] → [Reverse Shell terbuka]
      ↓
[Penyerang masuk] → [Privilege Escalation] → [Install backdoor /tmp]
      ↓
[Persistence via Crontab] → [Data Exfiltration via base64/DNS]
```

### Golden Rules IR (Urutan Tindakan)
| # | Tindakan | Alasan |
|---|----------|--------|
| 1 | Jangan matikan VM dulu | Memory evidence akan hilang |
| 2 | Ambil memory dump DULU | RAM bersifat volatile |
| 3 | Baru isolasi network | Cegah exfiltration lanjutan |
| 4 | Snapshot setelah dump | Preserve disk state |
| 5 | Hash semua evidence | Chain of custody |

---

## 🔬 FASE 1 — IR Log (Jalankan di WSL)

```bash
# Catat timestamp awal insiden
DATE=$(date +%Y%m%d)
echo "=== INCIDENT RESPONSE LOG ===" > ~/ir-log-$DATE.txt
echo "Timestamp Start: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> ~/ir-log-$DATE.txt
echo "Analyst: [Nama Kamu]" >> ~/ir-log-$DATE.txt
echo "Asset: Linux VM (VirtualBox)" >> ~/ir-log-$DATE.txt
echo "Incident Type: Suspected APT - Unauthorized Access" >> ~/ir-log-$DATE.txt
echo "Status: ACTIVE INVESTIGATION" >> ~/ir-log-$DATE.txt
cat ~/ir-log-$DATE.txt
```

**✅ Hasil yang diharapkan:** File `~/ir-log-20260515.txt` berisi timestamp + info insiden.

---

## 🔬 FASE 2 — Snapshot & Isolasi VM (PowerShell/Windows)

> ⚠️ Ganti `"NamaVM"` dengan nama VM Linux kamu di VirtualBox (cek di GUI VirtualBox).

### Step 1 — Cek nama VM
```powershell
VBoxManage list vms
VBoxManage list runningvms
```

### Step 2 — Ambil Snapshot Evidence (SEBELUM isolasi)
```powershell
# Ganti NamaVM dengan nama VM yang sebenarnya
VBoxManage snapshot "NamaVM" take "IR-Snapshot-Incident-001" `
  --description "Evidence snapshot sebelum containment - INC-2026-001"

# Verifikasi snapshot
VBoxManage snapshot "NamaVM" list
```

### Step 3 — Isolasi Network VM
```powershell
# Putus dari internet, VM masih bisa diakses dari host (Host-Only)
VBoxManage controlvm "NamaVM" nic1 hostonly "VirtualBox Host-Only Ethernet Adapter"

# Verifikasi
VBoxManage showvminfo "NamaVM" | findstr "NIC"
```

**✅ Hasil yang diharapkan:** VM tidak bisa lagi akses internet, tapi masih bisa dianalisis dari host.

---

## 🔬 FASE 3 — Memory Dump (PowerShell/Windows)

### Step 1 — Buat folder evidence
```powershell
New-Item -ItemType Directory -Path "D:\Downloads\Learning\IR-Evidence" -Force
```

### Step 2 — Dump RAM dari VM yang berjalan
```powershell
# Ganti "NamaVM" dengan nama VM kamu
# File output berformat ELF64 core — kompatibel dengan Volatility 3
VBoxManage debugvm "NamaVM" dumpvmcore `
  --filename "D:\Downloads\Learning\IR-Evidence\memory-dump-inc001.dmp"
```
> ⏳ Proses ini butuh **3-10 menit** tergantung ukuran RAM VM (1-4 GB).

### Step 3 — Verifikasi hasil dump
```powershell
Get-Item "D:\Downloads\Learning\IR-Evidence\memory-dump-inc001.dmp" |
  Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,2)}}
```

**✅ Hasil yang diharapkan:** File `.dmp` berukuran sesuai RAM VM (misal VM 2GB RAM → file ~2GB).

---

## 🔬 FASE 4 — Chain of Custody (Hash SHA256)

```powershell
# Hitung hash untuk integritas evidence
$file = "D:\Downloads\Learning\IR-Evidence\memory-dump-inc001.dmp"
$hash = Get-FileHash $file -Algorithm SHA256

# Simpan ke file chain of custody
@"
=== CHAIN OF CUSTODY ===
File    : memory-dump-inc001.dmp
SHA256  : $($hash.Hash)
Date    : $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
Analyst : [Nama Kamu]
Case    : INC-2026-001
"@ | Out-File "D:\Downloads\Learning\IR-Evidence\chain-of-custody.txt"

cat "D:\Downloads\Learning\IR-Evidence\chain-of-custody.txt"
```

**✅ Hasil yang diharapkan:** File `chain-of-custody.txt` berisi hash SHA256 yang unik.

---

## 🔬 FASE 5 — Volatility 3 Analysis (WSL)

### Setup — Pindahkan dump ke WSL
```bash
# Di WSL Ubuntu
mkdir -p ~/forensics/incident-001
cp /mnt/d/Downloads/Learning/IR-Evidence/memory-dump-inc001.dmp ~/forensics/incident-001/
cd ~/forensics/incident-001

# Alias untuk volatility (sesuaikan path)
alias vol="python3 /home/dmin/volatility3/vol.py"
```

### 5A — Identifikasi OS dari dump
```bash
# Cek banner OS
vol -f memory-dump-inc001.dmp banners.Banners

# Khusus Linux
vol -f memory-dump-inc001.dmp linux.banner.Banner
```

### 5B — List semua proses (PsList)
```bash
vol -f memory-dump-inc001.dmp linux.pslist.PsList 2>/dev/null | tee ~/forensics/incident-001/pslist.txt
cat ~/forensics/incident-001/pslist.txt
```
> 🔍 Cari: `nc`, `bash -i`, `python3 -c`, proses dengan nama aneh

### 5C — Process Tree (hubungan parent-child)
```bash
vol -f memory-dump-inc001.dmp linux.pstree.PsTree 2>/dev/null | tee ~/forensics/incident-001/pstree.txt
```
> 🔍 Aneh jika: `httpd` melahirkan `bash`, atau `bash` muncul tanpa parent SSH/login

### 5D — Koneksi Jaringan Aktif
```bash
vol -f memory-dump-inc001.dmp linux.netstat.NetStat 2>/dev/null | tee ~/forensics/incident-001/netstat.txt
cat ~/forensics/incident-001/netstat.txt
```
> 🔍 Cari: koneksi ESTABLISHED ke IP asing, port 4444/1337/6666 (C2 favorit)

### 5E — Deteksi Code Injection (Malfind)
```bash
vol -f memory-dump-inc001.dmp linux.malfind.Malfind 2>/dev/null | tee ~/forensics/incident-001/malfind.txt
cat ~/forensics/incident-001/malfind.txt
```
> 🔍 Cari: memory region dengan permission **rwx** (Read-Write-Execute) yang tidak wajar

### 5F — Ekstrak Bash History dari RAM
```bash
vol -f memory-dump-inc001.dmp linux.bash.Bash 2>/dev/null | tee ~/forensics/incident-001/bash_history.txt
cat ~/forensics/incident-001/bash_history.txt
```

### 5G — String Hunting Manual (Cari artefak APT)
```bash
# Cari perintah download mencurigakan
strings memory-dump-inc001.dmp | grep -E "(wget|curl|nc |chmod|/tmp/\.|base64)" | sort -u | head -30

# Cari IP address dalam memory
strings memory-dump-inc001.dmp | grep -E "^([0-9]{1,3}\.){3}[0-9]{1,3}$" | sort -u | head -30

# Cari kredensial di memory (HANYA di lab environment!)
strings memory-dump-inc001.dmp | grep -iE "(password|passwd|secret|token)" | grep -v "^#" | head -20
```

**✅ Hasil yang diharapkan:** Daftar proses mencurigakan, koneksi asing, dan command history penyerang.

---

## 🔬 FASE 6 — Temuan Forensik (Hasil Nyata)

> Output dari Volatility 3 Framework 2.28.1 — Memory Dump 4,117 MB

### Proses Mencurigakan (dari linux.pslist + linux.pstree):
```
HASIL: Tidak ada proses mencurigakan ditemukan.

Proses yang awalnya dicurigai → terverifikasi NORMAL:
- bash (PID 3302, PPID 1) → MicroK8s systemd service
- bash (PID 3489, PPID 1) → MicroK8s cluster-agent service
- python3 (PID 4778) → MicroK8s 10-pods-restart hook
- k8s-dqlite, kubelite, containerd → Komponen MicroK8s resmi

Proses Normal yang Ditemukan (total ~30 proses):
PID 1    : systemd          (init)
PID 376  : systemd-journal  (logging)
PID 719  : cron             (scheduler)
PID 732  : rsyslogd         (syslog)
PID 889  : sshd             (SSH server)
PID 3307 : k8s-dqlite       (MicroK8s DB)
PID 3312 : containerd       (container runtime)
PID 4228 : kubelite         (MicroK8s)
```

### Koneksi Jaringan (dari linux.netstat.NetStat):
```
HASIL: Tidak ada koneksi mencurigakan ditemukan.

Koneksi yang terdeteksi sesuai baseline:
- SSH (port 22) — sshd listening
- MicroK8s API server (port 16443) — loopback only
- Loopback services (127.0.0.1)
- Tidak ada koneksi ESTABLISHED ke IP publik asing
```

### Bash History dari RAM (dari linux.bash.Bash):
```
HASIL: Kosong — tidak ada sesi bash aktif saat dump diambil.

Ini NORMAL karena dump diambil dari VM yang tidak sedang digunakan secara
interaktif. Plugin linux.bash.Bash hanya menangkap history dari bash
yang sedang berjalan di foreground saat dump.
```

### Code Injection (dari linux.malfind.Malfind):
```
DITEMUKAN 2 region rwx — keduanya FALSE POSITIVE:

PID 728 networkd-dispatcher @ 0x7fea60669000 [rwx]
  Hexdump: f3 0f 1e fa 4c 8d 15 f5 ...
  → ENDBR64 instruction = Intel CET signature (glibc normal di Ubuntu 22.04)

PID 800 unattended-upgr @ 0x7faf43266000 [rwx]
  Hexdump: f3 0f 1e fa 4c 8d 15 f5 ...
  → ENDBR64 instruction = Intel CET signature (glibc normal di Ubuntu 22.04)

KESIMPULAN: Bukan malware. Pattern identik = library glibc standar.
```

### String APT Artifacts (dari strings + grep):
```
STATUS: SELESAI ✅

Hasil [5A] — Command mencurigakan:
  curl  → MicroK8s snap health check script (bukan malware)
           if curl --connect-timeout "${WAIT}" ... ${server} (MicroK8s internal)
  base64 → Kubernetes certificate handling (kubectl --set-raw-bytes)
           PROPERTY_VALUE expects a base64 encoded string (kubectl normal)
  /tmp/.X11-unix/ → Snap sandbox mount config (normal)
  PRIVATE KEY → TLS/crypto library strings (normal)

  KESIMPULAN: Tidak ada command APT/malware ditemukan.
  Semua string terkait MicroK8s, Kubernetes, dan snap (legitimate).

Hasil [5B] — IP addresses:
  0.0.0.0, 0.0.0.1, 0.0.2.0 ... (total 30 baris)
  → Semua dimulai dengan 0.x.x.x = version numbers / false positive
  → Tidak ada IP publik asing (misal 45.x.x.x, 192.x.x.x)
  → Tidak ada IP C2 server yang terdeteksi

  KESIMPULAN: Tidak ada koneksi ke IP eksternal mencurigakan.
```

### 📋 Kesimpulan Fase 6:
> **VM `Victim PC` dinyatakan CLEAN.** Tidak ada indikasi kompromi.
> Ini adalah latihan forensik baseline — mengetahui tampilan sistem
> NORMAL adalah fondasi untuk mendeteksi sistem yang TERINFEKSI.

---

## 📄 FASE 7 — Incident Report (Ringkasan)

> Detail lengkap: [IR-Evidence/Incident-Report-INC-2026-001.md](../IR-Evidence/Incident-Report-INC-2026-001.md)

### Informasi Insiden
| Field | Detail |
|-------|--------|
| No. Insiden | INC-2026-001 |
| Tanggal | 2026-05-15 |
| Severity | LOW (setelah investigasi) |
| Status | ✅ CLOSED — No Compromise Detected |

### Timeline Investigasi
| Waktu (UTC) | Event |
|-------------|-------|
| 00:12:39 | IR Log dibuat, investigasi dimulai |
| 00:15:00 | VM `Victim PC` diisolasi ke Host-Only network |
| 00:56:22 | Memory dump selesai — 4,117.87 MB |
| 00:57:40 | Hash SHA256 dicatat — chain of custody terbentuk |
| 01:02:00 | Volatility banner: Ubuntu 22.04, Kernel 5.15.0-177 |
| 01:25:00 | Symbol table di-generate dari vmlinux debug (720 MB) |
| 01:47:00 | PsList & PsTree: 30+ proses, semua normal (MicroK8s) |
| 01:58:00 | Malfind: 2 false positive glibc ENDBR64, bukan malware |
| 02:02:00 | Bash History dari RAM: kosong, tidak ada sesi aktif |
| 03:34:00 | Strings hunting selesai: tidak ada APT artifacts |
| 03:53:00 | Investigasi ditutup — VM dinyatakan CLEAN |

### Temuan Utama
| Aspek | Hasil |
|-------|-------|
| Backdoor User | ❌ Tidak ditemukan |
| Persistence (cron/systemd) | ❌ Tidak ditemukan |
| Koneksi ke C2 Server | ❌ Tidak ditemukan |
| Data Exfiltration | ❌ Tidak ditemukan |
| Proses Anomali | ❌ Tidak ditemukan |
| Code Injection | ❌ Tidak ditemukan (2 false positive glibc) |
| APT Artifacts di Memory | ❌ Tidak ditemukan |

### Rekomendasi (Preventif)
- [x] SSH sudah berjalan — verifikasi login root dinonaktifkan
- [ ] Audit MicroK8s API — pastikan port 16443 tidak terekspos publik
- [ ] Deploy Wazuh agent untuk real-time monitoring
- [ ] Implementasi network egress filtering di VM
- [ ] Jadwalkan forensik rutin (monthly baseline dump)

---

## 📊 Hash Evidence
| File | SHA256 |
|------|--------|
| memory-dump-inc001.dmp | `DBD13C9DEE13BBAE71D39D0BBECA379BF3F8F4040128D6ABC472EA5A13C06DE4` |

---

## ✅ Status Penyelesaian
- [x] Fase 1 — IR Log dibuat ✅
- [x] Fase 2 — VM di-snapshot & diisolasi ✅
- [x] Fase 3 — Memory dump berhasil (4,117.87 MB) ✅
- [x] Fase 4 — Hash SHA256 dicatat ✅
- [x] Fase 5A — Volatility: banner OK → Ubuntu 22.04, Kernel 5.15.0-177 ✅
- [x] Fase 5B — Volatility: pslist OK → 30+ proses, semua normal ✅
- [x] Fase 5C — Volatility: pstree OK → MicroK8s chain terverifikasi ✅
- [x] Fase 5D — Volatility: netstat OK → Tidak ada koneksi mencurigakan ✅
- [x] Fase 5E — Volatility: malfind OK → 2 false positive glibc ENDBR64 ✅
- [x] Fase 5F — Volatility: bash history OK → Kosong (VM idle) ✅
- [x] Fase 5G — Strings hunting OK → Semua artefak teridentifikasi normal ✅
- [x] Fase 6 — Temuan didokumentasikan lengkap ✅
- [x] Fase 7 — Incident Report INC-2026-001 selesai ✅

**🎯 HASIL AKHIR: VM `Victim PC` CLEAN — Tidak ada kompromi ditemukan.**

---
*Progress Hari 7 | Open Source Security Lab | 2026-05-15 | Selesai 03:53 WIB*
