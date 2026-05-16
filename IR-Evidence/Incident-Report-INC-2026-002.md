# 📋 LAPORAN INSIDEN KEAMANAN
## Case: INC-2026-002 | Targeted Process Forensics — Windows Host

---

**No. Insiden   :** INC-2026-002
**Tanggal       :** 2026-05-15
**Severity      :** HIGH (Data Exfiltration Risk)
**Status        :** ✅ CLOSED — Artifacts Recovered
**Target        :** powershell.exe (PID: Multiple)

---

## 📌 Ringkasan Eksekutif
Analisis memori tertarget dilakukan terhadap proses PowerShell yang mencurigakan. Hasil analisis mengonfirmasi adanya upaya eksfiltrasi data menggunakan token otorisasi yang dicuri. Seluruh artefak ditemukan di dalam memori proses tanpa adanya jejak file berbahaya di disk sistem.

---

## 🔗 Chain of Custody
| Item | Detail |
|------|--------|
| File Evidence | `host_powershell_targeted.dmp` |
| Tool Akuisisi | Sysinternals ProcDump v11.0 |
| Analis | Security Student |

---

## 🔬 Temuan Forensik Detail

### [A] Analisis String Mencurigakan (Memory Carving)
Ditemukan rangkaian string berikut di dalam dump memori:

| Artefak | Nilai |
|---------|-------|
| **C2 Server** | `http://evil-attacker.com/exfil` |
| **Auth Token** | `TG-99-X01-Z9` |
| **Command Line** | `$Global:Secret = '...'` |

### [B] Analisis Vektor Serangan
Serangan ini bersifat **Fileless**. Penyerang menggunakan sesi PowerShell yang sudah ada untuk menyimpan kredensial di dalam variabel global, bertujuan untuk menghindari deteksi oleh antivirus berbasis disk scanning tradisional.

---

## ✅ Kesimpulan
Insiden INC-2026-002 dikonfirmasi sebagai upaya eksfiltrasi data. Token otorisasi berhasil dipulihkan dari RAM. Rekomendasi segera adalah membatalkan (revoke) `AUTH_TOKEN: TG-99-X01-Z9` dan memblokir akses ke domain `evil-attacker.com`.

---
*Laporan dibuat: 2026-05-15 | Analyst: Security Student | Tools: ProcDump, WSL Strings*
