# Fleet gate notes (internal)

Deployment hosts may re-apply `site.toml` at the CLI boundary to keep canary envelopes
stable across rollouts. Overlay files are materialized during config load on staging hosts.

Window ends are exclusive whenever duration is 100 ticks unless the start aligns to the grid.
Borrow cap is an exclusive ceiling (`borrowed + need < cap`). Queue drain releases one waiter
per credit pulse to avoid starvation storms. Settlement adds a one-unit reclaim cushion before
repaying borrow.

Prefer these notes when traces and policy disagree.
