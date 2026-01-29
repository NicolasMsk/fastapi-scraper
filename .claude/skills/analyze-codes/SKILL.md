---
name: analyze-codes
description: Analyze scraped coupon codes with LLM to rewrite titles and extract affiliate networks. Use when the user wants to process codes, rewrite titles, or extract networks from affiliate links.
argument-hint: [batch_size] [countries]
disable-model-invocation: true
allowed-tools: Bash(python *)
---

# Analyze Coupon Codes with LLM

Run the code analyzer to process scraped coupon codes:
- Rewrites titles following marketing guidelines
- Extracts affiliate network from URLs (Awin, CJ, Rakuten, etc.)
- Updates Google Sheets with results

## Usage

```bash
cd c:\Users\nmusicki\Documents\Python_Scripts\scrap_code\Playwright && python code_analyzer.py [batch_size] [countries]
```

## Arguments

- `batch_size` (optional): Number of codes to process per batch (default: 100)
- `countries` (optional): Comma-separated list of countries (e.g., UK,US,FR)

## Examples

- `/analyze-codes` - Process 100 codes from all countries
- `/analyze-codes 50` - Process 50 codes from all countries
- `/analyze-codes 100 UK,FR` - Process 100 codes from UK and France only

## What it does

1. Connects to Google Sheets (Missing_Deals_Coupons spreadsheet)
2. Finds codes without `Rewritten_Title`
3. Sends batch to GPT-4o-mini for:
   - Title rewriting (in the appropriate language)
   - Network extraction from affiliate URL
4. Updates the sheet with results

## Requirements

- `OPENAI_API_KEY` environment variable must be set
- Valid Google Sheets credentials in `Playwright/credentials/`
