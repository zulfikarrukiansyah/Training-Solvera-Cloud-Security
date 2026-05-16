#!/usr/bin/env python3
"""
lab_checker_10hari.py
=====================
Script validasi komprehensif untuk Open Source Security Lab 10 Hari.
Mengecek semua komponen dari Hari 1 hingga Hari 10 sekaligus.

Usage:
  python3 lab_checker_10hari.py
  python3 lab_checker_10hari.py --verbose
  python3 lab_checker_10hari.py --day 4       (cek 1 hari saja)
  python3 lab_checker_10hari.py --report       (simpan hasil ke file)
"""

import subprocess
import socket
import os
import sys
import json
import time
import argparse
from datetime import datetime

# ─── Color codes ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

PASS = f"{GREEN}[✅ PASS]{RESET}"
FAIL = f"{RED}[❌ FAIL]{RESET}"
WARN = f"{YELLOW}[⚠️  WARN]{RESET}"
INFO = f"{CYAN}[ℹ️  INFO]{RESET}"

# ─── Globals ─────────────────────────────────────────────────────────────────
VERBOSE = False
results = []   # list of (day, check_name, status, detail)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def cmd(command):
    """Run shell command, return stdout or None on failure."""
    try:
        out = subprocess.check_output(command, shell=True,
                                      stderr=subprocess.DEVNULL,
                                      timeout=10)
        return out.decode().strip()
    except Exception:
        return None


def port_open(host, port, timeout=3):
    """Return True if TCP port is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def http_status(url, timeout=5):
    """Return HTTP status code as int, or None."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "lab-checker/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except Exception as e:
        code = getattr(getattr(e, 'code', None), '__class__', None)
        if hasattr(e, 'code'):
            return e.code
        return None


def section(day_num, title):
    bar = "─" * 55
    print(f"\n{CYAN}{BOLD}{bar}{RESET}")
    label = f"HARI {day_num:02d}" if day_num else "SUMMARY"
    print(f"{CYAN}{BOLD}  {label} — {title}{RESET}")
    print(f"{CYAN}{BOLD}{bar}{RESET}")


def record(day, name, ok, detail=""):
    icon = PASS if ok else FAIL
    print(f"  {icon} {name}")
    if detail and (VERBOSE or not ok):
        print(f"         {DIM}{detail}{RESET}")
    results.append((day, name, ok, detail))


def warn(day, name, detail=""):
    print(f"  {WARN} {name}")
    if detail and VERBOSE:
        print(f"         {DIM}{detail}{RESET}")
    results.append((day, name, "WARN", detail))


def info(msg):
    if VERBOSE:
        print(f"  {INFO} {DIM}{msg}{RESET}")


# ─── Day Checks ──────────────────────────────────────────────────────────────

def check_day1():
    """Hari 01 — IAM LocalStack"""
    section(1, "Identity & Access Management (LocalStack)")

    # LocalStack container running
    lc = cmd("docker ps --filter name=localstack --format '{{.Names}}'")
    record(1, "LocalStack container running", bool(lc), f"container={lc or 'not found'}")

    # LocalStack port 4566
    up = port_open("localhost", 4566)
    record(1, "LocalStack IAM endpoint :4566 reachable", up)

    # IAM user exists
    if up:
        users = cmd("aws --endpoint-url=http://localhost:4566 iam list-users --output text 2>/dev/null")
        has_user = bool(users)
        record(1, "IAM users exist in LocalStack", has_user, users[:80] if users else "")
    else:
        record(1, "IAM users exist in LocalStack", False, "LocalStack offline")

    # policy files exist
    base = "/mnt/d/Downloads/Learning"
    policy_ok = os.path.isfile(f"{base}/policy.json")
    strict_ok  = os.path.isfile(f"{base}/strict-ip-policy.json")
    record(1, "policy.json exists", policy_ok, f"{base}/policy.json")
    record(1, "strict-ip-policy.json exists", strict_ok)

    # TruffleHog available
    th = cmd("which trufflehog || docker images trufflesecurity/trufflehog -q 2>/dev/null")
    record(1, "TruffleHog available (secret scanner)", bool(th))


def check_day2():
    """Hari 02 — Network Security"""
    section(2, "Network Security Architecture (iptables + Docker)")

    # Docker networks
    nets = cmd("docker network ls --format '{{.Name}}'") or ""
    for net in ["public-net", "private-app-net", "private-db-net"]:
        record(2, f"Docker network '{net}' exists", net in nets)

    # iptables rules
    rules = cmd("sudo iptables -L INPUT -n 2>/dev/null") or ""
    has_rules = "DROP" in rules or "ACCEPT" in rules
    if has_rules:
        record(2, "iptables rules loaded", True, "rules present in INPUT chain")
    else:
        warn(2, "iptables INPUT chain is empty",
             "Rules not persistent after WSL restart — Gap Finding #1")

    # waf-lab-net (Hari 06 dependency)
    record(2, "Docker network 'waf-lab-net' exists", "waf-lab-net" in nets)


def check_day3():
    """Hari 03 — Data Security (MinIO + Vault)"""
    section(3, "Data Security — MinIO WORM + HashiCorp Vault")

    # MinIO API :8010
    minio_up = port_open("localhost", 8010)
    record(3, "MinIO API :8010 reachable", minio_up)

    # MinIO health endpoint
    if minio_up:
        st = http_status("http://localhost:8010/minio/health/live")
        record(3, "MinIO health/live returns 200", st == 200, f"HTTP {st}")
    else:
        record(3, "MinIO health/live returns 200", False, "MinIO offline")

    # MinIO console :8011
    record(3, "MinIO Console :8011 reachable", port_open("localhost", 8011))

    # Vault :8200
    vault_up = port_open("localhost", 8200)
    record(3, "HashiCorp Vault :8200 reachable", vault_up)

    # Vault status
    if vault_up:
        vs = cmd("docker exec vault vault status -format=json 2>/dev/null")
        if vs:
            try:
                vd = json.loads(vs)
                sealed = vd.get("sealed", True)
                if sealed:
                    warn(3, "Vault is SEALED", "Run: docker exec vault vault operator unseal <KEY>")
                else:
                    record(3, "Vault is UNSEALED (active)", True)
            except Exception:
                record(3, "Vault status parseable", False, vs[:60])
        else:
            warn(3, "Vault status check failed", "Container may not be named 'vault'")

    # MinIO volumes
    for vol in ["d1", "d2", "d3", "d4"]:
        vols = cmd(f"docker volume ls -q --filter name={vol}") or ""
        record(3, f"MinIO volume '{vol}' exists", vol in vols)


def check_day4():
    """Hari 04 — Wazuh SIEM"""
    section(4, "Security Monitoring & SIEM (Wazuh)")

    # Wazuh manager container
    wm = cmd("docker ps --filter name=wazuh.manager --format '{{.Names}}'")
    record(4, "Wazuh Manager container running", bool(wm), f"name={wm or 'not found'}")

    # Wazuh indexer
    wi = cmd("docker ps --filter name=wazuh.indexer --format '{{.Names}}'")
    record(4, "Wazuh Indexer container running", bool(wi))

    # Wazuh dashboard
    wd = cmd("docker ps --filter name=wazuh.dashboard --format '{{.Names}}'")
    record(4, "Wazuh Dashboard container running", bool(wd))

    # Dashboard port 443
    record(4, "Wazuh Dashboard :443 reachable", port_open("localhost", 443))

    # custom rules file
    rules_file = "/mnt/d/Downloads/Learning/local_rules.xml"
    record(4, "Wazuh custom rules file exists", os.path.isfile(rules_file))

    # active agents
    if wm:
        agents = cmd(f"docker exec {wm} /var/ossec/bin/agent_control -lc 2>/dev/null | grep -c Active")
        try:
            n = int(agents or 0)
            record(4, f"Wazuh active agents count ≥ 1", n >= 1, f"{n} agent(s) active")
        except Exception:
            warn(4, "Could not count Wazuh agents")


def check_day5():
    """Hari 05 — Vulnerability Management"""
    section(5, "Vulnerability Management (Trivy + OpenSCAP)")

    # Trivy
    tv = cmd("trivy --version 2>/dev/null | head -1")
    record(5, "Trivy installed", bool(tv), tv or "not found")

    # OpenSCAP
    oscap = cmd("oscap --version 2>/dev/null | head -1")
    record(5, "OpenSCAP scanner installed", bool(oscap), oscap[:60] if oscap else "not found")

    # scan results
    base = "/mnt/d/Downloads/Learning"
    record(5, "scan-results.xml exists", os.path.isfile(f"{base}/scan-results.xml"))
    record(5, "report.html (OpenSCAP) exists",
           os.path.isfile(f"{base}/report.html") or os.path.isfile(f"{base}/scan-report.html"))
    record(5, "parse_report.py exists", os.path.isfile(f"{base}/parse_report.py"))

    # SSG file
    ssg_paths = [
        os.path.expanduser("~/ssg"),
        "/usr/share/xml/scap/ssg/content",
    ]
    ssg_found = any(os.path.isdir(p) for p in ssg_paths)
    record(5, "SCAP Security Guide (SSG) present", ssg_found)


def check_day6():
    """Hari 06 — WAF & Fail2ban"""
    section(6, "Web Application Firewall (ModSecurity + Fail2ban)")

    # WAF container
    waf = cmd("docker ps --filter name=waf-server --format '{{.Names}}'")
    record(6, "WAF (waf-server) container running", bool(waf))

    # backend-app
    bk = cmd("docker ps --filter name=backend-app --format '{{.Names}}'")
    record(6, "backend-app container running", bool(bk))

    # WAF port 8081
    waf_up = port_open("localhost", 8081)
    record(6, "WAF endpoint :8081 reachable", waf_up)

    # SQLi block test
    if waf_up:
        try:
            import urllib.request, urllib.error
            url = "http://localhost:8081/?id=1%27%20OR%20%271%27%3D%271"
            try:
                urllib.request.urlopen(url, timeout=4)
                record(6, "WAF blocks SQL Injection (expects 403/drop)", False, "Request NOT blocked!")
            except urllib.error.HTTPError as e:
                record(6, "WAF blocks SQL Injection", e.code == 403, f"HTTP {e.code}")
            except Exception:
                # connection drop also counts as blocked
                record(6, "WAF blocks SQL Injection (connection drop)", True, "connection refused/dropped")
        except ImportError:
            warn(6, "urllib not available for WAF test")
    else:
        record(6, "WAF blocks SQL Injection", False, "WAF offline")

    # Fail2ban
    fb = cmd("sudo fail2ban-client status 2>/dev/null | head -2")
    record(6, "Fail2ban running", bool(fb), fb[:80] if fb else "not running or no sudo")

    if fb:
        jails_ok = "nginx-http-auth" in fb or "sshd" in fb
        record(6, "Fail2ban jails active (sshd or nginx-http-auth)",
               jails_ok, fb[:120])


def check_day7():
    """Hari 07 — Incident Response & Forensics"""
    section(7, "Incident Response & Digital Forensics (Volatility 3)")

    base = "/mnt/d/Downloads/Learning"

    # VBoxManage
    vbm = cmd("VBoxManage --version 2>/dev/null") or cmd("VBoxManage.exe --version 2>/dev/null")
    record(7, "VBoxManage installed", bool(vbm), vbm or "not found")

    # Volatility 3
    vol3_paths = [
        os.path.expanduser("~/volatility3/vol.py"),
        "/usr/local/bin/vol",
        "/usr/bin/vol",
    ]
    vol3 = any(os.path.isfile(p) for p in vol3_paths)
    record(7, "Volatility 3 installed", vol3)

    # Evidence folder
    ev_dir = f"{base}/IR-Evidence"
    record(7, "IR-Evidence folder exists", os.path.isdir(ev_dir))

    # Chain of custody
    coc = f"{ev_dir}/chain-of-custody.txt"
    record(7, "Chain of custody file exists", os.path.isfile(coc))
    if os.path.isfile(coc):
        content = open(coc).read()
        record(7, "Chain of custody has SHA256 hash",
               "SHA256" in content or "sha256" in content.lower())

    # Memory dump (may be large, just check existence)
    dump = f"{ev_dir}/memory-dump-inc001.dmp"
    if os.path.isfile(dump):
        size_mb = os.path.getsize(dump) / (1024*1024)
        record(7, f"Memory dump exists ({size_mb:.0f} MB)", True)
    else:
        warn(7, "memory-dump-inc001.dmp not found",
             "Expected at IR-Evidence/memory-dump-inc001.dmp")


def check_day8():
    """Hari 08 — BCDR PostgreSQL HA"""
    section(8, "Business Continuity & Disaster Recovery (PostgreSQL HA)")

    # pg_primary
    pg_p = cmd("docker ps --filter name=pg_primary --format '{{.Names}}'")
    record(8, "pg_primary container running", bool(pg_p))

    # pg_standby
    pg_s = cmd("docker ps --filter name=pg_standby --format '{{.Names}}'")
    record(8, "pg_standby container running", bool(pg_s))

    # Port 5432
    record(8, "PostgreSQL Primary :5432 reachable", port_open("localhost", 5432))

    # Port 5433
    record(8, "PostgreSQL Standby :5433 reachable", port_open("localhost", 5433))

    # Replication state
    if pg_p:
        repl = cmd("docker exec pg_primary psql -U postgres -tAc "
                   "'SELECT state FROM pg_stat_replication;' 2>/dev/null")
        streaming = bool(repl) and "streaming" in repl.lower()
        record(8, "Streaming replication state = 'streaming'",
               streaming, f"state={repl or 'no output'}")

        # RPO check via insert/select
        if pg_s and streaming:
            ts = str(int(time.time()))
            ins = cmd(f"docker exec pg_primary psql -U postgres -d secure_db -tAc "
                      f"\"INSERT INTO secure_logs(event,severity) "
                      f"VALUES('checker-{ts}','INFO') RETURNING id;\" 2>/dev/null")
            if ins:
                time.sleep(1)
                sel = cmd(f"docker exec pg_standby psql -U postgres -d secure_db -tAc "
                          f"\"SELECT id FROM secure_logs WHERE event='checker-{ts}';\" 2>/dev/null")
                record(8, "Data replicated Primary→Standby (RPO=0)", bool(sel),
                       f"inserted id={ins} found={sel or 'not found'}")
            else:
                warn(8, "Could not insert test row into secure_logs",
                     "Table may not exist — run Hari 08 lab first")
    else:
        record(8, "Streaming replication state = 'streaming'", False, "pg_primary offline")

    # bcdr-lab folder
    bcdr_dir = os.path.expanduser("~/bcdr-lab")
    record(8, "~/bcdr-lab directory exists", os.path.isdir(bcdr_dir))


def check_day9():
    """Hari 09 — Compliance & Zero Trust (Teleport + OpenSCAP)"""
    section(9, "Compliance & Zero Trust Access (Teleport + OpenSCAP)")

    base = "/mnt/d/Downloads/Learning"

    # Teleport binary
    tsh = cmd("which tsh 2>/dev/null") or cmd("tsh version 2>/dev/null | head -1")
    record(9, "Teleport (tsh) binary installed", bool(tsh))

    # Teleport port 3080
    tp_up = port_open("localhost", 3080)
    record(9, "Teleport Proxy :3080 reachable", tp_up)

    # tsh status
    if tp_up:
        ts = cmd("tsh status 2>/dev/null")
        record(9, "tsh session active (logged in)", bool(ts) and "Logged in" in (ts or ""))

    # OpenSCAP
    oscap = cmd("oscap --version 2>/dev/null | head -1")
    record(9, "OpenSCAP scanner installed", bool(oscap))

    # Scan reports
    record(9, "scan-report.html exists",
           os.path.isfile(f"{base}/scan-report.html"))
    record(9, "scan-results.xml exists",
           os.path.isfile(f"{base}/scan-results.xml"))

    # Final report (post-remediation)
    final_html  = os.path.isfile(f"{base}/final-report.html")
    final_xml   = os.path.isfile(f"{base}/final-results.xml")
    record(9, "Post-remediation final-report.html exists", final_html)
    record(9, "Post-remediation final-results.xml exists", final_xml)

    # teleport.yaml config
    record(9, "/etc/teleport.yaml config exists",
           os.path.isfile("/etc/teleport.yaml"))


def check_day10():
    """Hari 10 — SOC Operations Capstone"""
    section(10, "SOC Operations & Capstone Audit")

    base = "/mnt/d/Downloads/Learning"

    # capstone scripts
    record(10, "capstone_final_audit.py exists",
           os.path.isfile(f"{base}/capstone_final_audit.py"))
    record(10, "soc_health_check.py exists",
           os.path.isfile(f"{base}/soc_health_check.py"))
    record(10, "lab_checker_10hari.py exists",
           os.path.isfile(f"{base}/lab_checker_10hari.py"))

    # Progress Hari 10 doc
    record(10, "Progress_Hari_10_Final_Capstone.md exists",
           os.path.isfile(f"{base}/Progress_Hari_10_Final_Capstone.md"))

    # All 10 progress files
    for d in range(1, 11):
        names = {
            1: "Progress_Hari_01_IAM_LocalStack.md",
            2: "Progress_Hari_02_Network_Security.md",
            3: "Progress_Hari_03_MinIO_Vault.md",
            4: "Progress_Hari_04_Wazuh_SIEM.md",
            5: "Progress_Hari_05_Vulnerability_Management.md",
            6: "Progress_Hari_06_WAF_Fail2ban.md",
            7: "Progress_Hari_07_IR_Forensik.md",
            8: "Progress_Hari_08_BCDR_Postgres.md",
            9: "Progress_Hari_09_Compliance_Access.md",
            10: "Progress_Hari_10_Final_Capstone.md",
        }
        fname = names[d]
        record(10, f"Progress doc Hari {d:02d} exists",
               os.path.isfile(f"{base}/{fname}"), fname)

    # README
    record(10, "README.md exists", os.path.isfile(f"{base}/README.md"))

    # Overall service count
    running = cmd("docker ps --format '{{.Names}}'") or ""
    containers = [c for c in running.splitlines() if c.strip()]
    n = len(containers)
    record(10, f"Docker containers running ≥ 5", n >= 5,
           f"{n} running: {', '.join(containers[:8])}")


# ─── Summary ──────────────────────────────────────────────────────────────────

def print_summary():
    bar = "═" * 60
    print(f"\n{BOLD}{CYAN}{bar}{RESET}")
    print(f"{BOLD}{CYAN}  RINGKASAN HASIL — OPEN SOURCE SECURITY LAB 10 HARI{RESET}")
    print(f"{BOLD}{CYAN}{bar}{RESET}\n")

    by_day = {}
    for (day, name, ok, detail) in results:
        by_day.setdefault(day, []).append(ok)

    total_pass = total_fail = total_warn = 0
    day_labels = {
        1: "IAM LocalStack",
        2: "Network Security",
        3: "MinIO + Vault",
        4: "Wazuh SIEM",
        5: "Vulnerability Mgmt",
        6: "WAF + Fail2ban",
        7: "IR & Forensics",
        8: "BCDR PostgreSQL",
        9: "Compliance ZTA",
        10: "SOC Capstone",
    }

    for day in sorted(by_day.keys()):
        checks = by_day[day]
        p = sum(1 for c in checks if c is True)
        f = sum(1 for c in checks if c is False)
        w = sum(1 for c in checks if c == "WARN")
        total_pass += p; total_fail += f; total_warn += w
        pct = int(p / max(len(checks),1) * 100)
        bar_len = 20
        filled = int(bar_len * pct / 100)
        prog = f"{'█'*filled}{'░'*(bar_len-filled)}"
        status_icon = "✅" if f == 0 else ("⚠️" if p > f else "❌")
        label = day_labels.get(day, f"Day {day}")
        print(f"  Hari {day:02d} [{label:<20}] {prog} {pct:3d}%  {status_icon}  "
              f"{GREEN}{p}✅{RESET} {RED}{f}❌{RESET} {YELLOW}{w}⚠️{RESET}")

    total = total_pass + total_fail
    overall_pct = int(total_pass / max(total, 1) * 100)
    print(f"\n{BOLD}  {'─'*58}{RESET}")
    print(f"{BOLD}  TOTAL  : {total_pass}/{total} checks passed ({overall_pct}%){RESET}")
    print(f"  {GREEN}PASS{RESET}: {total_pass}  {RED}FAIL{RESET}: {total_fail}  "
          f"{YELLOW}WARN{RESET}: {total_warn}")

    if total_fail == 0:
        print(f"\n  {GREEN}{BOLD}🎉 SEMUA CHECK PASSED — LAB INFRASTRUKTUR SEHAT!{RESET}")
    elif overall_pct >= 70:
        print(f"\n  {YELLOW}{BOLD}⚠️  INFRASTRUKTUR SEBAGIAN BESAR OK — Cek item FAIL di atas{RESET}")
    else:
        print(f"\n  {RED}{BOLD}❌ BANYAK KOMPONEN OFFLINE — Jalankan recovery script{RESET}")

    print(f"\n  {DIM}Waktu audit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{CYAN}{'═'*60}{RESET}\n")


def save_report():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"/mnt/d/Downloads/Learning/lab_check_report_{ts}.txt"
    lines = []
    lines.append(f"Open Source Security Lab — Hasil Audit {ts}\n")
    lines.append("="*60 + "\n")
    for (day, name, ok, detail) in results:
        status = "PASS" if ok is True else ("FAIL" if ok is False else "WARN")
        lines.append(f"Hari {day:02d} | {status:4s} | {name}")
        if detail:
            lines.append(f"             {detail}")
        lines.append("")
    try:
        with open(path, "w") as f:
            f.write("\n".join(lines))
        print(f"  {INFO} Report saved to: {path}")
    except Exception as e:
        print(f"  {WARN} Could not save report: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────

DAY_MAP = {
    1: check_day1,
    2: check_day2,
    3: check_day3,
    4: check_day4,
    5: check_day5,
    6: check_day6,
    7: check_day7,
    8: check_day8,
    9: check_day9,
    10: check_day10,
}


def main():
    global VERBOSE

    parser = argparse.ArgumentParser(
        description="Lab Checker — Open Source Security Lab 10 Hari"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show extra detail for passing checks too")
    parser.add_argument("--day", "-d", type=int, choices=range(1, 11),
                        help="Check only a specific day (1-10)")
    parser.add_argument("--report", "-r", action="store_true",
                        help="Save results to a text file")
    args = parser.parse_args()

    VERBOSE = args.verbose

    print(f"\n{BOLD}{CYAN}{'╔'+'═'*58+'╗'}{RESET}")
    print(f"{BOLD}{CYAN}║{'  🛡️  OPEN SOURCE SECURITY LAB — CHECKER 10 HARI  ':^58}║{RESET}")
    print(f"{BOLD}{CYAN}{'╚'+'═'*58+'╝'}{RESET}")
    print(f"  {DIM}Analyst: {os.environ.get('USER','unknown')} | "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")

    days_to_run = [args.day] if args.day else list(range(1, 11))

    for d in days_to_run:
        DAY_MAP[d]()

    print_summary()

    if args.report:
        save_report()


if __name__ == "__main__":
    main()
