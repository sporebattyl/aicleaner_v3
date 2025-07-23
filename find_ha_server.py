#!/usr/bin/env python3
"""
Home Assistant Server Discovery
Helps find your real HA server IP address on the network
"""

import socket
import requests
import ipaddress
import concurrent.futures
from typing import List, Dict

def get_local_networks() -> List[str]:
    """Get local network ranges to scan"""
    networks = []
    
    # Get all network interfaces
    try:
        # Get default gateway
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        
        # Determine network based on local IP
        ip = ipaddress.IPv4Address(local_ip)
        
        # Common network ranges
        common_networks = [
            "192.168.1.0/24",
            "192.168.0.0/24", 
            "10.0.0.0/24",
            "172.16.0.0/24"
        ]
        
        # Add network containing our IP
        for mask in [24, 16, 8]:
            network = ipaddress.IPv4Network(f"{local_ip}/{mask}", strict=False)
            if network.num_addresses <= 256:  # Only scan small networks
                networks.append(str(network))
                break
        
        # Add common networks
        networks.extend(common_networks)
        
        # Remove duplicates
        networks = list(set(networks))
        
        print(f"🔍 Local IP: {local_ip}")
        print(f"🌐 Networks to scan: {networks}")
        
        return networks
        
    except Exception as e:
        print(f"Error getting networks: {e}")
        return ["192.168.1.0/24", "192.168.0.0/24"]

def check_ha_server(ip: str) -> Dict:
    """Check if IP has a Home Assistant server"""
    try:
        # Try common HA ports
        ports = [8123, 80, 443]
        
        for port in ports:
            try:
                url = f"http://{ip}:{port}"
                response = requests.get(url, timeout=2)
                
                # Check for HA indicators in response
                ha_indicators = [
                    "Home Assistant",
                    "Lovelace",
                    "homeassistant",
                    response.status_code in [200, 401, 415]  # HA returns these codes
                ]
                
                if any(ha_indicators):
                    return {
                        "ip": ip,
                        "port": port,
                        "url": url,
                        "status_code": response.status_code,
                        "found": True,
                        "headers": dict(response.headers)
                    }
                    
            except:
                continue
                
        return {"ip": ip, "found": False}
        
    except Exception as e:
        return {"ip": ip, "found": False, "error": str(e)}

def scan_for_ha_servers() -> List[Dict]:
    """Scan local networks for Home Assistant servers"""
    print("🔍 Scanning for Home Assistant servers...")
    
    networks = get_local_networks()
    all_ips = []
    
    # Generate IP list from networks
    for network_str in networks:
        try:
            network = ipaddress.IPv4Network(network_str, strict=False)
            # Only scan first 50 IPs to avoid taking too long
            for ip in list(network.hosts())[:50]:
                all_ips.append(str(ip))
        except:
            continue
    
    # Remove duplicates
    all_ips = list(set(all_ips))
    print(f"📡 Scanning {len(all_ips)} IP addresses...")
    
    ha_servers = []
    
    # Parallel scanning for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_ip = {executor.submit(check_ha_server, ip): ip for ip in all_ips}
        
        for future in concurrent.futures.as_completed(future_to_ip):
            result = future.result()
            if result.get("found"):
                ha_servers.append(result)
                print(f"✅ Found HA server: {result['url']} (Status: {result['status_code']})")
    
    return ha_servers

def main():
    """Main discovery function"""
    print("Home Assistant Server Discovery")
    print("=" * 40)
    
    servers = scan_for_ha_servers()
    
    if servers:
        print(f"\n🎉 Found {len(servers)} Home Assistant server(s):")
        for i, server in enumerate(servers, 1):
            print(f"\n{i}. {server['url']}")
            print(f"   IP: {server['ip']}")
            print(f"   Port: {server['port']}")
            print(f"   Status Code: {server['status_code']}")
            
            # Check if it has server header info
            if 'headers' in server:
                server_header = server['headers'].get('Server', '')
                if server_header:
                    print(f"   Server: {server_header}")
        
        print(f"\n💡 To test with Playwright:")
        for server in servers:
            print(f"   python3 playwright_ha_test.py {server['url']}")
    else:
        print("\n❌ No Home Assistant servers found on local network")
        print("\n💡 Manual options:")
        print("   - Check your HA server's IP manually")
        print("   - Use: python3 playwright_ha_test.py http://YOUR_HA_IP:8123")

if __name__ == "__main__":
    main()