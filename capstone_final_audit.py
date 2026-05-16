import subprocess
import requests
import json
import time

class CapstoneAudit:
    def __init__(self):
        self.colors = {
            "HEADER": "\033[95m",
            "OK": "\033[92m",
            "WARNING": "\033[93m",
            "FAIL": "\033[91m",
            "END": "\033[0m",
            "BOLD": "\033[1m"
        }

    def print_section(self, title):
        print(f"\n{self.colors['HEADER']}{self.colors['BOLD']}>>> {title} <<<{self.colors['END']}")

    def run_cmd(self, cmd):
        try:
            return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
        except Exception:
            return None

    def check_iam(self):
        self.print_section("PILAR 1: IDENTITY & ACCESS (TELEPORT)")
        status = self.run_cmd("docker ps --filter name=teleport --format '{{.Status}}'")
        if status:
            print(f"{self.colors['OK']}[✅] Teleport Container: {status}{self.colors['END']}")
        else:
            print(f"{self.colors['FAIL']}[❌] Teleport Container NOT FOUND/OFFLINE{self.colors['END']}")

    def check_network(self):
        self.print_section("PILAR 2: NETWORK & WAF (MODSECURITY)")
        # Test SQL Injection block
        try:
            r = requests.get("http://localhost:8081/?id=1'%20OR%20'1'='1", timeout=3)
            if r.status_code == 403:
                print(f"{self.colors['OK']}[✅] WAF Security: ACTIVE (Blocked SQLi with 403){self.colors['END']}")
            else:
                print(f"{self.colors['WARNING']}[⚠️] WAF Security: BYPASSED/MISCONFIGURED (Status: {r.status_code}){self.colors['END']}")
        except:
            print(f"{self.colors['FAIL']}[❌] WAF Endpoint unreachable (localhost:8081){self.colors['END']}")

    def check_data(self):
        self.print_section("PILAR 3: DATA SECURITY (VAULT & MINIO)")
        # Vault
        vault_raw = self.run_cmd("docker exec vault vault status -format=json 2>/dev/null")
        if vault_raw:
            v_data = json.loads(vault_raw)
            v_status = "LOCKED/SEALED" if v_data['sealed'] else "ACTIVE/UNSEALED"
            v_color = self.colors['WARNING'] if v_data['sealed'] else self.colors['OK']
            print(f"{v_color}[🔒] Vault: {v_status}{self.colors['END']}")
        else:
            print(f"{self.colors['FAIL']}[❌] Vault Container OFFLINE{self.colors['END']}")
        
        # MinIO
        minio_health = self.run_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:8010/minio/health/live")
        if minio_health == "200":
            print(f"{self.colors['OK']}[✅] MinIO API: ONLINE{self.colors['END']}")
        else:
            print(f"{self.colors['FAIL']}[❌] MinIO API: OFFLINE (Status: {minio_health}){self.colors['END']}")

    def check_monitoring(self):
        self.print_section("PILAR 4: MONITORING (WAZUH)")
        wazuh_name = self.run_cmd("docker ps --filter name=wazuh.manager --format '{{.Names}}'")
        if wazuh_name:
            print(f"{self.colors['OK']}[✅] Wazuh Manager: UP ({wazuh_name}){self.colors['END']}")
            agents = self.run_cmd(f"docker exec -it {wazuh_name} /var/ossec/bin/agent_control -lc | grep -c 'Active'")
            print(f"{self.colors['OK']}[📊] Connected Active Agents: {agents or 0}{self.colors['END']}")
        else:
            print(f"{self.colors['FAIL']}[❌] Wazuh Manager NOT FOUND/OFFLINE{self.colors['END']}")

    def check_bcdr(self):
        self.print_section("PILAR 5: BCDR (POSTGRESQL HA)")
        repl = self.run_cmd("docker exec pg_primary psql -U postgres -c 'SELECT state FROM pg_stat_replication;' 2>/dev/null")
        if "streaming" in str(repl).lower():
            print(f"{self.colors['OK']}[✅] DB Replication: STREAMING (Healthy){self.colors['END']}")
        else:
            print(f"{self.colors['FAIL']}[❌] DB Replication: DOWN/NOT FOUND{self.colors['END']}")

    def run(self):
        print(f"{self.colors['BOLD']}=== SOC INFRASTRUCTURE FINAL AUDIT ==={self.colors['END']}")
        print(f"Time: {time.ctime()}")
        self.check_iam()
        self.check_network()
        self.check_data()
        self.check_monitoring()
        self.check_bcdr()
        print(f"\n{self.colors['BOLD']}=== AUDIT FINISHED ==={self.colors['END']}")

if __name__ == "__main__":
    CapstoneAudit().run()
