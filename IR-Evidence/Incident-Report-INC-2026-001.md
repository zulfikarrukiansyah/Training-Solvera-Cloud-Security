# 📋 LAPORAN INSIDEN KEAMANAN
## Case: INC-2026-001 | Forensik Memory — VM Victim PC

---

**No. Insiden   :** INC-2026-001
**Tanggal       :** 2026-05-15
**Waktu Mulai   :** 00:12:39 UTC
**Severity      :** LOW (setelah investigasi)
**Status        :** ✅ CLOSED — No Compromise Detected
**Analyst       :** Security Student

---

## 📌 Ringkasan Eksekutif

VM `Victim PC` (Ubuntu 22.04 Jammy, Kernel 5.15.0-177-generic) dilaporkan
sebagai target investigasi forensik dalam skenario APT latihan Hari 7.
Memory dump sebesar **4,117 MB** berhasil diambil menggunakan `VBoxManage debugvm`
dan dianalisis menggunakan **Volatility 3 Framework 2.28.1**.

**Hasil investigasi: Tidak ditemukan indikasi kompromi.** Semua proses,
koneksi jaringan, dan artefak memori sesuai dengan baseline sistem Ubuntu 22.04
minimal dengan MicroK8s dan SSH aktif.

---

## 🔗 Chain of Custody

| Item | Detail |
|------|--------|
| File Evidence | `memory-dump-inc001.dmp` |
| Ukuran File | 4,117.87 MB |
| SHA256 Hash | `DBD13C9DEE13BBAE71D39D0BBECA379BF3F8F4040128D6ABC472EA5A13C06DE4` |
| Waktu Akuisisi | 2026-05-15T01:56:22Z |
| Tools Digunakan | VBoxManage 7.2.8, Volatility 3.2.28.1, dwarf2json v0.9.0 |
| Symbol Table | `ubuntu-5.15.0-177-generic.json.gz` (dari ddeb Ubuntu) |

---

## ⏱️ Timeline Investigasi

| Waktu (UTC) | Tindakan |
|-------------|----------|
| 00:12:39 | IR Log dibuat, investigasi dimulai |
| 00:15:00 | VM `Victim PC` diisolasi ke Host-Only network |
| 00:56:22 | Memory dump selesai (4,117 MB via VBoxManage debugvm) |
| 00:57:40 | SHA256 hash dicatat — chain of custody terbentuk |
| 01:02:00 | Volatility banner scan — OS teridentifikasi |
| 01:25:00 | Symbol table di-generate dari vmlinux debug (720 MB) |
| 01:47:00 | PsList & PsTree selesai — proses dianalisis |
| 01:58:00 | Malfind selesai — tidak ada injeksi kode |
| 02:02:00 | Bash History dari RAM — kosong (tidak ada sesi aktif) |
| 03:34:00 | Strings hunting selesai — tidak ada APT artifacts |
| 03:53:00 | Investigasi ditutup — VM dinyatakan CLEAN |

---

## 🔬 Temuan Forensik Detail

### [A] Identifikasi Sistem
```
OS      : Ubuntu 22.04 LTS (Jammy)
Kernel  : 5.15.0-177-generic #187-Ubuntu SMP
Compiler: gcc 11.4.0 (Ubuntu)
Build   : Sat Apr 11 22:54:33 UTC 2026
```

### [B] Process List — Volatility linux.pslist.PsList

**Proses Utama yang Ditemukan:**

| PID | Proses | PPID | Penilaian |
|-----|--------|------|-----------|
| 1 | systemd | 0 | ✅ Normal |
| 376 | systemd-journal | 1 | ✅ Normal |
| 415 | multipathd | 1 | ✅ Normal |
| 568 | systemd-timesyn | 1 | ✅ Normal |
| 719 | cron | 1 | ✅ Normal |
| 721 | dbus-daemon | 1 | ✅ Normal |
| 732 | rsyslogd | 1 | ✅ Normal |
| 737 | snapd | 1 | ✅ Normal |
| 761 | ModemManager | 1 | ✅ Normal |
| 792 | login | 1 | ✅ Normal |
| 889 | sshd | 1 | ✅ Normal |
| 3302 | k8s-dqlite | 1 | ✅ Normal (MicroK8s) |
| 3312 | containerd | 1 | ✅ Normal (MicroK8s) |
| 3489 | bash | 1 | ✅ Normal (MicroK8s systemd service) |
| 4228 | kubelite | 1 | ✅ Normal (MicroK8s) |

**Proses Mencurigakan:** ❌ Tidak ada

### [C] Process Tree — Volatility linux.pstree.PsTree

Ditemukan process chain yang awalnya mencurigakan:
```
bash (PID 3302)
  └── python3 (PID 4778)
        └── 10-pods-restart (PID 4779)   ← nama mencurigakan
              └── python3 (PID 4789)
                    └── bash (PID 4803)
                          └── sudo (PID 4813)
                                └── ctr (PID 4814)
```

**Kesimpulan:** Setelah diverifikasi, seluruh chain ini adalah bagian dari
**MicroK8s** (Kubernetes versi single-node Ubuntu). Script `10-pods-restart`
adalah hook resmi MicroK8s. **Tidak mencurigakan.**

### [D] Network Connections — Volatility linux.netstat.NetStat

**Koneksi Mencurigakan:** ❌ Tidak ada
**Koneksi Normal:** SSH (port 22), MicroK8s API (port 16443), loopback services

### [E] Code Injection — Volatility linux.malfind.Malfind

Ditemukan 2 memory region dengan flag `rwx`:

| PID | Proses | Alamat | Penilaian |
|-----|--------|--------|-----------|
| 728 | networkd-dispatcher | 0x7fea60669000 | ✅ False positive (glibc ENDBR64) |
| 800 | unattended-upgr | 0x7faf43266000 | ✅ False positive (glibc ENDBR64) |

**Catatan:** Pattern `f3 0f 1e fa` = instruksi `ENDBR64` adalah signature
Intel CET (Control-flow Enforcement) yang normal di Ubuntu 22.04. Bukan malware.

### [F] Bash History dari RAM — Volatility linux.bash.Bash

```
(kosong — tidak ada sesi bash aktif saat dump diambil)
```

### [G] String Hunting — strings + grep

**Hasil [5A] — Command mencurigakan:**
```
curl  → MicroK8s snap health check (bukan malware)
        if curl --connect-timeout "${WAIT}" ... ${server}
base64 → Kubernetes certificate handling (kubectl normal)
        PROPERTY_VALUE expects a base64 encoded string
/tmp/.X11-unix/ → Snap sandbox mount config (normal)
PRIVATE KEY → TLS/crypto library strings (normal)
```

**Hasil [5B] — IP addresses (30 baris):**
```
0.0.0.0, 0.0.0.1, 0.0.2.0, 0.0.2.15 ...
→ Semua 0.x.x.x = version numbers / false positive regex
→ Tidak ada IP publik asing terdeteksi
→ Tidak ada C2 server IP
```

**Kesimpulan:** ✅ Tidak ada APT artifacts. Semua string legitimate dari MicroK8s/K8s/snap.

---

## 🧠 Pembelajaran Forensik dari Lab Ini

### ✅ Skill yang Dipraktikkan
1. **Memory Acquisition** — `VBoxManage debugvm dumpvmcore` untuk VM yang running
2. **Chain of Custody** — SHA256 hash sebelum analisis
3. **Symbol Table Generation** — dwarf2json + vmlinux debug → ISF untuk Volatility 3
4. **OS Identification** — `banners.Banners` plugin
5. **Process Analysis** — membedakan proses normal vs anomali
6. **False Positive Recognition** — ENDBR64 = glibc, bukan injeksi malware
7. **Baseline Comparison** — mengetahui "normal" untuk bisa deteksi "abnormal"

### 📚 Konsep Kunci yang Dipelajari

| Konsep | Penjelasan |
|--------|------------|
| Memory Forensics | RAM adalah volatile evidence — harus diambil SEBELUM shutdown |
| Symbol Table (ISF) | Volatility butuh "peta" struktur kernel untuk baca memory |
| false positive | Malfind sering hasilkan false positive dari glibc/JIT |
| Baseline | Tanpa tahu "normal", kita tidak bisa tahu yang "mencurigakan" |
| Chain of Custody | Hash evidence = integritas forensik di pengadilan |

---

## 📋 Rekomendasi

Karena **tidak ditemukan kompromi**, rekomendasi bersifat preventif:

- [ ] **Hardening SSH** — Nonaktifkan login root, gunakan key-based auth saja
- [ ] **Audit MicroK8s** — Pastikan API port 16443 tidak terekspos ke public
- [ ] **Deploy Wazuh agent** — Untuk monitoring real-time (integrasi hari ke-4)
- [ ] **Automatic Security Updates** — `unattended-upgr` sudah aktif, verifikasi config
- [ ] **Network Egress Filtering** — Batasi koneksi keluar dari VM

---

## ✅ Kesimpulan

| Aspek | Hasil |
|-------|-------|
| Kompromi | ❌ Tidak ditemukan |
| Malware | ❌ Tidak ditemukan |
| Backdoor/Persistence | ❌ Tidak ditemukan |
| Data Exfiltration | ❌ Tidak ditemukan |
| Proses Anomali | ❌ Tidak ditemukan |
| Code Injection | ❌ Tidak ditemukan (2 false positive glibc) |
| APT Artifacts (strings) | ❌ Tidak ditemukan |
| Status VM | ✅ Clean — baseline normal |

**VM `Victim PC` dinyatakan AMAN. Insiden ini merupakan false positive atau
latihan forensik pada sistem yang belum dikompromikan.**

---

*Laporan dibuat: 2026-05-15 | Analyst: Security Student | Tools: Volatility 3*
