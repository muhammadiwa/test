# PowerShell setup script untuk TradingBot dengan VPN
# Script ini akan membantu setup environment dan deployment di Windows

param(
    [string]$Action = "menu"
)

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$WarningColor = "Yellow"
$InfoColor = "Cyan"

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $InfoColor
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $SuccessColor
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $WarningColor
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $ErrorColor
}

# Function to check if Docker is installed
function Test-Docker {
    Write-Info "Checking Docker installation..."
    
    try {
        $dockerVersion = docker --version
        Write-Success "Docker detected: $dockerVersion"
    }
    catch {
        Write-Error "Docker tidak ditemukan! Silakan install Docker Desktop terlebih dahulu."
        Write-Host "Download dari: https://docs.docker.com/desktop/windows/" -ForegroundColor Yellow
        exit 1
    }
    
    try {
        $composeVersion = docker compose version
        Write-Success "Docker Compose detected: $composeVersion"
    }
    catch {
        Write-Error "Docker Compose tidak ditemukan!"
        exit 1
    }
}

# Function to setup environment file
function Set-Environment {
    Write-Info "Setting up environment file..."
    
    if (-not (Test-Path ".env")) {
        Write-Info "Membuat file .env dari template..."
        Copy-Item ".env.example" ".env"
        Write-Warning "File .env telah dibuat. Silakan edit file .env dan isi dengan kredensial Anda:"
        Write-Host "  - MEXC_API_KEY" -ForegroundColor Yellow
        Write-Host "  - MEXC_API_SECRET" -ForegroundColor Yellow
        Write-Host "  - TELEGRAM_BOT_TOKEN" -ForegroundColor Yellow
        Write-Host "  - TELEGRAM_CHAT_ID" -ForegroundColor Yellow
        Write-Host "  - VPN_USERNAME (opsional)" -ForegroundColor Yellow
        Write-Host "  - VPN_PASSWORD (opsional)" -ForegroundColor Yellow
        
        # Open .env file in notepad
        notepad .env
        Read-Host "Tekan Enter setelah Anda mengisi file .env"
    }
    else {
        Write-Success "File .env sudah ada!"
    }
}

# Function to setup VPN
function Set-VPN {
    Write-Info "Setting up VPN configuration..."
    
    if (-not (Test-Path "vpn\config.ovpn")) {
        Write-Warning "File konfigurasi VPN tidak ditemukan!"
        Write-Host ""
        Write-Host "Untuk menggunakan VPN, Anda perlu:" -ForegroundColor Yellow
        Write-Host "1. Mendaftar di penyedia VPN gratis seperti:" -ForegroundColor Yellow
        Write-Host "   - ProtonVPN Free: https://protonvpn.com/free-vpn" -ForegroundColor Yellow
        Write-Host "   - Windscribe Free: https://windscribe.com" -ForegroundColor Yellow
        Write-Host "   - TunnelBear Free: https://tunnelbear.com" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "2. Download file konfigurasi OpenVPN (.ovpn) untuk server Asia" -ForegroundColor Yellow
        Write-Host "   (Singapore, Hong Kong, Japan, dll)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "3. Simpan file tersebut sebagai 'vpn\config.ovpn'" -ForegroundColor Yellow
        Write-Host ""
        
        $continue = Read-Host "Apakah Anda ingin melanjutkan tanpa VPN? (y/N)"
        if ($continue -eq "y" -or $continue -eq "Y") {
            Write-Warning "Melanjutkan tanpa VPN. MEXC API mungkin tidak dapat diakses dari Indonesia."
            # Disable VPN in .env
            if (Test-Path ".env") {
                (Get-Content ".env") -replace "VPN_ENABLED=true", "VPN_ENABLED=false" | Set-Content ".env"
            }
        }
        else {
            Write-Error "Setup dibatalkan. Silakan setup VPN terlebih dahulu."
            exit 1
        }
    }
    else {
        Write-Success "File konfigurasi VPN ditemukan!"
    }
}

# Function to build and run the container
function Start-Deployment {
    param([string]$Environment = "production")
    
    Write-Info "Building dan deploying TradingBot ($Environment)..."
    
    # Stop existing container if running
    Write-Info "Stopping existing containers..."
    try {
        if ($Environment -eq "development") {
            docker compose -f docker-compose.dev.yml down
        } else {
            docker compose down
        }
    }
    catch {
        # Ignore if no containers are running
    }
    
    # Build new image
    Write-Info "Building Docker image..."
    if ($Environment -eq "development") {
        docker compose -f docker-compose.dev.yml build --no-cache
    } else {
        docker compose build --no-cache
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build Docker image!"
        exit 1
    }
    
    # Start the services
    Write-Info "Starting TradingBot ($Environment)..."
    if ($Environment -eq "development") {
        docker compose -f docker-compose.dev.yml up -d
    } else {
        docker compose up -d
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "TradingBot telah di-deploy!"
        Write-Host ""
        Write-Host "Untuk memonitor logs:" -ForegroundColor Yellow
        if ($Environment -eq "development") {
            Write-Host "  docker compose -f docker-compose.dev.yml logs -f" -ForegroundColor Cyan
        } else {
            Write-Host "  docker compose logs -f" -ForegroundColor Cyan
        }
        Write-Host ""
        Write-Host "Untuk menghentikan bot:" -ForegroundColor Yellow
        if ($Environment -eq "development") {
            Write-Host "  docker compose -f docker-compose.dev.yml down" -ForegroundColor Cyan
        } else {
            Write-Host "  docker compose down" -ForegroundColor Cyan
        }
        Write-Host ""
        Write-Host "Dashboard (jika diaktifkan): http://localhost:9876" -ForegroundColor Yellow
    }
    else {
        Write-Error "Failed to start TradingBot!"
    }
}

# Function to test deployment
function Test-Deployment {
    Write-Info "Running deployment tests..."
    
    # Check if test script exists
    if (Test-Path "test_deployment.sh") {
        # Run test script using WSL or Git Bash if available
        try {
            if (Get-Command wsl -ErrorAction SilentlyContinue) {
                Write-Info "Running tests using WSL..."
                wsl bash test_deployment.sh
            } elseif (Get-Command bash -ErrorAction SilentlyContinue) {
                Write-Info "Running tests using Git Bash..."
                bash test_deployment.sh
            } else {
                Write-Warning "Bash not available. Running basic PowerShell tests..."
                # Basic PowerShell tests
                Test-BasicDeployment
            }
        }
        catch {
            Write-Warning "Failed to run bash tests. Running basic PowerShell tests..."
            Test-BasicDeployment
        }
    } else {
        Write-Warning "Test script not found. Running basic tests..."
        Test-BasicDeployment
    }
}

# Basic PowerShell deployment tests
function Test-BasicDeployment {
    $testsPassed = 0
    $testsTotal = 0
    
    Write-Info "Running basic deployment tests..."
    
    # Test 1: Check .env file
    $testsTotal++
    if (Test-Path ".env") {
        Write-Success "✅ .env file exists"
        $testsPassed++
    } else {
        Write-Error "❌ .env file not found"
    }
    
    # Test 2: Check VPN config
    $testsTotal++
    if (Test-Path "vpn\config.ovpn") {
        Write-Success "✅ VPN config file exists"
        $testsPassed++
    } else {
        Write-Warning "⚠️  VPN config file not found"
        $testsPassed++  # Don't fail for VPN
    }
    
    # Test 3: Try building image
    $testsTotal++
    try {
        Write-Info "Testing Docker build..."
        docker compose build --quiet
        Write-Success "✅ Docker build successful"
        $testsPassed++
    }
    catch {
        Write-Error "❌ Docker build failed"
    }
    
    Write-Host ""
    Write-Host "Test Results: $testsPassed/$testsTotal passed" -ForegroundColor $(if ($testsPassed -eq $testsTotal) { "Green" } else { "Yellow" })
}

# Function to show logs
function Show-Logs {
    Write-Info "Showing container logs..."
    docker compose logs -f
}

# Function to check status
function Test-Status {
    Write-Info "Checking container status..."
    docker compose ps
    
    Write-Host ""
    Write-Info "Testing MEXC API connectivity..."
    try {
        $result = docker compose exec tradebot curl -s --max-time 10 https://api.mexc.com/api/v3/ping
        if ($LASTEXITCODE -eq 0) {
            Write-Success "MEXC API: Accessible ✅"
        }
        else {
            Write-Error "MEXC API: Not accessible ❌"
        }
    }
    catch {
        Write-Error "Could not test API connectivity"
    }
}

# Function to show menu
function Show-Menu {
    Write-Host ""
    Write-Host "=== TradingBot Management ===" -ForegroundColor Green
    Write-Host "1. Setup Environment" -ForegroundColor Cyan
    Write-Host "2. Setup VPN" -ForegroundColor Cyan
    Write-Host "3. Deploy Bot (Production)" -ForegroundColor Cyan
    Write-Host "4. Deploy Bot (Development)" -ForegroundColor Cyan
    Write-Host "5. Test Deployment" -ForegroundColor Cyan
    Write-Host "6. Show Logs" -ForegroundColor Cyan
    Write-Host "7. Check Status" -ForegroundColor Cyan
    Write-Host "8. Stop Bot" -ForegroundColor Cyan
    Write-Host "9. Restart Bot" -ForegroundColor Cyan
    Write-Host "10. Exit" -ForegroundColor Cyan
    Write-Host ""
}

# Main script
function Main {
    Write-Host "=== TradingBot Setup dengan VPN untuk MEXC API ===" -ForegroundColor Green
    Write-Host ""
    
    Test-Docker
    
    if ($Action -ne "menu") {
        switch ($Action) {
            "env" { Set-Environment }
            "vpn" { Set-VPN }
            "deploy" { 
                Set-Environment
                Set-VPN
                Start-Deployment
            }
            "logs" { Show-Logs }
            "status" { Test-Status }
            "stop" { 
                Write-Info "Stopping TradingBot..."
                docker compose down
                Write-Success "TradingBot stopped!"
            }
            "restart" {
                Write-Info "Restarting TradingBot..."
                docker compose restart
                Write-Success "TradingBot restarted!"
            }
            default {
                Write-Error "Unknown action: $Action"
                Write-Host "Available actions: env, vpn, deploy, logs, status, stop, restart"
                exit 1
            }
        }
        return
    }
    
    while ($true) {
        Show-Menu
        $choice = Read-Host "Pilih opsi (1-10)"
        
        switch ($choice) {
            "1" { Set-Environment }
            "2" { Set-VPN }
            "3" { 
                Set-Environment
                Set-VPN
                Start-Deployment -Environment "production"
            }
            "4" {
                Set-Environment
                Start-Deployment -Environment "development"
            }
            "5" { Test-Deployment }
            "6" { Show-Logs }
            "7" { Test-Status }
            "8" {
                Write-Info "Stopping TradingBot..."
                docker compose down
                docker compose -f docker-compose.dev.yml down
                Write-Success "TradingBot stopped!"
            }
            "9" {
                Write-Info "Restarting TradingBot..."
                docker compose restart
                Write-Success "TradingBot restarted!"
            }
            "10" {
                Write-Info "Goodbye!"
                exit 0
            }
            default {
                Write-Error "Pilihan tidak valid!"
            }
        }
        
        Write-Host ""
        Read-Host "Tekan Enter untuk kembali ke menu"
    }
}

# Run main function
Main
