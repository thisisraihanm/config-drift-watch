# Config Drift Watch

## Open it without commands (Windows)

[**Download the Windows app**](https://github.com/thisisraihanm/config-drift-watch/releases/latest) → download **ConfigDriftWatch-Windows.zip** under Assets → **Extract All** → double-click **ConfigDriftWatch.exe**. Python is included.

Click **Try a safe example** first. Then Click **Save current settings** while things work. Save again after a change. Choose the earlier and later saved files, then click **Compare saved settings**. You do not need to open or edit the saved files.

[Step-by-step beginner guide](../START-HERE.md). The screen and report explain the result in plain language. Detailed evidence remains available for IT.

If you downloaded source code with **Code → Download ZIP**, Python 3.11+ with Tk is required; double-click **Start-Windows.cmd** after installing it.


**Answer “what changed?” with a before/after report for a Windows endpoint.**

After a VPN installation or a maintenance window, a laptop suddenly behaves differently. Instead of resetting everything, capture a known-good snapshot and compare it with the current settings. The report highlights changes worth checking against the intended configuration.

This is a read-only comparison tool. It does not declare every change a fault or automatically revert anything.

## Try the offline demo

Requires Python 3.11 or newer; no pip packages. Run from this repository directory:

```sh
python config_drift_watch.py --demo
```

Open `reports/config-drift.html`. The fictional example shows three changes: reordered DNS servers, a disabled firewall profile, and a stopped print spooler. Exit code **1** is expected because drift is present.

[Included fictional example report](demo-report.html)

## Capture Windows snapshots

The collector targets Windows 10/11 and Windows Server with the NetTCPIP, NetAdapter, DnsClient, NetSecurity, and CIM cmdlets available. Use Windows PowerShell 5.1 or newer under your organization's script policy:

```powershell
powershell -NoProfile -File .\Collect-Snapshot.ps1 -OutputPath .\snapshots\before.json
```

After the planned change, collect again with the same service list:

```powershell
powershell -NoProfile -File .\Collect-Snapshot.ps1 -OutputPath .\snapshots\after.json
python .\config_drift_watch.py --before .\snapshots\before.json --after .\snapshots\after.json
```

For a different set of services, invoke directly from PowerShell:

```powershell
.\Collect-Snapshot.ps1 -OutputPath .\snapshots\before.json -ServiceName Dnscache,W32Time,Spooler
```

Only collect settings on a machine you administer. No unrestricted execution-policy change is needed by the design. If your policy blocks scripts, use your approved signing/deployment process. Collection permissions vary: failed sections remain explicitly uncollected rather than disappearing silently.

## What is captured

| Section | Collected settings | Useful question |
|---|---|---|
| Interfaces | Stable adapter GUID, alias, status, IPv4 address/prefix, default routes and route metrics | Did the address or intended default path change? |
| DNS | Resolver addresses per adapter/address family, in configured order | Did the VPN reorder or replace resolvers? |
| Firewall | Effective profile enabled state from ActiveStore | Did a profile become disabled? |
| Services | State and startup mode for explicitly requested service names | Did a required service stop or change startup mode? |

The collector does not include passwords, environment variables, application data, or a full registry dump. Snapshots still contain sensitive operational details; keep them private.

## Interpret drift carefully

`unchanged` means these successfully collected settings match. It does not mean every setting on the computer is identical.

`drift` means one or more observed settings changed. A DHCP renewal, planned VPN change, adapter removal, or intentionally stopped service can be legitimate. The next step is review, not automatic repair.

`incomplete` means a section could not be collected in either snapshot, or the requested service scope differs. Other successfully collected changes remain visible, but missing data is not labeled as a deletion. Snapshots from different hosts/platforms are rejected.

DNS list order is preserved because reordering may matter. Timestamps and collector error text are contextual evidence, not configuration drift. An added adapter generates one finding rather than a flood of leaf changes.

## Limits and validation

- The Windows collector has not been run on a Windows host in the initial local build. Validate it on a lab endpoint before operational use. Python comparison behavior was tested locally on Linux.
- IPv6 addresses, individual firewall rules, GPO provenance, effective route selection, interface metrics, drivers, installed software, registry settings, and application health are outside the initial collection scope.
- Snapshots are not atomic. Capture during a quiet interval; a rapidly changing endpoint can produce a mixed-time view.
- Interfaces are keyed by GUID. Reinstallation can legitimately create a new GUID. Hostname changes require a new baseline.
- There is no automatic scheduling or baseline approval. Keep a known-good snapshot with its maintenance/change ticket; do not overwrite it blindly.

```sh
python -m unittest discover -s tests -v
```

Tests cover DNS order, timestamp noise, wrong hosts, missing collection coverage, changed service selection, adapter additions, and independent findings. GitHub Actions also parses the PowerShell collector on Windows; parser success is not an on-device collection test.

See [WALKTHROUGH.md](../WALKTHROUGH.md) for a lab and investigation example.

## References

- [Get-NetIPAddress](https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-netipaddress)
- [Get-NetRoute](https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-netroute)
- [Get-DnsClientServerAddress](https://learn.microsoft.com/en-us/powershell/module/dnsclient/get-dnsclientserveraddress)
- [Get-NetFirewallProfile](https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallprofile)
- [Get-CimInstance](https://learn.microsoft.com/en-us/powershell/module/cimcmdlets/get-ciminstance)

MIT licensed. Initial implementation prepared with AI assistance for Raihan Mahmud's learning portfolio. No production adoption or incident resolution is claimed.

