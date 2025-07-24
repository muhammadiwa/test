# Sniper Bot - Ultra-Fast Token Listing Bot

## 🧠 **Tujuan Utama**
Mengembangkan bot sniper ultra-cepat yang secara otomatis mendeteksi listing token baru di MEXC, lalu mengeksekusi pembelian di harga paling bawah dan menjual sesuai target profit \\— dengan toleransi waktu super rendah (1ms – 50ms).

## 🌐 **Akses MEXC API dari Indonesia**
Bot ini dilengkapi dengan fitur VPN terintegrasi untuk mengakses MEXC API yang diblokir di Indonesia. Bot akan otomatis terkoneksi ke server Asia melalui VPN gratis.

---

## 📦 **Deskripsi Singkat Aplikasi**
Sniper Bot adalah aplikasi terotomatisasi yang terhubung ke MEXC (melalui API WebSocket/REST atau integrasi tidak resmi bila perlu), yang mendeteksi event listing token baru dan melakukan:

- Spam transaksi beli segera setelah market pair aktif atau dari 30 detik sebelum aktif supaya tidak tertinggal.
- Mengatur take profit dan/atau trailing stop.
- Opsi auto-sell saat harga turun drastis (stop loss).

---

## 🚀 **Quick Start dengan Docker**

### **Prerequisites**
- Docker Desktop (Windows/Mac) atau Docker Engine (Linux)
- File konfigurasi VPN (.ovpn) dari penyedia VPN gratis

### **1. Setup Cepat (Windows)**
```powershell
# Clone repository
git clone <repository-url>
cd tradebot

# Jalankan setup script
.\setup.ps1

# Atau manual:
# 1. Copy dan edit konfigurasi
copy .env.example .env
notepad .env

# 2. Build dan jalankan
docker compose up -d
```

### **2. Setup Cepat (Linux/Mac)**
```bash
# Clone repository
git clone <repository-url>
cd tradebot

# Jalankan setup script
chmod +x setup.sh
./setup.sh

# Atau manual:
# 1. Copy dan edit konfigurasi
cp .env.example .env
nano .env

# 2. Build dan jalankan
docker compose up -d
```

### **3. Setup VPN (Wajib untuk Indonesia)**
1. Daftar akun VPN gratis:
   - **ProtonVPN Free**: https://protonvpn.com/free-vpn
   - **Windscribe Free**: https://windscribe.com
   - **TunnelBear Free**: https://tunnelbear.com

2. Download konfigurasi OpenVPN (.ovpn) untuk server Asia (Singapore, Hong Kong, Japan)

3. Simpan file sebagai `vpn/config.ovpn`

4. Isi username/password VPN di file `.env`:
   ```
   VPN_USERNAME=your_vpn_username
   VPN_PASSWORD=your_vpn_password
   ```

### **4. Monitoring**
```bash
# Lihat logs
docker compose logs -f

# Cek status
docker compose ps

# Cek konektivitas MEXC API
docker compose exec tradebot curl -s https://api.mexc.com/api/v3/ping

# Dashboard (jika diaktifkan)
# http://localhost:9876
```

---

## 🔧 **Fitur Utama (Modular)**

### 1. **Buy Order Engine (Sniper Engine)**
- Spam buy order sebelum dan saat token listing aktif (jika belum ada harga maka lihat dari orderbook sell yang aktif dan ketebalannya untuk patokan harga belinya).
- Adjustable frequency: 1ms – 100ms.
- Multi-threading / async untuk efisiensi.
- Retry logic & fallback.

### 2. **Order Executor & Manager**
- Full kontrol order: Market.
- Auto-retry order gagal sampai filled.

### 3. **Sell Strategy Manager**
- **Take Profit (TP)** dengan % target (contoh: +50%) - dapat dikonfigurasi untuk jual sebagian atau seluruh posisi
- **Stop Loss (SL)** dengan % batas bawah (contoh: -10%).
- **Trailing Stop Loss (TSL)** - aktif setelah harga naik minimum X% dan jual otomatis saat harga turun Y% dari tertinggi
- **Strategi Hybrid TP+TSL** - jual sebagian di TP dan sisanya dikelola dengan TSL untuk maksimalisasi profit
- **Time-based selling** (sell after X minutes).

### 4. **Logging & Monitoring Dashboard**
- Menampilkan performa per token (Buy price, Sell price, P&L).
- Auto-notify via Telegram.
- Semua pengaturan bisa di setting di bot telegram dan start bot-nya dari Telegram.

---

## 🛠️ **Teknologi yang Direkomendasikan**

### **Bahasa Pemrograman**
- Python (karena ekosistemnya yang kaya untuk API, async, dan multi-threading).

### **Library Utama**
- **WebSocket**: `websockets` atau `websocket-client`.
- **HTTP Client**: `httpx` (untuk performa async).
- **Multi-threading/Async**: `asyncio`, `concurrent.futures`.
- **Telegram Bot**: `python-telegram-bot`.
- **Logging**: `loguru`.

### **Database**
- SQLite atau Redis (untuk menyimpan konfigurasi dan log transaksi).

---

## 📂 **Struktur Proyek**
```
tradebot/
├── core/                # Logika inti (Sniper Engine, Order Executor, Sell Strategy Manager)
├── api/                 # Integrasi API MEXC (WebSocket/REST)
├── utils/               # Fungsi pendukung (logging, konfigurasi, retry logic)
├── dashboard/           # Monitoring dan logging (web/CLI)
├── telegram/            # Modul untuk integrasi Telegram bot
├── main.py              # Entry point aplikasi
└── requirements.txt     # Dependensi proyek
```

---

## 🚀 **Langkah Awal Pengembangan**

### **1. Setup Proyek**
1. Buat struktur direktori seperti di atas.
2. Tambahkan file `requirements.txt` untuk dependensi:
   ```plaintext
   websockets
   httpx
   python-telegram-bot
   loguru
   asyncio
   ```

### **2. Modul Sniper Engine**
- **Fungsi Utama**:
  - Spam buy untuk pairs yang dari hasil input contoh PUMPUSDT maka akan spam buy pair ini dengan nominal berapa usdt yang akan di tradingkan.
  - Spam buy order dengan adjustable frequency.
  - Retry logic untuk order yang gagal.

### **3. Modul Order Executor**
- **Fungsi Utama**:
  - Eksekusi order (market order).
  - Auto-retry hingga order terisi penuh.

### **4. Modul Sell Strategy Manager**
- **Fungsi Utama**:
  - **Take Profit (TP)**: Jual sebagian atau seluruh posisi saat target profit tercapai
  - **Stop Loss (SL)**: Jual saat harga turun ke level tertentu untuk membatasi kerugian
  - **Trailing Stop Loss (TSL)**: Aktif setelah kenaikan minimum, menjual saat harga turun dari tertinggi
  - **Strategi Hybrid TP+TSL**: Kombinasi jual sebagian di TP, sisanya dengan TSL untuk maksimalisasi profit
  - **Time-based selling**: Jual otomatis setelah X menit

### **5. Logging & Monitoring**
- **Fungsi Utama**:
  - Menampilkan performa transaksi.
  - Mengirim notifikasi ke Telegram.

---

## � **Docker Deployment**

Bot ini bisa dijalankan menggunakan Docker untuk lingkungan yang konsisten dan terisolasi. Ikuti langkah-langkah di [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) untuk detail lengkapnya.

Ringkasan deployment dengan Docker:

1. **Siapkan konfigurasi**:
   ```bash
   cp .env.example .env
   # Edit file .env dengan API key dan konfigurasi Anda
   ```

2. **Build dan jalankan container**:
   ```bash
   docker-compose up -d
   ```

3. **Cek logs**:
   ```bash
   docker-compose logs -f
   ```

4. **Menghentikan bot**:
   ```bash
   docker-compose down
   ```

## �📈 **Langkah Selanjutnya**
1. **Implementasi Modul API MEXC**:
   - Buat koneksi WebSocket untuk mendeteksi listing token baru.
   - Implementasikan REST API untuk eksekusi order.
2. **Pengembangan Sniper Engine**:
   - Buat loop async untuk spam buy order.
   - Tambahkan retry logic.
3. **Integrasi Telegram Bot**:
   - Buat command untuk memulai/menyetel bot.
   - Kirim notifikasi transaksi ke Telegram.
4. **Testing & Optimasi**:
   - Uji performa bot dengan simulasi listing token.
   - Optimalkan latensi (target 1ms – 50ms).
