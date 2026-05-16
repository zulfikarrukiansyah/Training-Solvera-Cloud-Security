# 🔐 Progress Hari 3 — Keamanan Data & Enkripsi (MinIO & Vault)
**Tanggal:** ~12–13 Mei 2026 | **Status:** ✅ SELESAI

---

## 🎯 Tujuan Pembelajaran
- [x] Mengimplementasikan enkripsi saat diam (at-rest) dan berpindah (in-transit)
- [x] Mengonfigurasi HashiCorp Vault sebagai Key Management System (KMS)
- [x] Mengamankan object storage lokal dengan MinIO (Object Lock & Versioning)

---

## 📖 Teori — Konsep Enkripsi Data

| Jenis Enkripsi | Penjelasan | Tool |
|----------------|-----------|------|
| **At-Rest** | Data dienkripsi saat tersimpan di disk | MinIO + Vault KMS |
| **In-Transit** | Data dienkripsi saat dikirim melalui jaringan | TLS/HTTPS |
| **WORM** | *Write Once Read Many* — data tidak bisa diubah/dihapus setelah ditulis | MinIO Object Lock |

---

## 🔬 Lab 3A — Implementasi MinIO & HashiCorp Vault ✅

### Langkah 1: Setup MinIO (4-Volume Cluster)

Catatan dari Master file: **MinIO membutuhkan 4 volume** agar fitur Object Lock dapat aktif di Windows/Docker Desktop.

```bash
# Buat 4 volume virtual
docker volume create d1
docker volume create d2
docker volume create d3
docker volume create d4

# Jalankan MinIO dengan 4 volume (port 8010 = API, 8011 = Dashboard)
docker run -d --name minio \
  -p 8010:9000 -p 8011:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=password123" \
  -v d1:/data1 -v d2:/data2 -v d3:/data3 -v d4:/data4 \
  --entrypoint sh minio/minio \
  -c "mkdir -p /data1 /data2 /data3 /data4 && minio server /data1 /data2 /data3 /data4 --console-address :9001"
```
> **Dashboard MinIO:** `http://localhost:8011` (Login: `admin` / `password123`)

---

### Langkah 2: Setup HashiCorp Vault (KMS)

```bash
# Jalankan Vault dalam mode development
docker run -d --name vault \
  --cap-add=IPC_LOCK \
  -e "VAULT_DEV_ROOT_TOKEN_ID=myroot" \
  -p 8200:8200 \
  hashicorp/vault
```
> **Dashboard Vault:** `http://localhost:8200` (Login pakai token: `myroot`)

**Konfigurasi Transit Secret Engine untuk KMS MinIO:**
```bash
# Masuk ke container Vault
docker exec -it vault sh

# Di dalam container:
vault secrets enable transit
vault write -f transit/keys/minio-key
exit
```
*Transit engine ini berfungsi sebagai "KMS lokal" — setiap file yang disimpan di MinIO akan dienkripsi menggunakan kunci yang dikelola Vault.*

---

### Langkah 3: Konfigurasi Object Lock & Versioning

```bash
# Set alias MinIO Client (mc)
docker exec minio mc alias set myminio http://localhost:9000 admin password123

# Buat bucket dengan Object Lock aktif (WORM)
docker exec minio mc mb --with-lock myminio/medical-records

# Aktifkan versioning
docker exec minio mc version enable myminio/medical-records

# Set retention: data TIDAK BISA dihapus bahkan oleh admin selama 365 hari
docker exec minio mc retention set --default compliance 365d myminio/medical-records
```

---

## 📚 Studi Kasus 3: Serangan Ransomware pada Storage

**Skenario:** Data medis **2TB** dihapus permanen oleh ransomware karena tidak ada perlindungan storage.
Rumah sakit diminta membayar tebusan. Data tidak bisa dipulihkan.

### Simulasi Serangan & Pemulihan ✅

```bash
# 1. Simpan file asli ke MinIO
echo "Data Medis Rahasia Pasien A" > pasien.txt
docker exec minio mc cp pasien.txt myminio/medical-records/

# 2. Ransomware menyerang — file di-overwrite
echo "ENCRYPTED BY RANSOMWARE - PAY NOW" > pasien.txt
docker exec minio mc cp pasien.txt myminio/medical-records/

# 3. Versioning menyimpan riwayat! Lihat semua versi file:
docker exec minio mc ls --versions myminio/medical-records/pasien.txt

# 4. Pulihkan file versi asli (gunakan VERSION_ID dari output step 3)
docker exec minio mc cp --vid <VERSION_ID_ASLI> \
  myminio/medical-records/pasien.txt recovered_pasien.txt

cat recovered_pasien.txt
# Output: Data Medis Rahasia Pasien A ✅
```

**Kesimpulan:** Dengan **Versioning + Object Lock (WORM)**, ransomware **tidak bisa menghapus permanen** — karena versi sebelumnya selalu tersimpan dan terlindungi oleh retention policy.

---

## 💡 Key Takeaways

| Konsep | Pelajaran |
|--------|-----------|
| **Object Lock (WORM)** | Data yang sudah ditulis tidak bisa diubah atau dihapus hingga masa retensi habis — bahkan oleh admin. |
| **Versioning** | Setiap perubahan file membuat versi baru. File lama tidak pernah hilang, sehingga bisa di-*revert*. |
| **Vault sebagai KMS** | Kunci enkripsi dikelola secara terpusat dan terpisah dari data — standar industri keamanan enterprise. |
| **Compliance Mode** | Mode paling ketat di MinIO. Tidak ada yang bisa override retention, berbeda dari mode Governance. |
| **4-Volume MinIO** | Di Windows/Docker Desktop, MinIO membutuhkan minimal 4 volume agar mode distributed (dengan fitur Lock) dapat aktif. |
| **Separation of Concern** | Data (MinIO) dan kunci enkripsinya (Vault) disimpan terpisah. Jika satu dibobol, yang lain tetap aman. |

---

## 📁 Layanan yang Berjalan Setelah Lab Ini

| Container | Port | URL | Fungsi |
|-----------|------|-----|--------|
| `minio` | 8010 (API), 8011 (Dashboard) | `http://localhost:8011` | Object Storage |
| `vault` | 8200 | `http://localhost:8200` | Key Management System |
