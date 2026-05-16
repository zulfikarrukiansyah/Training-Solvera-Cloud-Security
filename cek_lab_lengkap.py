#!/usr/bin/env python3
"""
cek_lab_lengkap.py — Cek Lengkap Open Source Security Lab Hari 1-10
====================================================================
Jalankan sekali untuk cek SEMUA komponen dari Hari 1 hingga Hari 10.

Usage:
  python3 cek_lab_lengkap.py              # cek semua hari
  python3 cek_lab_lengkap.py --day 4      # cek 1 hari saja
  python3 cek_lab_lengkap.py -v           # verbose (tampil detail)
  python3 cek_lab_lengkap.py --fix        # tampil perintah recovery
"""

import subprocess, socket, os, sys, json, time, argparse
from datetime import datetime

# ─── Colors ─────────────────────────────────────────────────────────────────
G="\033[92m"; Y="\033[93m"; R="\033[91m"; C="\033[96m"; B="\033[1m"; D="\033[2m"; X="\033[0m"
PASS=f"{G}[PASS]{X}"; FAIL=f"{R}[FAIL]{X}"; WARN=f"{Y}[WARN]{X}"

BASE    = "/mnt/d/Downloads/Learning"
VERBOSE = False
RESULTS = []   # (day, name, status, detail, fix_cmd)

# ─── Helpers ─────────────────────────────────────────────────────────────────
def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=10).decode().strip()
    except:
        return None

def tcp(port, host="127.0.0.1", t=3):
    try:
        socket.create_connection((host, port), timeout=t).close(); return True
    except:
        return False

def http_ok(url):
    try:
        import urllib.request
        return urllib.request.urlopen(url, timeout=5).status == 200
    except Exception as e:
        return hasattr(e, "code") and e.code == 200

def ok(day, name, passed, detail="", fix=""):
    icon = PASS if passed else FAIL
    print(f"  {icon} {name}")
    if detail and (VERBOSE or not passed):
        print(f"        {D}{detail}{X}")
    RESULTS.append((day, name, True if passed else False, detail, fix))

def warn(day, name, detail="", fix=""):
    print(f"  {WARN} {name}")
    if detail and VERBOSE:
        print(f"        {D}{detail}{X}")
    RESULTS.append((day, name, "WARN", detail, fix))

def hdr(day, title):
    print(f"\n{C}{B}{'─'*58}{X}")
    print(f"{C}{B}  HARI {day:02d} — {title}{X}")
    print(f"{C}{B}{'─'*58}{X}")

# ─── Day 1 ───────────────────────────────────────────────────────────────────
def day1():
    hdr(1, "IAM — LocalStack")
    lc = sh("docker ps --filter name=localstack --format '{{.Names}}'")
    ok(1, "LocalStack container running", bool(lc), f"name={lc}", "bash lab_recovery.sh --day 1")
    up = tcp(4566)
    ok(1, "LocalStack :4566 reachable", up, fix="bash lab_recovery.sh --day 1")
    if up:
        u = sh("aws --endpoint-url=http://localhost:4566 iam list-users --output text 2>/dev/null")
        ok(1, "IAM users exist", bool(u))
    ok(1, "policy.json exists",        os.path.isfile(f"{BASE}/policy.json"))
    ok(1, "strict-ip-policy.json exists", os.path.isfile(f"{BASE}/strict-ip-policy.json"))
    th = sh("which trufflehog 2>/dev/null || docker images trufflesecurity/trufflehog -q 2>/dev/null")
    ok(1, "TruffleHog tersedia", bool(th), fix="docker pull trufflesecurity/trufflehog")

# ─── Day 2 ───────────────────────────────────────────────────────────────────
def day2():
    hdr(2, "Network Security — Docker + iptables")
    nets = sh("docker network ls --format '{{.Name}}'") or ""
    for n in ["public-net","private-app-net","private-db-net","waf-lab-net"]:
        ok(2, f"Docker network '{n}'", n in nets, fix=f"docker network create {n}")
    rules = sh("sudo iptables -L INPUT -n 2>/dev/null") or ""
    if "DROP" in rules or "REJECT" in rules:
        ok(2, "iptables rules loaded (DROP/REJECT present)", True)
    else:
        warn(2, "iptables kosong (tidak persisten setelah WSL restart)",
             "Gap Finding #1 — install iptables-persistent",
             "sudo apt install iptables-persistent && sudo netfilter-persistent save")

# ─── Day 3 ───────────────────────────────────────────────────────────────────
def day3():
    hdr(3, "Data Security — MinIO WORM + HashiCorp Vault")
    mup = tcp(8010)
    ok(3, "MinIO API :8010", mup, fix="bash lab_recovery.sh --day 3")
    if mup:
        ok(3, "MinIO health/live 200", http_ok("http://localhost:8010/minio/health/live"))
    ok(3, "MinIO Console :8011", tcp(8011))
    for v in ["d1","d2","d3","d4"]:
        vols = sh(f"docker volume ls -q --filter name={v}") or ""
        ok(3, f"MinIO volume '{v}'", v in vols)
    vup = tcp(8200)
    ok(3, "Vault :8200", vup, fix="bash lab_recovery.sh --day 3")
    if vup:
        vs = sh("docker exec vault vault status -format=json 2>/dev/null")
        if vs:
            try:
                sealed = json.loads(vs).get("sealed", True)
                if sealed:
                    warn(3, "Vault SEALED", fix="docker restart vault  # (dev mode)")
                else:
                    ok(3, "Vault UNSEALED", True)
            except:
                warn(3, "Vault status parse error")

# ─── Day 4 ───────────────────────────────────────────────────────────────────
def day4():
    hdr(4, "SIEM — Wazuh")
    wm = sh("docker ps --filter name=wazuh.manager --format '{{.Names}}'")
    wi = sh("docker ps --filter name=wazuh.indexer --format '{{.Names}}'")
    wd = sh("docker ps --filter name=wazuh.dashboard --format '{{.Names}}'")
    ok(4, "Wazuh Manager running",   bool(wm), fix="bash lab_recovery.sh --day 4")
    ok(4, "Wazuh Indexer running",   bool(wi))
    ok(4, "Wazuh Dashboard running", bool(wd))
    ok(4, "Wazuh Dashboard :443",    tcp(443))
    ok(4, "local_rules.xml exists",  os.path.isfile(f"{BASE}/local_rules.xml"))
    if wm:
        n = sh(f"docker exec {wm} /var/ossec/bin/agent_control -lc 2>/dev/null | grep -c Active") or "0"
        try:
            ok(4, f"Wazuh agents active ≥ 1", int(n) >= 1, f"{n} agent(s)")
        except:
            warn(4, "Could not count Wazuh agents")

# ─── Day 5 ───────────────────────────────────────────────────────────────────
def day5():
    hdr(5, "Vulnerability Management — Trivy + OpenSCAP")
    tv = sh("trivy --version 2>/dev/null | head -1")
    ok(5, "Trivy installed", bool(tv), tv or "", fix="bash lab_recovery.sh --day 5")
    oscap = sh("oscap --version 2>/dev/null | head -1")
    ok(5, "OpenSCAP installed", bool(oscap), (oscap or "")[:60])
    ok(5, "scan-results.xml exists", os.path.isfile(f"{BASE}/scan-results.xml"))
    ok(5, "scan-report.html exists",
       os.path.isfile(f"{BASE}/scan-report.html") or os.path.isfile(f"{BASE}/report.html"))
    ok(5, "parse_report.py exists", os.path.isfile(f"{BASE}/parse_report.py"))

# ─── Day 6 ───────────────────────────────────────────────────────────────────
def day6():
    hdr(6, "WAF — ModSecurity + Fail2ban")
    waf = sh("docker ps --filter name=waf-server --format '{{.Names}}'")
    bk  = sh("docker ps --filter name=backend-app --format '{{.Names}}'")
    ok(6, "waf-server running",   bool(waf), fix="bash lab_recovery.sh --day 6")
    ok(6, "backend-app running",  bool(bk))
    wup = tcp(8081)
    ok(6, "WAF :8081 reachable",  wup)
    if wup:
        try:
            import urllib.request, urllib.error
            try:
                urllib.request.urlopen("http://localhost:8081/?id=1'%20OR%20'1'='1", timeout=4)
                ok(6, "WAF blokir SQLi", False, "Request NOT blocked!")
            except urllib.error.HTTPError as e:
                ok(6, "WAF blokir SQLi (HTTP 403)", e.code == 403, f"HTTP {e.code}")
            except:
                ok(6, "WAF blokir SQLi (conn drop)", True, "connection refused/dropped")
        except:
            warn(6, "Tidak bisa test WAF SQLi")
    fb = sh("sudo fail2ban-client status 2>/dev/null | head -2")
    ok(6, "Fail2ban running", bool(fb), fix="bash lab_recovery.sh --day 6")

# ─── Day 7 ───────────────────────────────────────────────────────────────────
def day7():
    hdr(7, "Incident Response & Forensics — Volatility 3")
    vbm = sh("VBoxManage --version 2>/dev/null") or sh("VBoxManage.exe --version 2>/dev/null")
    ok(7, "VBoxManage installed", bool(vbm), vbm or "not found")
    vol3 = any(os.path.isfile(p) for p in [
        os.path.expanduser("~/volatility3/vol.py"), "/usr/local/bin/vol", "/usr/bin/vol"])
    ok(7, "Volatility 3 installed", vol3, fix="git clone https://github.com/volatilityfoundation/volatility3.git ~/volatility3")
    ev = f"{BASE}/IR-Evidence"
    ok(7, "IR-Evidence/ folder exists", os.path.isdir(ev))
    coc = f"{ev}/chain-of-custody.txt"
    ok(7, "Chain of Custody file exists", os.path.isfile(coc))
    if os.path.isfile(coc):
        ct = open(coc).read()
        ok(7, "Chain of Custody punya SHA256", "SHA256" in ct or "sha256" in ct.lower())
    dmp = f"{ev}/memory-dump-inc001.dmp"
    if os.path.isfile(dmp):
        mb = os.path.getsize(dmp)/(1024*1024)
        ok(7, f"Memory dump exists ({mb:.0f} MB)", True)
    else:
        warn(7, "memory-dump-inc001.dmp tidak ditemukan (opsional)")

# ─── Day 8 ───────────────────────────────────────────────────────────────────
def day8():
    hdr(8, "BCDR — PostgreSQL Streaming Replication")
    pp = sh("docker ps --filter name=pg_primary --format '{{.Names}}'")
    ps = sh("docker ps --filter name=pg_standby --format '{{.Names}}'")
    ok(8, "pg_primary running",  bool(pp), fix="bash lab_recovery.sh --day 8")
    ok(8, "pg_standby running",  bool(ps))
    ok(8, "PostgreSQL Primary :5432", tcp(5432))
    ok(8, "PostgreSQL Standby :5433", tcp(5433))
    if pp:
        repl = sh("docker exec pg_primary psql -U postgres -tAc 'SELECT state FROM pg_stat_replication;' 2>/dev/null")
        streaming = bool(repl) and "streaming" in repl.lower()
        ok(8, "Streaming replication = 'streaming'", streaming, f"state={repl or 'no output'}")
        if ps and streaming:
            ts = str(int(time.time()))
            sh(f"docker exec pg_primary psql -U postgres -d secure_db -tAc \"INSERT INTO secure_logs(event,severity) VALUES('chk-{ts}','INFO');\" 2>/dev/null")
            time.sleep(1)
            found = sh(f"docker exec pg_standby psql -U postgres -d secure_db -tAc \"SELECT id FROM secure_logs WHERE event='chk-{ts}';\" 2>/dev/null")
            ok(8, "Replikasi Primary→Standby (RPO=0)", bool(found))
    ok(8, "~/bcdr-lab/ exists", os.path.isdir(os.path.expanduser("~/bcdr-lab")))

# ─── Day 9 ───────────────────────────────────────────────────────────────────
def day9():
    hdr(9, "Zero Trust Access — Teleport + OpenSCAP Compliance")
    tsh = sh("which tsh 2>/dev/null") or sh("tsh version 2>/dev/null | head -1")
    ok(9, "Teleport (tsh) binary installed", bool(tsh), fix="bash lab_recovery.sh --day 9")
    tp = tcp(3080)
    ok(9, "Teleport Proxy :3080", tp, fix="bash lab_recovery.sh --day 9")
    if tp:
        ts = sh("tsh status 2>/dev/null")
        ok(9, "tsh session active", bool(ts) and "Logged in" in (ts or ""), ts[:60] if ts else "")
    ok(9, "/etc/teleport.yaml exists", os.path.isfile("/etc/teleport.yaml"))
    ok(9, "scan-report.html exists",  os.path.isfile(f"{BASE}/scan-report.html"))
    ok(9, "scan-results.xml exists",  os.path.isfile(f"{BASE}/scan-results.xml"))

# ─── Day 10 ──────────────────────────────────────────────────────────────────
def day10():
    hdr(10, "SOC Capstone — Scripts & Dokumentasi")
    scripts = ["cek_lab_lengkap.py","lab_checker_10hari.py","capstone_final_audit.py",
               "soc_health_check.py","parse_report.py","lab_recovery.sh","README.md"]
    for f in scripts:
        ok(10, f"{f} exists", os.path.isfile(f"{BASE}/{f}"))
    docs = {
        1:"Progress_Hari_01_IAM_LocalStack.md",        2:"Progress_Hari_02_Network_Security.md",
        3:"Progress_Hari_03_MinIO_Vault.md",           4:"Progress_Hari_04_Wazuh_SIEM.md",
        5:"Progress_Hari_05_Vulnerability_Management.md", 6:"Progress_Hari_06_WAF_Fail2ban.md",
        7:"Progress_Hari_07_IR_Forensik.md",           8:"Progress_Hari_08_BCDR_Postgres.md",
        9:"Progress_Hari_09_Compliance_Access.md",    10:"Progress_Hari_10_Final_Capstone.md",
    }
    for d, fname in docs.items():
        ok(10, f"Progress Hari {d:02d} doc", os.path.isfile(f"{BASE}/{fname}"), fname)
    running = sh("docker ps --format '{{.Names}}'") or ""
    containers = [c for c in running.splitlines() if c.strip()]
    ok(10, f"Docker containers running ≥ 5", len(containers) >= 5,
       f"{len(containers)} running: {', '.join(containers[:6])}")

# ─── Summary ─────────────────────────────────────────────────────────────────
DAY_LABELS = {
    1:"IAM LocalStack",      2:"Network Security",    3:"MinIO + Vault",
    4:"Wazuh SIEM",          5:"Vuln Management",     6:"WAF + Fail2ban",
    7:"IR & Forensics",      8:"BCDR PostgreSQL",     9:"ZTA Compliance",
    10:"SOC Capstone",
}

def summary(show_fix=False):
    bar = "═"*62
    print(f"\n{B}{C}{bar}{X}")
    print(f"{B}{C}  RINGKASAN — OPEN SOURCE SECURITY LAB 10 HARI{X}")
    print(f"{B}{C}{bar}{X}\n")
    by_day = {}
    for (day, name, status, detail, fix) in RESULTS:
        by_day.setdefault(day, []).append((status, fix))
    tp=tf=tw=0
    for d in sorted(by_day):
        checks = by_day[d]
        p = sum(1 for s,_ in checks if s is True)
        f = sum(1 for s,_ in checks if s is False)
        w = sum(1 for s,_ in checks if s=="WARN")
        tp+=p; tf+=f; tw+=w
        pct = int(p/max(len(checks),1)*100)
        filled = int(20*pct/100)
        bar20 = f"{'█'*filled}{'░'*(20-filled)}"
        icon = "✅" if f==0 else ("⚠️" if p>f else "❌")
        lbl = DAY_LABELS.get(d,f"Day {d}")
        print(f"  Hari {d:02d} [{lbl:<20}] {bar20} {pct:3d}%  {icon}  "
              f"{G}{p}✓{X} {R}{f}✗{X} {Y}{w}!{X}")
        if show_fix and f > 0:
            fixes = set(fix for s,fix in checks if s is False and fix)
            for fx in fixes:
                print(f"         {D}→ {fx}{X}")
    total = tp+tf
    pct_total = int(tp/max(total,1)*100)
    print(f"\n{B}  {'─'*60}{X}")
    print(f"{B}  TOTAL: {tp}/{total} checks passed ({pct_total}%){X}")
    print(f"  {G}PASS: {tp}{X}  {R}FAIL: {tf}{X}  {Y}WARN: {tw}{X}")
    if tf == 0:
        print(f"\n  {G}{B}🎉 SEMUA CHECK PASSED — LAB INFRASTRUKTUR SEHAT!{X}")
    elif pct_total >= 70:
        print(f"\n  {Y}{B}⚠️  SEBAGIAN BESAR OK — jalankan: bash lab_recovery.sh{X}")
    else:
        print(f"\n  {R}{B}❌ BANYAK KOMPONEN OFFLINE — jalankan: bash lab_recovery.sh{X}")
    print(f"  {D}Audit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{X}")
    print(f"{B}{C}{'═'*62}{X}\n")

# ─── Main ─────────────────────────────────────────────────────────────────────
DAY_MAP = {1:day1, 2:day2, 3:day3, 4:day4, 5:day5,
           6:day6, 7:day7, 8:day8, 9:day9, 10:day10}

def main():
    global VERBOSE
    p = argparse.ArgumentParser(description="Cek Lengkap Security Lab Hari 1-10")
    p.add_argument("--day","-d", type=int, choices=range(1,11), help="Cek 1 hari saja (1-10)")
    p.add_argument("--verbose","-v", action="store_true", help="Tampil detail semua check")
    p.add_argument("--fix","-f", action="store_true", help="Tampil recovery command untuk item FAIL")
    args = p.parse_args()
    VERBOSE = args.verbose

    print(f"\n{B}{C}{'╔'+'═'*60+'╗'}{X}")
    print(f"{B}{C}║{'  🛡️  CEK LENGKAP SECURITY LAB — HARI 1 s/d 10  ':^60}║{X}")
    print(f"{B}{C}{'╚'+'═'*60+'╝'}{X}")
    print(f"  {D}Analyst: {os.environ.get('USER','unknown')} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{X}")

    days = [args.day] if args.day else list(range(1,11))
    for d in days:
        DAY_MAP[d]()

    summary(show_fix=args.fix)

if __name__ == "__main__":
    main()
