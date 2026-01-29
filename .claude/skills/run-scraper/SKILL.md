---
name: run-scraper
description: Run a coupon scraper for a specific country and source
argument-hint: [country] [source]
disable-model-invocation: true
allowed-tools: Bash(python *)
---

# Run Coupon Scraper

Execute a Playwright scraper for a specific country and source combination.

## Available Scrapers

| Country | Source | Script |
|---------|--------|--------|
| AU | cuponation | `Playwright/AU/scrap_cuponation_AU.py` |
| AU | lifehacker | `Playwright/AU/scrap_lifehacker_AU.py` |
| DE | mydealz | `Playwright/DE/scrap_mydealz_DE.py` |
| DE | sparwelt | `Playwright/DE/scrap_sparwelt_DE.py` |
| ES | chollometro | `Playwright/ES/scrap_chollometro_ES.py` |
| ES | cuponation | `Playwright/ES/scrap_cuponation_ES.py` |
| FR | igraal | `Playwright/FR/scrap_igraal_FR.py` |
| FR | mareduc | `Playwright/FR/scrap_mareduc_FR.py` |
| IT | codice-sconto | `Playwright/IT/scrap_codicescontonet_IT.py` |
| IT | cuponation | `Playwright/IT/scrap_cuponation_IT.py` |
| UK | hotukdeals | `Playwright/UK/scrap_hotukdeals_UK.py` |
| UK | vouchercodes | `Playwright/UK/scrap_vouchercodes_UK.py` |
| US | retailmenot | `Playwright/US/scrap_retailmenot_US.py` |
| US | simplycodes | `Playwright/US/scrap_simplycodes_US.py` |

## Usage

When invoked with `/run-scraper [country] [source]`:

1. Parse the arguments: `$ARGUMENTS`
2. Find the matching script from the table above
3. Run the script with Python:
   ```bash
   cd c:\Users\nmusicki\Documents\Python_Scripts\scrap_code\Playwright && python [script_path]
   ```

## Examples

- `/run-scraper UK vouchercodes` - Run VoucherCodes UK scraper
- `/run-scraper FR mareduc` - Run Ma-Reduc France scraper
- `/run-scraper US` - List all US scrapers available

## Notes

- Scripts read URLs from Google Sheets and write results back
- Requires valid credentials in `Playwright/credentials/`
- Some scrapers (VoucherCodes UK) may be blocked by Cloudflare on GCP
