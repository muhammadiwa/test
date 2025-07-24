# Deployment Guide - TradingBot dengan VPN

## 🚀 Panduan Deployment untuk Mengakses MEXC API dari Indonesia

Bot ini dilengkapi dengan fitur VPN terintegrasi untuk mengatasi pemblokiran MEXC API di Indonesia.

## 📋 Prerequisites

- **Docker Desktop** (Windows/Mac) atau **Docker Engine** (Linux)
- **Docker Compose** (biasanya sudah termasuk dalam Docker Desktop)
- **Akun VPN gratis** untuk server Asia
- **Git** untuk clone repository

## 🛠️ Setup Environment

### 1. Clone Repository

```bash
git clone <repository-url>
cd tradebot
```

### 2. Setup Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit file .env dan isi:
# - MEXC_API_KEY
# - MEXC_API_SECRET  
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHAT_ID
# - VPN_USERNAME (opsional)
# - VPN_PASSWORD (opsional)
```

## 🌐 Setup VPN (Wajib untuk Indonesia)

### Penyedia VPN Gratis yang Direkomendasikan

1. **ProtonVPN Free**
   - Website: [https://protonvpn.com/free-vpn](https://protonvpn.com/free-vpn)
   - Server tersedia: Japan (Tokyo)
   - Bandwidth: Unlimited
   - Registrasi: Email verification required

2. **Windscribe Free**
   - Website: [https://windscribe.com](https://windscribe.com)
   - Server tersedia: Hong Kong, Singapore (dengan promo)
   - Bandwidth: 10GB/bulan (15GB dengan email confirmation)
   - Registrasi: Mudah, bisa dengan email saja

3. **TunnelBear Free**
   - Website: [https://tunnelbear.com](https://tunnelbear.com)
   - Server tersedia: Singapore, Japan
   - Bandwidth: 500MB/bulan (2GB dengan tweet)
   - Registrasi: Email verification required

### Cara Setup VPN

#### Untuk ProtonVPN:
1. Daftar akun gratis di ProtonVPN
2. Login ke dashboard
3. Download -> OpenVPN configuration files
4. Pilih server "Japan Free" atau "Netherlands Free"
5. Download file .ovpn
6. Rename file menjadi `config.ovpn`
7. Pindahkan ke folder `vpn/config.ovpn`

#### Untuk Windscribe:
1. Daftar akun gratis di Windscribe
2. Login ke dashboard
3. Tools -> Config Generator
4. Protocol: OpenVPN
5. Location: Hong Kong atau Singapore
6. Generate config dan download
7. Rename file menjadi `config.ovpn`
8. Pindahkan ke folder `vpn/config.ovpn`

## 🐳 Deployment dengan Docker

### Menggunakan Setup Script (Recommended)

#### Windows (PowerShell):
```powershell
.\setup.ps1
```

#### Linux/Mac (Bash):
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Deployment

```bash
# 1. Build image
docker compose build --no-cache

# 2. Start services
docker compose up -d

# 3. Check logs
docker compose logs -f

# 4. Check status
docker compose ps
```

## 📊 Monitoring dan Debugging

### Cek Status Container
```bash
docker compose ps
```

### Lihat Logs Real-time
```bash
# Semua logs
docker compose logs -f

# Logs spesifik service
docker compose logs -f tradebot
```

### Test Konektivitas VPN
```bash
# Cek apakah VPN aktif
docker compose exec tradebot ip route | grep tun

# Test IP publik setelah VPN
docker compose exec tradebot curl -s https://httpbin.org/ip

# Test akses MEXC API
docker compose exec tradebot curl -s https://api.mexc.com/api/v3/ping
```

### Troubleshooting VPN

#### VPN tidak terkoneksi:
1. Pastikan file `vpn/config.ovpn` ada dan valid
2. Cek username/password VPN di file `.env`
3. Restart container: `docker compose restart`

#### MEXC API masih terblokir:
1. Coba server VPN yang berbeda
2. Pastikan DNS settings benar (8.8.8.8, 1.1.1.1)
3. Cek apakah VPN provider memblokir traffic tertentu

## 🔧 Management Commands

### Start Bot
```bash
docker compose up -d
```

### Stop Bot
```bash
docker compose down
```

### Restart Bot
```bash
docker compose restart
```

### Update Bot (setelah git pull)
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Clean Up (hapus semua container dan image)
```bash
docker compose down --rmi all --volumes
```

## 📱 Dashboard

Jika dashboard diaktifkan, akses melalui:
- URL: http://localhost:9876
- Port dapat diubah di `docker-compose.yml`

## 🔒 Keamanan

1. **File .env**: Jangan commit file ini ke repository
2. **VPN Credentials**: Simpan dengan aman, jangan share
3. **API Keys**: Gunakan API key dengan permission minimal yang dibutuhkan
4. **Firewall**: Pastikan hanya port yang diperlukan yang terbuka

## 📋 Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| MEXC_API_KEY | MEXC API Key | Yes | - |
| MEXC_API_SECRET | MEXC API Secret | Yes | - |
| TELEGRAM_BOT_TOKEN | Telegram Bot Token | Yes | - |
| TELEGRAM_CHAT_ID | Telegram Chat ID | Yes | - |
| VPN_ENABLED | Enable/disable VPN | No | true |
| VPN_USERNAME | VPN Username | No | - |
| VPN_PASSWORD | VPN Password | No | - |
| TZ | Timezone | No | Asia/Jakarta |
| LOG_LEVEL | Logging level | No | INFO |
| DASHBOARD_ENABLED | Enable dashboard | No | true |
| DASHBOARD_PORT | Dashboard port | No | 9876 |

## 🆘 Support

Jika mengalami masalah:

1. Cek logs container: `docker compose logs -f`
2. Cek status VPN: `docker compose exec tradebot ip route`
3. Test konektivitas: `docker compose exec tradebot curl -s https://api.mexc.com/api/v3/ping`
4. Pastikan semua environment variables sudah diset dengan benar

Untuk troubleshooting lebih lanjut, silakan buka issue di repository.
