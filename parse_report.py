import xml.etree.ElementTree as ET

tree = ET.parse('scan-results.xml')
root = tree.getroot()
ns = {'xccdf': 'http://checklists.nist.gov/xccdf/1.2'}

score_elem = root.find('.//xccdf:score', ns)
score = score_elem.text if score_elem is not None else 'N/A'
print(f'Score: {score}')

results = {'pass': 0, 'fail': 0, 'notapplicable': 0, 'notchecked': 0}
fails = []

for rr in root.findall('.//xccdf:rule-result', ns):
    result_elem = rr.find('xccdf:result', ns)
    if result_elem is not None:
        r = result_elem.text.strip()
        results[r] = results.get(r, 0) + 1
        if r == 'fail':
            rule_id = rr.get('idref', '').replace('xccdf_org.ssgproject.content_rule_', '')
            severity = rr.get('severity', 'unknown')
            fails.append((severity, rule_id))

print(f'PASS:           {results["pass"]}')
print(f'FAIL:           {results["fail"]}')
print(f'NOT APPLICABLE: {results["notapplicable"]}')
print(f'NOT CHECKED:    {results["notchecked"]}')

# Sort by severity
sev_order = {'high': 0, 'medium': 1, 'low': 2, 'unknown': 3}
fails.sort(key=lambda x: sev_order.get(x[0], 3))

print('\nTop FAILED Rules (sorted by severity):')
for sev, rule in fails[:20]:
    print(f'  [{sev.upper():6}] {rule}')
