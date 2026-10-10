# Omada Traffic for Home Assistant

A Home Assistant custom integration that shows where your internet allowance goes.
It reads a TP-Link Omada controller every 30 seconds, records usage per device and per
internet line in its own small database, and adds a **Traffic** page to the sidebar.

- **Summary:** current download and upload, today's usage, and a card per internet plan
  with allowance, cycle dates, projection and what is left.
- **Bandwidth:** live charts over 1 hour to 7 days, with per-person and per-type rankings.
- **Usage:** hourly or daily bars over 6 hours to 30 days or the plan cycle.
- **Usage-by table:** by device, person or type, sortable, with sparklines.
- **Devices:** assign each device to a person, rename it and set its type from the page.
  Manufacturer names come from the bundled public IEEE registry.
- **Private Wi-Fi addresses:** phones and laptops that rotate their MAC address are
  recognised by the name they announce on the network and kept as one device.
- **Notifications:** "What device is this?" when something unidentified joins.
- **Sensors:** download rate, upload rate, used today, used this plan period.

The integration is **read-only** towards the controller: it logs in and issues GET
requests. It never blocks clients or changes a setting.

> **Unofficial.** This uses the controller's private web API, the same one the Omada
> web page uses. TP-Link can change it in any controller update. Developed against a
> hardware controller (OC200) running controller version 6.3 with an ER605 gateway.
> Not affiliated with TP-Link.

## Install

With [HACS](https://hacs.xyz): HACS › ⋮ › Custom repositories › add this repository as an
*Integration*, install **Omada Traffic**, and restart Home Assistant.

By hand: copy `custom_components/omada_traffic` into your Home Assistant
`config/custom_components/` folder and restart.

## Set up

Settings › Devices & services › Add integration › **Omada Traffic**, then enter:

- the controller address, for example `https://192.168.0.2` (add `:8043` for a software controller),
- a controller username and password. Create a dedicated **viewer** account for this;
- whether to check the controller's certificate (leave off for the built-in self-signed one).

If the account can see several sites you are asked which one to use.

Then open the integration's **Configure** screen to:

- **add your internet plans:** name, monthly allowance, renewal day and the gateway WAN
  port the plan is on. With a WAN port chosen, the plan counts true internet traffic on
  that line; without one it adds up the devices. If recording starts part-way through a
  billing cycle you can enter your provider's reading as a starting point;
- **list the people in the household;**
- **choose when the day starts** (midnight or 6 AM).

## Assigning devices

On the Traffic page, right-click a device row (or click it, or use ⋯ on a touch screen)
to assign it to a person, rename it or change its type. Clicking a person or type in a
ranking filters the whole page. Only Home Assistant administrators can make changes.

Photos come from Home Assistant's own People: a person whose name matches gets their
picture.

## Where your data lives

Nothing personal is stored in the integration's files.

| What | Where |
|---|---|
| Controller address and login | Home Assistant config entry (`.storage/core.config_entries`) |
| People, plans, device owners, names and types | `.storage/omada_traffic` |
| Usage history | `config/omada_traffic/traffic.db` (SQLite) |

Include those in your Home Assistant backups.

## How counting works

- Each poll reads every connected client's running download and upload totals. The
  difference since the last poll is spread over the minutes it covers.
- Counters that go backwards are treated as a reconnect. Jumps above 2 Gbit/s are
  discarded as glitches.
- Per-device figures come from access point and switch counters, so they include
  traffic between devices on your own network. Per-line plan figures come from the
  gateway's WAN ports and are internet traffic only.
- Kept: per-minute data for 48 hours, 5-minute data for 35 days, hourly data forever
  (roughly 35 MB a year for 40 devices).

## Private (rotating) Wi-Fi addresses

Apple and other devices can change their Wi-Fi MAC address, which makes the controller
see a new device. The integration asks private-address devices for their own name over
mDNS (for example "Sams-iPhone"). When a new private address announces the same name as
one that is no longer connected, its history is merged into the older one. Two connected
devices with the same name are left alone. A name never decides who owns a device.

## Limits

- No per-app or per-site breakdown: that needs deep packet inspection on the gateway.
- One controller site per Home Assistant.
- The setup screen has been tested less than the rest; please open an issue if it fails
  on your controller version.

## Development

`tools/build_oui.py` rebuilds the bundled manufacturer table from the IEEE registry.

API (requires Home Assistant auth): `/api/omada_traffic/meta`, `summary`,
`bandwidth?window=1h|6h|24h|7d&filter=&end=`, `usage?window=6h|24h|7d|14d|30d|plan&filter=`,
`table?by=device|person|type&window=`. Filters: `house`, `type:<Type>`, `person:<Name>`,
`device:<MAC>`.

## Licence

MIT. The bundled `oui.tsv` is derived from the public IEEE MA-L registry.
