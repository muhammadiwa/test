# MEXC Trading Bot

## Strategi Pembelian Token Baru

Bot ini dirancang untuk dapat menangani pembelian token baru yang baru saja listing atau belum memiliki data harga yang cukup. Berikut adalah strategi yang diimplementasikan:

### 1. Mekanisme Retry Otomatis

Ketika token baru di-listing, sering kali data harga tidak langsung tersedia. Bot ini akan mencoba beberapa kali jika terjadi error seperti:
- "float division by zero" (ketika tidak ada data harga ticker)
- "Invalid symbol" (ketika token belum sepenuhnya tersedia)

### 2. Analisis Order Book

Untuk token yang baru listing, bot menggunakan order book untuk:
- Mengevaluasi likuiditas yang tersedia
- Menghitung harga rata-rata eksekusi
- Menentukan kuantitas token yang dapat dibeli

### 3. Batasan Minimum Order

Bot secara otomatis mengatur jumlah pembelian minimum:
- Order minimum untuk MEXC adalah 1 USDT
- Jika order di bawah minimum, jumlahnya akan disesuaikan otomatis

### 4. Penanganan Error

Bot ini memiliki mekanisme untuk menangani berbagai error yang mungkin terjadi:
- Mencoba kembali jika terjadi error jaringan
- Mencoba kembali dengan pendekatan berbeda jika order ditolak
- Logging semua error untuk analisis

## Cara Menggunakan Bot untuk Token Baru

Untuk melakukan pembelian token baru yang baru saja listing:

1. Gunakan perintah `/buy [symbol] [amount]` di bot Telegram
   Contoh: `/buy NEWTOKEN 5`

2. Bot akan otomatis menangani:
   - Pengecekan apakah token sudah tersedia
   - Retry jika token belum fully listed
   - Penyesuaian jumlah order jika diperlukan

## Parameter Konfigurasi

Beberapa parameter yang dapat dikonfigurasi:
- `MAX_RETRY_ATTEMPTS`: Jumlah percobaan ulang maksimum (default: 5)
- `MIN_ORDER_USDT`: Jumlah minimum order dalam USDT (default: 1.0)
- `RETRY_DELAY`: Waktu tunggu antara percobaan ulang (default: 2 detik)

## Debugging dan Pemecahan Masalah

Jika Anda mengalami masalah dengan pembelian token baru:

1. Periksa log untuk pesan error spesifik
2. Pastikan token sudah benar-benar tersedia di MEXC
3. Cobalah meningkatkan `MAX_RETRY_ATTEMPTS` untuk token yang baru listing
4. Pastikan jumlah order memenuhi batasan minimum MEXC
