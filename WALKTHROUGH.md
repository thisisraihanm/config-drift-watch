# Learn and demonstrate it

## A 20-minute offline lab

1. Run the demo. Find the reordered DNS list, stopped service, and firewall change in the evidence.
2. Copy `examples/before.json` and `examples/after.json` into the ignored `snapshots` folder. Keep the example originals intact.
3. Edit only the timestamp in the copied baseline, then compare identical settings: no drift should appear.
4. In a copied snapshot, set DNS coverage to `error` and remove the DNS object. The report must say `incomplete`, not that every DNS setting was removed.
5. Change the requested service list in one copy. Explain why different collection scope cannot prove a service disappeared.
6. On an authorized Windows lab, collect twice without intentionally modifying any settings. Review any changes caused by ordinary endpoint activity.

Do not disable a real firewall or stop a production service to create a demonstration. The fictional JSON exercises the same comparison logic without operational risk.

## Read the implementation in this order

`Collect-Snapshot.ps1` collects four sections independently and records coverage. `validate()` checks identity/schema/scope. `flatten()` keeps ordered lists intact. `compare()` compares only sections observed in both captures. `finding()` turns differences into review steps without pretending to know the cause.

## Explain your work honestly

“I worked on a before/after configuration report for Windows troubleshooting. It tracks selected network, DNS, firewall-profile, and service settings, and avoids treating collection failures as deleted configuration. I tested the comparison on synthetic snapshots. On-device Windows collection needs a lab check.”

Replace the last sentence only after you have performed that check and retained redacted evidence.

## A useful next contribution

Extend the snapshot to track interface metrics and DHCP mode, with a schema change and a fictional regression case. Do not turn drift into automatic repair: the intended configuration still needs an owner and approved baseline.
