# Pho65 inventory known-answer fixture

All names and codes here are fictional class data. The `PHO65-INV-*` values are internal codes, not UPC/EAN identifiers.

| Item | Code | Base unit | Reorder point |
|---|---|---:|---:|
| Rice noodles | `PHO65-INV-000101` | bag | 8 |
| Oat milk | `PHO65-INV-000102` | carton | 4 |

## Cost known answer

For one fictional item, record these three events in order:

1. Received `10` bags at `$2.00` each.
2. Received `10` bags at `$2.50` each.
3. Used `12` bags.

Expected result: `8` bags remain; moving weighted-average cost is `$2.25` per bag; inventory value is `$18.00`. Use a unique button press/request ID for every event; retrying a single submission must not produce a fourth event.

