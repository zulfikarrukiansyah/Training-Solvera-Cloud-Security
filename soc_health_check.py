import subprocess
import socket
import sys

# Konfigurasi Target Layanan & Port
TARGET_SERVICES = {
    "Teleport Proxy": 3080,
    "PostgreSQL Primary": 5432,
    "PostgreSQL Standby": 5433,
    "MinIO Console": 9001,
    "HashiCorp Vault": 8200,
    "Wazuh Dashboard": 443
}

def check_port(name, port):
    """Memeriksa apakah port layanan terbuka di localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', port))
        return result == 0

def get_docker_status():
    """Mengambil status kontainer Docker menggunakan CLI."""
    try:
        # Mencoba menjalankan docker ps melalui shell agar kompatibel dengan WSL/Windows
        result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}|{{.Status}}'], 
                               capture_output=True, text=True)
        return result.stdout.strip().split('\n')
    except Exception:
        return []

def print_banner():
    print("="*60)
    print("      🛡️  SOC OPERATIONAL READINESS DASHBOARD - DAY 10 🛡️")
    print("="*60)

def main():
    print_banner()
    
    # 1. Cek Layanan via Port
    print("\n🔍 MEMERIKSA KONEKTIVITAS LAYANAN (PORT):")
    all_online = True
    for name, port in TARGET_SERVICES.items():
        is_open = check_port(name, port)
        status = "✅ ONLINE" if is_open else "❌ OFFLINE"
        if not is_open: all_online = False
        print(f"   [{status}] {name:<20} (Port: {port})")
    
    # 2. Cek Status Kontainer Docker
    print("\n🐳 MEMERIKSA STATUS KONTAINER DOCKER:")
    containers = get_docker_status()
    if not containers or containers == ['']:
        print("   [!] Tidak ada kontainer Docker yang berjalan.")
    else:
        for ct in containers:
            if '|' in ct:
                name, status = ct.split('|')
                print(f"   [📦] {name:<20} | {status}")

    print("\n" + "="*60)
    if all_online:
        print("🎉 KESIMPULAN: Seluruh infrastruktur lab siap dioperasikan!")
    else:
        print("⚠️  KESIMPULAN: Beberapa layanan masih memerlukan perhatian.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
