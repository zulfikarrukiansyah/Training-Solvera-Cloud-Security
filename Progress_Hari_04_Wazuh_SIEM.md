# 🔍 Progress Hari 4 — Security Monitoring & SIEM (Wazuh)
**Tanggal:** 14 Mei 2026 | **Status:** ✅ SELESAI (Completed with Real Lab)

---

## 🎯 Tujuan Pembelajaran
- [x] Mengonfigurasi log sentral dan audit trail
- [x] Mengatur peringatan real-time menggunakan Wazuh SIEM
- [x] Membangun dashboard Security Operations Center (SOC) lokal
- [x] Mengintegrasikan Wazuh Agent ke server target

---

## 🔬 Lab 4A — Implementasi SIEM & Alerting ✅

### Langkah 1: Instalasi Wazuh Stack (Docker Compose)

```bash
# Clone repo Wazuh Docker
git clone https://github.com/wazuh/wazuh-docker.git -b v4.7.0
cd wazuh-docker/single-node

# Generate sertifikat SSL internal antar komponen
docker-compose -f generate-indexer-certs.yml run --rm generator

# Jalankan full stack (Manager + Indexer + Dashboard)
docker-compose up -d
```

> **Dashboard Wazuh:** `https://localhost` (Login: `admin` / `SecretPassword`)

**Komponen yang berjalan:**
| Container | Fungsi |
|-----------|--------|
| `wazuh.manager` | Menerima log dari semua agent & menjalankan rules |
| `wazuh.indexer` | Database penyimpanan log (Elasticsearch-based) |
| `wazuh.dashboard` | UI visualisasi & monitoring (Kibana-based) |

---

### Langkah 2: Custom Rule — Deteksi SSH Brute Force

File `local_rules.xml` ditambahkan rule kustom (disimpan di folder Learning):

```xml
<!-- Rule dari Learning Plan (Rule ID 100001 - Level 10) -->
<rule id="100001" level="10" frequency="5" timeframe="60">
  <if_matched_sid>5716</if_matched_sid>
  <description>SSH Brute force attack detected (Multiple failed logins)</description>
  <group>authentication_failures,</group>
</rule>

<!-- Rule yang diimplementasikan di lab nyata (Rule ID 100002 - Level 12) -->
<rule id="100002" level="12" frequency="5" timeframe="60">
  <if_matched_sid>5716</if_matched_sid>
  <description>CUSTOM ALERT: Multiple SSH failed logins detected (Possible Brute Force)</description>
  <group>authentication_failures,</group>
</rule>
```

> **Catatan Troubleshooting:** Rule awalnya menggunakan `<if_sid>` yang menyebabkan API error.
> Diperbaiki dengan menggantinya menjadi `<if_matched_sid>` sesuai sintaks yang benar.

---

### Langkah 3: Integrasi Wazuh Agent ✅

| Agent | Target | Status | Fungsi |
|-------|--------|--------|--------|
| **Zul** | Host / WSL Ubuntu | ✅ Aktif | Monitoring host utama |
| **web-server-lab** | Container Docker | ✅ Aktif | SCA (Security Configuration Assessment) |

---

## 🧪 Hasil Simulasi Serangan Brute Force

**Skenario:** Login SSH gagal dilakukan 5–10 kali dalam 1 menit ke target container.

**Script Simulasi:**
```bash
for i in {1..10}; do
  ssh -o StrictHostKeyChecking=no wronguser@<target-ip>
  sleep 1  # Jeda penting agar timestamp log unik
done
```

**Hasil di Dashboard Wazuh:**
- ✅ Alert **Level 12** muncul dengan deskripsi: *"CUSTOM ALERT: Multiple SSH failed logins detected (Possible Brute Force)"*
- ✅ Alert terdaftar di grup `authentication_failures`
- ✅ Alert menunjukkan IP sumber, waktu kejadian, dan jumlah percobaan

> **Insight:** Flag `sleep 1` sangat penting — tanpanya, log memiliki timestamp yang sama sehingga Wazuh tidak menghitung sebagai event berulang dalam timeframe yang berbeda.

---

## 🛠️ Troubleshooting yang Ditemui

| Masalah | Penyebab | Solusi |
|---------|---------|--------|
| API Manager gagal start | Sintaks `<if_sid>` salah di `local_rules.xml` | Ganti ke `<if_matched_sid>` |
| Agent tidak terkoneksi | `ossec.conf` rusak saat diedit di dalam Docker | Restorasi konfigurasi bersih, restart agent |
| Alert tidak muncul | Log SSH tidak unik (timestamp sama) | Tambah `sleep 1` di skrip simulasi |
| Docker `protocol not available` | Docker Desktop daemon tidak jalan | Restart Docker Desktop service di Windows |

---

## 💡 Key Takeaways

| Konsep | Pelajaran |
|--------|-----------|
| **SIEM** | *Security Information and Event Management* — satu platform untuk kumpulkan, korelasikan, dan visualisasikan semua log keamanan. |
| **Rule Hierarchy** | Wazuh menggunakan rule bawaan (`5716` = SSH login failure). Custom rule kita membangun *di atas* rule itu dengan `if_matched_sid`. |
| **Level Alert** | Level 1–4: Low, Level 5–9: Medium, **Level 10–14: High**, Level 15+: Critical |
| **Agent vs Agentless** | Dengan agent terinstal, monitoring lebih dalam (filesystem, proses, SCA). Agentless hanya bisa analisis syslog. |
| **FIM (File Integrity Monitoring)** | Wazuh secara otomatis mendeteksi perubahan file kritis di `/etc`, `/bin`, dll. Ini menggantikan kebutuhan AIDE (yang gagal di audit OpenSCAP Hari 5). |

---

## 📁 File Terkait
| File | Keterangan |
|------|-----------|
| `local_rules.xml` | File custom rule Wazuh (tersimpan di folder Learning) |

---

*Catatan: Lab Hari 4 dijalani dengan kendala Docker yang sempat tidak bisa connect (protocol not available). Diselesaikan dengan restart Docker Desktop service.*
