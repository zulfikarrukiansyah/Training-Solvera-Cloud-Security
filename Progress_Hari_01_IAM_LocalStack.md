# 🔑 Progress Hari 1 — Dasar Cloud Security & IAM (LocalStack)
**Tanggal:** ~12 Mei 2026 | **Status:** ✅ SELESAI

---

## 🎯 Tujuan Pembelajaran
- [x] Memahami Model Tanggung Jawab Bersama (Shared Responsibility Model)
- [x] Menguasai arsitektur Identity and Access Management (IAM)
- [x] Mengonfigurasi kredensial akses dengan prinsip Least-Privilege

---

## 📖 Teori — Konsep IAM

### Komponen IAM
| Komponen | Fungsi |
|----------|--------|
| **User** | Identitas individu (developer, admin, dll) |
| **Group** | Kumpulan user dengan hak akses serupa |
| **Role** | Identitas sementara yang bisa "dipakai" oleh service/user |
| **Policy** | Dokumen JSON yang mendefinisikan apa yang boleh/tidak boleh dilakukan |

### Aturan Emas Evaluasi IAM
> **Explicit Deny selalu mengesampingkan Allow.**
> Artinya: Jika ada satu rule `Deny` yang cocok, akses DITOLAK meskipun ada `Allow` lain.

---

## 🔬 Lab 1A — Konfigurasi IAM via LocalStack ✅

### Langkah 1: Setup LocalStack & Buat Admin User

```bash
# Jalankan LocalStack (simulasi AWS lokal)
docker run -d --name localstack \
  -p 4566:4566 -p 4510-4559:4510-4559 \
  localstack/localstack:3.8

# Buat user admin
docker exec localstack awslocal iam create-user --user-name security-admin

# Set password (simulasi login profile)
docker exec localstack awslocal iam create-login-profile \
  --user-name security-admin \
  --password "Str0ng!P@ss2024" \
  --password-reset-required
```

> **Catatan Penting:** Perintah `awslocal` lebih stabil dijalankan via `docker exec localstack awslocal ...`
> daripada langsung dari host (terutama di WSL2).

---

### Langkah 2: Buat & Terapkan Least-Privilege Policy

Policy ini mengizinkan user hanya membaca info EC2 dan CloudWatch, dan **melarang SEMUA operasi IAM**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:DescribeInstances", "cloudwatch:GetMetricData"],
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
# Terapkan policy ke LocalStack
docker exec localstack awslocal iam create-policy \
  --policy-name ReadOnly-EC2-Internal \
  --policy-document file://policy.json
```

---

## 📚 Studi Kasus 1: Kebocoran Kredensial E-Commerce

**Skenario:** Developer tidak sengaja meng-*push* AWS Access Key ke GitHub publik.
Penyerang langsung menggunakannya untuk menyewa 50 GPU Instance. **Tagihan membengkak $47,000 dalam semalam.**

---

### Solusi yang Dipelajari:

**1. Deteksi Secret yang Bocor (TruffleHog)**

Sebelum push ke Git, scan dulu repositori untuk mencari kredensial yang tersimpan:
```bash
docker pull trufflesecurity/trufflehog:latest
docker run --rm -v "$PWD:/proj" trufflesecurity/trufflehog:latest filesystem /proj
```

**2. Rotasi Kunci Akses (Incident Response)**

Langkah pertama saat tahu kunci bocor — **nonaktifkan segera**:
```bash
# Cek key mana yang bocor
docker exec localstack awslocal iam list-access-keys --user-name security-admin

# Nonaktifkan & hapus kunci lama
docker exec localstack awslocal iam update-access-key \
  --access-key-id <ID_BOCOR> --status Inactive --user-name security-admin
docker exec localstack awslocal iam delete-access-key \
  --access-key-id <ID_BOCOR> --user-name security-admin

# Buat kunci baru
docker exec localstack awslocal iam create-access-key --user-name security-admin
```

**3. IP Whitelisting Policy — Batasi dari Mana Kunci Bisa Digunakan** ✅

File `strict-ip-policy.json` sudah dibuat dan ada di folder Learning:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "NotIpAddress": {
        "aws:SourceIp": ["203.0.113.50/32", "127.0.0.1/32"]
      }
    }
  }]
}
```
*Efeknya: Meskipun Access Key bocor, penyerang dari IP asing tidak bisa menggunakannya.*

```bash
# Terapkan ke LocalStack
docker exec localstack awslocal iam create-policy \
  --policy-name RequireCorpIP \
  --policy-document file:///policy.json

docker exec localstack awslocal iam attach-user-policy \
  --user-name security-admin \
  --policy-arn arn:aws:iam::000000000000:policy/RequireCorpIP
```

---

## 💡 Key Takeaways

| Konsep | Pelajaran |
|--------|-----------|
| **Least Privilege** | User hanya boleh punya izin minimum yang dibutuhkan — tidak lebih. |
| **Explicit Deny** | `Deny` selalu menang atas `Allow`. Gunakan ini untuk blokir aksi berbahaya secara mutlak. |
| **IP Whitelisting** | Batasi penggunaan Access Key hanya dari IP terpercaya (VPN kantor, IP statis). |
| **Secret Scanning** | Wajib scan repo sebelum push ke Git. Gunakan TruffleHog atau Trivy. |
| **Segera Rotasi** | Saat kunci bocor, langkah pertama adalah **nonaktifkan** — baru investigasi. Jangan tunggu. |
| **LocalStack** | Simulasi AWS IAM lokal yang aman tanpa risiko tagihan cloud nyata. |

---

## 📁 File Dihasilkan
| File | Keterangan |
|------|-----------|
| `strict-ip-policy.json` | Policy JSON pembatas IP untuk IAM (tersimpan di folder Learning) |
