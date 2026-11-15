"""Read native STA reports including OpenSTA's explicit 'max' qualifier."""
from common_runtime import *
import re
def main():
    rows=list(csv.DictReader((O/'native_flow_timing.csv').open()))
    for r in rows:
        d=O/'native'/r['case']/r['method']/r['block'];log=(d/'native.log').read_text()
        slack=re.search(r'worst slack(?: max)? (-?[\d.eE+]+)',log);tns=re.search(r'tns(?: max)? (-?[\d.eE+]+)',log);assert slack and tns
        unit=re.search(r'^\s*time\s+([\d.]+)(\w+)',log,re.M);factor=float(unit[1])*{'s':1e12,'ms':1e9,'us':1e6,'ns':1e3,'ps':1.,'fs':1e-3}[unit[2]]
        values=dict(worst_slack=float(slack[1]),tns=float(tns[1]),sta_time_unit=unit[0].strip(),worst_slack_ps=float(slack[1])*factor,tns_ps=float(tns[1])*factor)
        r.update(values);receipt=read(d/'receipt.json');receipt.update(values);write(d/'receipt.json',receipt)
    csvwrite(O/'native_flow_timing.csv',rows)
    write(O/'sta_parse_checks.json',dict(runs=len(rows),passed=True,units=sorted(set(r['sta_time_unit'] for r in rows)),scope='Raw report values with max qualifier, native units and picosecond conversion; no extraction rerun or timing adjustment'))
if __name__=='__main__':main()
