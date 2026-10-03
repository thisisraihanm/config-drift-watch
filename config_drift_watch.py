"""Compare read-only Windows snapshots without confusing collection gaps with deletions."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from report import write_report

SECTIONS = ('interfaces', 'dns', 'firewall', 'services')


def validate(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('schema_version') != 1:
        raise ValueError('Snapshot schema_version must be 1')
    for field in ('host', 'platform', 'timestamp'):
        if not isinstance(snapshot.get(field), str) or not snapshot[field].strip():
            raise ValueError(f'Snapshot requires {field}')
    if not isinstance(snapshot.get('coverage'), dict):
        raise ValueError('Snapshot requires coverage for every section')
    scope = snapshot.get('service_scope')
    if not isinstance(scope, list) or any(not isinstance(s, str) or not s for s in scope) or len(set(scope)) != len(scope):
        raise ValueError('service_scope must list unique requested service names')
    for section in SECTIONS:
        if snapshot['coverage'].get(section) not in ('ok', 'error'):
            raise ValueError(f'Invalid coverage for {section}')
        if snapshot['coverage'][section] == 'ok' and not isinstance(snapshot.get(section), dict):
            raise ValueError(f'Section {section} must be an object when coverage is ok')
    if snapshot['coverage']['services'] == 'ok' and set(scope) != set(snapshot['services']):
        raise ValueError('Collected services must match service_scope')
    return snapshot


def flatten(value, path=()):
    if isinstance(value, dict) and value:
        result = {}
        for key, item in value.items():
            result.update(flatten(item, path + (key,)))
        return result
    # DNS order affects resolver behavior; lists deliberately remain ordered.
    return {path: value}


def compare(before, after):
    validate(before)
    validate(after)
    if (before['host'].casefold(), before['platform']) != (after['host'].casefold(), after['platform']):
        raise ValueError('Snapshots must describe the same host and platform')
    findings = []
    changes = []
    incomplete = False
    for section in SECTIONS:
        if section == 'services' and set(before['service_scope']) != set(after['service_scope']):
            incomplete = True
            findings.append({'status': 'incomplete', 'item': section, 'evidence': 'Requested service scope differs; service additions/removals cannot be inferred.', 'next_step': 'Recollect both snapshots with the same ServiceName list.'})
            continue
        if before['coverage'][section] != 'ok' or after['coverage'][section] != 'ok':
            incomplete = True
            findings.append({'status': 'incomplete', 'item': section, 'evidence': 'At least one snapshot could not collect this section; no deletion is inferred.', 'next_step': 'Review collector errors and recollect this section before judging drift.'})
            continue
        # Compare each keyed item separately so adding one device/service is
        # represented by one useful finding, rather than dozens of leaf diffs.
        left, right = before[section], after[section]
        for item in sorted(set(left) | set(right)):
            if item not in left or item not in right:
                change = {'section': section, 'item': item, 'kind': 'added' if item in right else 'removed', 'before': left.get(item), 'after': right.get(item)}
                changes.append(change)
                findings.append(finding(change))
                continue
            lflat, rflat = flatten(left[item]), flatten(right[item])
            for path in sorted(set(lflat) | set(rflat)):
                if path in lflat and path in rflat and lflat[path] == rflat[path]:
                    continue
                change = {'section': section, 'item': item, 'field_path': list(path), 'kind': 'changed' if path in lflat and path in rflat else ('added' if path in rflat else 'removed'), 'before': lflat.get(path), 'after': rflat.get(path)}
                changes.append(change)
                findings.append(finding(change))
    status = 'incomplete' if incomplete else ('drift' if changes else 'unchanged')
    if not findings:
        findings.append({'status': 'unchanged', 'item': before['host'], 'evidence': 'No differences in the four successfully collected sections.', 'next_step': 'Keep the baseline with its change ticket. Other system settings were not checked.'})
    return {'schema_version': 1, 'timestamp': datetime.now(timezone.utc).isoformat(), 'status': status, 'summary': f'{len(changes)} observed changes. Change is evidence, not proof of misconfiguration.', 'host': before['host'], 'before_timestamp': before['timestamp'], 'after_timestamp': after['timestamp'], 'findings': findings, 'changes': changes, 'collector_errors': {'before': before.get('errors', []), 'after': after.get('errors', [])}}


def finding(change):
    section = change['section']
    advice = {
        'dns': 'Check whether resolver addresses and order match the intended network or VPN. Confirm against a change ticket before reverting.',
        'interfaces': 'Compare IP, gateway, route metric, and adapter details with the intended network. DHCP or VPN changes can be legitimate.',
        'firewall': 'Review the intended profile policy and effective GPO. This snapshot covers profile enabled state, not individual firewall rules.',
        'services': 'Check the service owner and intended startup mode. A stopped service may be intentional; investigate before restarting.'
    }[section]
    label = '/'.join([section, change['item']] + change.get('field_path', []))
    evidence = f"{change['kind']}: {json.dumps(change['before'], ensure_ascii=False)} → {json.dumps(change['after'], ensure_ascii=False)}"
    return {'status': 'review', 'item': label, 'evidence': evidence, 'next_step': advice}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', type=Path)
    p.add_argument('--after', type=Path)
    p.add_argument('--demo', action='store_true')
    p.add_argument('--output', default='reports/config-drift')
    args = p.parse_args()
    if args.demo:
        if args.before or args.after:
            p.error('Use --demo or a --before/--after pair')
        args.before = Path(__file__).parent / 'examples/before.json'
        args.after = Path(__file__).parent / 'examples/after.json'
    elif not args.before or not args.after:
        p.error('Both --before and --after are required')
    try:
        result = compare(json.loads(args.before.read_text(encoding='utf-8-sig')), json.loads(args.after.read_text(encoding='utf-8-sig')))
        report = write_report(result, args.output, 'Config Drift Watch')
        print(f"{result['status'].upper()}: {report}")
        return 0 if result['status'] == 'unchanged' else (2 if result['status'] == 'incomplete' else 1)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
