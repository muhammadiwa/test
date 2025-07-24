#!/bin/bash

# Test deployment script untuk memverifikasi setup TradingBot

set -e

echo "=== TradingBot Deployment Test ==="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test Docker installation
test_docker() {
    print_test "Testing Docker installation..."
    
    if command -v docker &> /dev/null; then
        docker_version=$(docker --version)
        print_pass "Docker installed: $docker_version"
    else
        print_fail "Docker not found!"
        return 1
    fi
    
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        if command -v docker-compose &> /dev/null; then
            compose_version=$(docker-compose --version)
        else
            compose_version=$(docker compose version)
        fi
        print_pass "Docker Compose available: $compose_version"
    else
        print_fail "Docker Compose not found!"
        return 1
    fi
    
    return 0
}

# Test environment file
test_env_file() {
    print_test "Testing environment configuration..."
    
    if [ ! -f ".env" ]; then
        print_fail ".env file not found!"
        return 1
    fi
    
    # Check required variables
    required_vars=("MEXC_API_KEY" "MEXC_API_SECRET" "TELEGRAM_BOT_TOKEN" "TELEGRAM_CHAT_ID")
    
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=your_" .env && ! grep -q "^${var}=$" .env; then
            print_pass "$var is configured"
        else
            print_fail "$var not configured or using default value"
            return 1
        fi
    done
    
    return 0
}

# Test VPN configuration
test_vpn_config() {
    print_test "Testing VPN configuration..."
    
    if [ ! -f "vpn/config.ovpn" ]; then
        print_warn "VPN config file not found. Bot will try to run without VPN."
        return 0
    fi
    
    # Basic validation of VPN config
    if grep -q "^client" vpn/config.ovpn && grep -q "^remote" vpn/config.ovpn; then
        print_pass "VPN config file looks valid"
    else
        print_fail "VPN config file appears to be invalid"
        return 1
    fi
    
    return 0
}

# Test Docker build
test_docker_build() {
    print_test "Testing Docker build..."
    
    if docker compose build --quiet; then
        print_pass "Docker build successful"
    else
        print_fail "Docker build failed!"
        return 1
    fi
    
    return 0
}

# Test container startup
test_container_startup() {
    print_test "Testing container startup..."
    
    # Start containers
    if docker compose up -d; then
        print_pass "Containers started"
    else
        print_fail "Failed to start containers!"
        return 1
    fi
    
    # Wait a bit for startup
    sleep 10
    
    # Check if container is running
    if docker compose ps | grep -q "Up"; then
        print_pass "Container is running"
    else
        print_fail "Container not running!"
        docker compose logs
        return 1
    fi
    
    return 0
}

# Test VPN connectivity (if VPN is configured)
test_vpn_connectivity() {
    print_test "Testing VPN connectivity..."
    
    # Check if VPN_ENABLED is true
    if grep -q "VPN_ENABLED=true" .env; then
        # Wait for VPN to connect
        sleep 30
        
        # Check if tun interface exists
        if docker compose exec -T tradebot ip route | grep -q tun; then
            print_pass "VPN interface detected"
            
            # Test IP change
            external_ip=$(docker compose exec -T tradebot curl -s --max-time 10 https://httpbin.org/ip 2>/dev/null | grep -o '"origin": "[^"]*"' | cut -d'"' -f4 || echo "unknown")
            print_pass "External IP through VPN: $external_ip"
        else
            print_warn "VPN interface not detected. Check VPN configuration."
        fi
    else
        print_warn "VPN disabled in configuration"
    fi
    
    return 0
}

# Test MEXC API access
test_mexc_api() {
    print_test "Testing MEXC API access..."
    
    if docker compose exec -T tradebot curl -s --max-time 10 https://api.mexc.com/api/v3/ping > /dev/null; then
        print_pass "MEXC API is accessible"
    else
        print_fail "MEXC API is not accessible!"
        return 1
    fi
    
    return 0
}

# Test bot logs
test_bot_logs() {
    print_test "Testing bot logs..."
    
    # Check if bot is generating logs
    if docker compose logs tradebot | grep -q "Starting TradingBot"; then
        print_pass "Bot startup logs detected"
    else
        print_warn "Bot startup logs not found"
    fi
    
    return 0
}

# Cleanup after tests
cleanup() {
    print_test "Cleaning up test environment..."
    docker compose down
    print_pass "Cleanup completed"
}

# Main test suite
run_tests() {
    local failed_tests=0
    
    echo "Starting deployment tests..."
    echo ""
    
    # Pre-deployment tests
    test_docker || ((failed_tests++))
    test_env_file || ((failed_tests++))
    test_vpn_config || ((failed_tests++))
    
    echo ""
    
    # Build and deployment tests
    test_docker_build || ((failed_tests++))
    test_container_startup || ((failed_tests++))
    
    echo ""
    
    # Runtime tests
    test_vpn_connectivity || ((failed_tests++))
    test_mexc_api || ((failed_tests++))
    test_bot_logs || ((failed_tests++))
    
    echo ""
    echo "=== Test Results ==="
    
    if [ $failed_tests -eq 0 ]; then
        print_pass "All tests passed! 🎉"
        echo ""
        echo "Your TradingBot deployment is ready!"
        echo "Monitor with: docker compose logs -f"
    else
        print_fail "$failed_tests test(s) failed ❌"
        echo ""
        echo "Please fix the issues above before proceeding."
    fi
    
    echo ""
    read -p "Do you want to keep the containers running? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        cleanup
    else
        echo "Containers are still running. Use 'docker compose down' to stop them."
    fi
    
    return $failed_tests
}

# Trap cleanup on script exit
trap cleanup EXIT

# Run the tests
run_tests
