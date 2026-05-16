# 📑 Progress Hari 08 — Business Continuity & Disaster Recovery (BCDR)
## Lab: PostgreSQL Streaming Replication & Failover Testing

**Tanggal:** 2026-05-15
**Durasi Target:** 6 Jam
**Status:** ✅ SELESAI

---

## 🎯 Checklist Hari Ini
- [x] **Fase 1:** Infrastruktur Docker — 2 kontainer PostgreSQL berjalan ✅
- [x] **Fase 2:** Konfigurasi Streaming Replication (WAL + HBA + pg_basebackup) ✅
- [x] **Fase 3:** Uji Sinkronisasi Data — tabel `secure_logs` tersinkron instan ✅
- [x] **Fase 4:** Simulasi Failover — Standby berhasil dipromosikan jadi Primary ✅
- [x] **Fase 5:** Dokumentasi & Kesimpulan BCDR ✅

---

## 🏗️ Desain Arsitektur

```
[Aplikasi/User]
      |
      | Read/Write
      ↓
[pg_primary] ──── Streaming WAL ────→ [pg_standby]
 Port: 5432                              Port: 5433
 (Read/Write)                        (Read-Only Replica)
      |
      └─────────── Docker Network: bcdr-lab_bcdr-net ──────────┘
```

**Catatan Teknis:**
- Lingkungan: WSL Ubuntu (native ext4) — menghindari isu permission NTFS Windows
- Image: `postgres:15-alpine`
- Volume: Bind mount ke `~/bcdr-lab/pg_primary_data` dan `~/bcdr-lab/pg_standby_data`

---

## 🔬 FASE 1 — Persiapan Infrastruktur Docker

### Step 1 — Membuat Direktori Lab di WSL
```bash
# Buat folder utama lab dan subfolder data untuk masing-masing node
mkdir -p ~/bcdr-lab/pg_primary_data ~/bcdr-lab/pg_standby_data
cd ~/bcdr-lab
```

### Step 2 — Membuat Docker Network
```bash
# Network ini digunakan agar Primary dan Standby bisa saling berkomunikasi
docker network create bcdr-net
```

### Step 3 — Membuat File docker-compose.yml (via HEREDOC di WSL)
```bash
cat <<EOF > docker-compose.yml
version: '3.8'

services:
  pg_primary:
    image: postgres:15-alpine
    container_name: pg_primary
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: masterpassword
      POSTGRES_DB: secure_db
    ports:
      - "5432:5432"
    networks:
      - bcdr-net
    volumes:
      - ./pg_primary_data:/var/lib/postgresql/data
    command: ["postgres", "-c", "wal_level=replica", "-c", "max_wal_senders=10", "-c", "max_replication_slots=10", "-c", "hot_standby=on"]

  pg_standby:
    image: postgres:15-alpine
    container_name: pg_standby
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: masterpassword
      POSTGRES_DB: secure_db
    ports:
      - "5433:5432"
    networks:
      - bcdr-net
    depends_on:
      - pg_primary
    volumes:
      - ./pg_standby_data:/var/lib/postgresql/data

networks:
  bcdr-net:
    driver: bridge
EOF
```

### Step 4 — Menjalankan Kontainer
```bash
# Jalankan kedua kontainer di background
docker-compose up -d

# Verifikasi status kontainer (keduanya harus berstatus Up)
docker ps
```

**✅ Hasil yang diharapkan:**
```
CONTAINER ID   IMAGE                PORTS                    STATUS
xxxxxxxxxxxx   postgres:15-alpine   0.0.0.0:5432->5432/tcp   Up
xxxxxxxxxxxx   postgres:15-alpine   0.0.0.0:5433->5432/tcp   Up
```

### Isu yang Dihadapi & Solusi:
| Isu | Penyebab | Solusi |
|-----|----------|--------|
| `Operation not permitted` (chmod) | Bind mount ke drive Windows (NTFS) tidak support Linux permissions | Pindah seluruh lab ke WSL filesystem (`~/bcdr-lab/`) |
| `no configuration file provided` | `docker-compose` dijalankan di direktori yang salah | Pastikan berada di direktori yang sama dengan `docker-compose.yml` |
| `docker logs` menunjukkan `initdb: error` | Folder data dari volume tidak bisa di-chmod oleh PostgreSQL | Gunakan `~/bcdr-lab/` bukan `/mnt/d/...` |

**✅ Hasil:** Kedua kontainer berstatus `Up` setelah dipindah ke ekosistem WSL.

---

## 🔬 FASE 2 — Konfigurasi Streaming Replication

### Step 1 — Membuat User Replikasi
```sql
CREATE USER repuser REPLICATION LOGIN CONNECTION LIMIT 10
  ENCRYPTED PASSWORD 'replication_password';
```
> **Prinsip Keamanan:** Menggunakan user terpisah dengan hak akses terbatas (Least Privilege), bukan superuser `postgres`.

### Step 2 — Membuat Replication Slot
```sql
SELECT * FROM pg_create_physical_replication_slot('standby_slot');
```
> **Fungsi:** Memastikan Primary menyimpan WAL log sampai Standby sudah menerimanya — mencegah data gap.

### Step 3 — Konfigurasi pg_hba.conf
```bash
echo 'host replication repuser 0.0.0.0/0 scram-sha-256' >> /var/lib/postgresql/data/pg_hba.conf
SELECT pg_reload_conf();
```
> **Isu yang Dihadapi:** Error `no pg_hba.conf entry for replication connection` — PostgreSQL memblokir koneksi replikasi yang tidak terdaftar secara eksplisit.

### Step 4 — Clone Data (pg_basebackup)
```bash
docker run --rm -it \
  --network bcdr-lab_bcdr-net \
  -v ~/bcdr-lab/pg_standby_data:/var/lib/postgresql/data \
  postgres:15-alpine \
  pg_basebackup -h $PRIMARY_IP -D /var/lib/postgresql/data -U repuser -v -P -X stream -R
```

**Isu yang Dihadapi & Solusi:**
| Isu | Solusi |
|-----|--------|
| `Name does not resolve` (pg_primary) | Gunakan IP langsung: `docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' pg_primary` |
| `directory is not empty` | Hapus folder dan buat ulang: `rm -rf pg_standby_data && mkdir pg_standby_data` |

**✅ Hasil `pg_basebackup`:**
```
pg_basebackup: checkpoint completed
pg_basebackup: write-ahead log start point: 0/2000028 on timeline 1
pg_basebackup: base backup completed
```

---

## 🔬 FASE 3 — Verifikasi & Uji Sinkronisasi Data

### Verifikasi Replikasi Aktif (Sisi Primary)
```sql
SELECT usename, application_name, client_addr, state, sync_state
FROM pg_stat_replication;
-- state = 'streaming' → Replikasi aktif ✅
```

### Uji Tulis di Primary, Baca di Standby
```sql
-- Di Primary:
CREATE TABLE secure_logs (id serial PRIMARY KEY, event text,
  severity text, log_time timestamp DEFAULT now());
INSERT INTO secure_logs (event, severity)
  VALUES ('Inisialisasi Replikasi Berhasil', 'INFO'),
         ('Percobaan Akses Tidak Sah Terdeteksi', 'WARNING');

-- Di Standby (Port 5433):
SELECT * FROM secure_logs;
```

**✅ Hasil:** Data muncul secara instan di Standby tanpa delay yang terdeteksi.

---

## 🔬 FASE 4 — Simulasi Failover (Disaster Recovery)

### Skenario: Primary Server Mati Total
```bash
docker stop pg_primary
```

### Konfirmasi Standby Masih Read-Only
```sql
-- Hasil error yang diharapkan:
INSERT INTO secure_logs ... → ERROR: cannot execute INSERT in a read-only transaction
```

### Promosi Standby → Primary Baru
```bash
# Harus dijalankan sebagai user postgres (bukan root)
docker exec -u postgres -it pg_standby pg_ctl promote -D /var/lib/postgresql/data
```

> **Isu yang Dihadapi:** `pg_ctl: cannot be run as root` — PostgreSQL melarang perintah admin dari root.
> **Solusi:** Tambahkan flag `-u postgres` pada perintah `docker exec`.

### Verifikasi Kemampuan Tulis Pasca-Failover
```sql
INSERT INTO secure_logs (event, severity)
  VALUES ('Failover Berhasil - Standby menjadi Primary', 'SUCCESS');
-- Berhasil! ✅
```

### Hasil Failover
| Tahapan | Status | Keterangan |
|---------|--------|------------|
| Shutdown Primary | ✅ Berhasil | `docker stop pg_primary` |
| Standby Read-Only Check | ✅ Berhasil | Menolak `INSERT` saat masih mode Slave |
| Promosi Standby | ✅ Berhasil | `pg_ctl promote` sebagai user `postgres` |
| Write ke Primary Baru | ✅ Berhasil | Data berhasil di-insert ke Standby yang dipromosikan |
| RTO (Recovery Time) | ✅ < 1 Menit | Dari Primary mati hingga Standby siap Write |

---

## 🧠 Konsep Kunci yang Dipelajari

| Konsep | Penjelasan |
|--------|------------|
| WAL (Write-Ahead Log) | Log transaksi yang dikirim Primary ke Standby untuk replikasi |
| Hot Standby | Standby bisa melayani query Read-Only sambil tetap menerima data replikasi |
| Replication Slot | Mekanisme agar Primary tidak hapus WAL sebelum Standby menerimanya |
| pg_basebackup | Tool untuk kloning base image database dari Primary ke Standby |
| RTO (Recovery Time Objective) | Waktu yang dibutuhkan untuk memulihkan layanan setelah insiden |
| RPO (Recovery Point Objective) | Toleransi kehilangan data — dengan streaming replication, mendekati 0 |
| Failover | Proses pengambilalihan peran Primary oleh Standby saat Primary gagal |
| Least Privilege | User `repuser` hanya punya hak replikasi, bukan superuser |

---

## 📋 Rekomendasi Peningkatan (Production)
- [ ] Implementasi **Patroni** atau **Repmgr** untuk auto-failover (tanpa intervensi manual)
- [ ] Konfigurasi **synchronous_commit = on** untuk zero data loss (RPO = 0)
- [ ] Setup **pgBouncer** sebagai connection pooler di depan Primary
- [ ] Monitoring dengan **pg_activity** atau integrasi Wazuh untuk alert replikasi
- [ ] Automasi backup regular dengan **pgBackRest**

---

## 📊 Metrik Lab
| Metric | Nilai |
|--------|-------|
| Ukuran Data di-clone | ~30 MB |
| Waktu pg_basebackup | < 30 detik |
| Waktu Failover (RTO) | < 1 menit |
| Data Loss (RPO) | 0 (semua data tersinkron) |
| Kontainer | 2 (pg_primary, pg_standby) |

---

**🎯 KESIMPULAN: Sistem High Availability PostgreSQL berhasil divalidasi secara end-to-end. Streaming Replication aktif, data tersinkron instan, dan mekanisme Failover manual berhasil memulihkan kemampuan Write dalam waktu < 1 menit.**

---
*Progress Hari 8 | Open Source Security Lab | 2026-05-15 | Selesai 12:16 WIB*
