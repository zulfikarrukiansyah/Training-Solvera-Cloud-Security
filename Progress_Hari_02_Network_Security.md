# 🌐 Progress Hari 2 — Arsitektur Keamanan Jaringan (Network Security)
**Tanggal:** ~12 Mei 2026 | **Status:** ✅ SELESAI

---

## 🎯 Tujuan Pembelajaran
- [x] Mendesain arsitektur jaringan yang aman (Defense-in-depth)
- [x] Mengonfigurasi firewall dan aturan akses (iptables)
- [x] Menerapkan pola isolasi jaringan antar layer (Web / App / DB)

---

## 🔬 Lab 2A — Arsitektur Tiga Tingkat (Three-Tier Network)

### Task 1: Setup Jaringan Terisolasi dengan Docker Networks ✅

| Perintah | Jaringan | Tujuan |
|----------|----------|--------|
| `docker network create --driver bridge public-net` | `public-net` | Layer Web — dapat diakses internet |
| `docker network create --driver bridge --internal private-app-net` | `private-app-net` | Layer App — hanya internal |
| `docker network create --driver bridge --internal private-db-net` | `private-db-net` | Layer DB — paling terisolasi |

**Konsep Penting:**
- Flag `--internal` mencegah container terhubung ke internet luar secara langsung.
- Ini adalah implementasi digital dari konsep **DMZ (Demilitarized Zone)** dan **Network Segmentation**.

---

### Task 2: Simulasi Security Groups dengan iptables ✅

Aturan firewall yang diterapkan di WSL2 (simulasi Linux server):

```bash
# Default Deny — Tolak semua koneksi masuk
iptables -P INPUT DROP

# Izinkan loopback (localhost)
iptables -A INPUT -i lo -j ACCEPT

# Izinkan HTTP/HTTPS dari internet ke Web Server
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Izinkan SSH HANYA dari Bastion Host (10.0.0.50)
iptables -A INPUT -p tcp -s 10.0.0.50 --dport 22 -j ACCEPT

# Di Server DB: Izinkan MySQL HANYA dari subnet App (10.0.1.0/24)
iptables -A INPUT -p tcp -s 10.0.1.0/24 --dport 3306 -j ACCEPT
```

**Prinsip yang diterapkan:**
- **Default Deny** — Semua koneksi ditolak kecuali yang diizinkan secara eksplisit.
- **Least Privilege Network** — Setiap layer hanya bisa berkomunikasi dengan layer yang memang perlu.
- **Bastion Host Pattern** — SSH hanya bisa diakses lewat satu titik masuk yang dikontrol.

---

## 📚 Studi Kasus 2: Database Terekspos ke Internet

**Skenario:** Database MySQL startup finansial bocor — **2,1 juta data nasabah** dicuri via SQL Injection karena port 3306 terbuka ke `0.0.0.0/0`.

### Root Cause:
Developer menjalankan container dengan flag `-p 3306:3306` yang memetakan port database langsung ke interface publik.

### Solusi yang Dipelajari:

**1. Isolasi Database — Hapus Port Publik:**
```bash
# Hentikan container yang terekspos
docker stop mysql-db && docker rm mysql-db

# Buat jaringan internal terpisah
docker network create --internal secure-db-net

# Jalankan ulang MySQL TANPA port mapping publik
docker run -d --name secure-mysql \
  --network secure-db-net \
  -e MYSQL_ROOT_PASSWORD=SuperSecret123 \
  mysql:8
```

**2. Setup Gateway — Nginx sebagai Proxy:**
```bash
# Web server terhubung ke dua jaringan (public + internal)
docker run -d --name web-server -p 8080:80 nginx:latest
docker network connect secure-db-net web-server
```
*Hasilnya: MySQL hanya bisa diakses oleh Nginx (via jaringan internal), tidak bisa diakses langsung dari internet.*

**3. Penguncian dengan iptables:**
```bash
iptables -P INPUT DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -p icmp -j ACCEPT
# Hanya izinkan app server spesifik (192.168.1.15) akses ke MySQL
iptables -A INPUT -p tcp -s 192.168.1.15 --dport 3306 -j ACCEPT
iptables-save > /etc/iptables/rules.v4
```

---

## 💡 Key Takeaways

| Konsep | Pelajaran |
|--------|-----------|
| **Network Segmentation** | Pisahkan Web, App, dan DB ke jaringan berbeda. Jangan satu jaringan flat. |
| **Default Deny** | Lebih aman memblokir semua lalu lintas lalu mengizinkan yang diperlukan, bukan sebaliknya. |
| **No Public DB Port** | Database **tidak boleh** punya port mapping ke interface publik (`-p 3306:3306` = bahaya). |
| **Bastion Host** | Satu pintu masuk terkontrol untuk SSH, bukan buka port 22 ke semua IP. |
| **Docker `--internal`** | Flag ini adalah cara mudah membuat jaringan terisolasi tanpa akses internet di Docker. |

---

## ⚠️ Keterbatasan di WSL2

- `iptables -P INPUT DROP` di WSL2 bisa memutus koneksi ke host Windows. Gunakan dengan hati-hati dan pastikan ada rule untuk loopback sebelum menerapkan default DROP.
- Disarankan menjalankan simulasi iptables di dalam container atau VM yang terisolasi.
