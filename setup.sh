#!/bin/bash

# Setup script untuk TradingBot dengan VPN
# Script ini akan membantu setup environment dan deployment

set -e

echo "=== TradingBot Setup dengan VPN untuk MEXC API ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is installed
check_docker() {
    print_info "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker tidak ditemukan! Silakan install Docker terlebih dahulu."
        echo "Download dari: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose tidak ditemukan! Silakan install Docker Compose."
        exit 1
    fi
    
    print_success "Docker dan Docker Compose terdeteksi!"
}

# Function to setup environment file
setup_env() {
    print_info "Setting up environment file..."
    
    if [ ! -f ".env" ]; then
        print_info "Membuat file .env dari template..."
        cp .env.example .env
        print_warning "File .env telah dibuat. Silakan edit file .env dan isi dengan kredensial Anda:"
        echo "  - MEXC_API_KEY"
        echo "  - MEXC_API_SECRET"
        echo "  - TELEGRAM_BOT_TOKEN"
        echo "  - TELEGRAM_CHAT_ID"
        echo "  - VPN_USERNAME (opsional)"
        echo "  - VPN_PASSWORD (opsional)"
        read -p "Tekan Enter setelah Anda mengisi file .env..."
    else
        print_success "File .env sudah ada!"
    fi
}

# Function to setup VPN
setup_vpn() {
    print_info "Setting up VPN configuration..."
    
    if [ ! -f "vpn/config.ovpn" ]; then
        print_warning "File konfigurasi VPN tidak ditemukan!"
        echo ""
        echo "Untuk menggunakan VPN, Anda perlu:"
        echo "1. Mendaftar di penyedia VPN gratis seperti:"
        echo "   - ProtonVPN Free: https://protonvpn.com/free-vpn"
        echo "   - Windscribe Free: https://windscribe.com"
        echo "   - TunnelBear Free: https://tunnelbear.com"
        echo ""
        echo "2. Download file konfigurasi OpenVPN (.ovpn) untuk server Asia"
        echo "   (Singapore, Hong Kong, Japan, dll)"
        echo ""
        echo "3. Simpan file tersebut sebagai 'vpn/config.ovpn'"
        echo ""
        
        read -p "Apakah Anda ingin melanjutkan tanpa VPN? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Melanjutkan tanpa VPN. MEXC API mungkin tidak dapat diakses dari Indonesia."
            # Disable VPN in .env
            sed -i 's/VPN_ENABLED=true/VPN_ENABLED=false/' .env 2>/dev/null || true
        else
            print_error "Setup dibatalkan. Silakan setup VPN terlebih dahulu."
            exit 1
        fi
    else
        print_success "File konfigurasi VPN ditemukan!"
    fi
}

# Function to build and run the container
deploy() {
    print_info "Building dan deploying TradingBot..."
    
    # Stop existing container if running
    print_info "Stopping existing containers..."
    docker-compose down || true
    
    # Build new image
    print_info "Building Docker image..."
    docker-compose build --no-cache
    
    # Start the services
    print_info "Starting TradingBot with VPN..."
    docker-compose up -d
    
    print_success "TradingBot telah di-deploy!"
    echo ""
    echo "Untuk memonitor logs:"
    echo "  docker-compose logs -f"
    echo ""
    echo "Untuk menghentikan bot:"
    echo "  docker-compose down"
    echo ""
    echo "Dashboard (jika diaktifkan): http://localhost:9876"
}

# Function to show logs
show_logs() {
    print_info "Showing container logs..."
    docker-compose logs -f
}

# Function to check status
check_status() {
    print_info "Checking container status..."
    docker-compose ps
    
    echo ""
    print_info "Checking VPN status..."
    docker-compose exec tradebot ip route | grep tun || echo "VPN tidak aktif atau tidak dikonfigurasi"
    
    echo ""
    print_info "Testing MEXC API connectivity..."
    docker-compose exec tradebot curl -s --max-time 10 https://api.mexc.com/api/v3/ping && echo " - MEXC API: Accessible ✅" || echo " - MEXC API: Not accessible ❌"
}

# Main menu
show_menu() {
    echo ""
    echo "=== TradingBot Management ==="
    echo "1. Setup Environment"
    echo "2. Setup VPN"
    echo "3. Deploy Bot"
    echo "4. Show Logs"
    echo "5. Check Status"
    echo "6. Stop Bot"
    echo "7. Restart Bot"
    echo "8. Exit"
    echo ""
}

# Main script
main() {
    check_docker
    
    while true; do
        show_menu
        read -p "Pilih opsi (1-8): " choice
        
        case $choice in
            1)
                setup_env
                ;;
            2)
                setup_vpn
                ;;
            3)
                setup_env
                setup_vpn
                deploy
                ;;
            4)
                show_logs
                ;;
            5)
                check_status
                ;;
            6)
                print_info "Stopping TradingBot..."
                docker-compose down
                print_success "TradingBot stopped!"
                ;;
            7)
                print_info "Restarting TradingBot..."
                docker-compose restart
                print_success "TradingBot restarted!"
                ;;
            8)
                print_info "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Pilihan tidak valid!"
                ;;
        esac
        
        echo ""
        read -p "Tekan Enter untuk kembali ke menu..."
    done
}

# Run main function
main
