---
name: deploy-gcp
description: Update Cloud Run Jobs after modifying scraper scripts
argument-hint: [job-name|all] [--test]
disable-model-invocation: true
allowed-tools: Bash(gcloud *)
---

# Update Cloud Run Jobs

Rebuild the Docker image and update Cloud Run Job(s) after code modification.

## Workflow

### Single job: `/deploy-gcp [job-name] [--test]`

1. Build and push new image
2. Update the specified job
3. (with `--test`) Execute the job

### All jobs: `/deploy-gcp all [--test]`

1. Build and push new image (once)
2. Update ALL 13 jobs
3. (with `--test`) Execute all jobs in parallel (async)

## All Jobs List (13 total, excluding lifehacker)

| Job Name | Country | Source |
|----------|---------|--------|
| scraper-au-cuponation | AU | cuponation |
| scraper-de-mydealz | DE | mydealz |
| scraper-de-sparwelt | DE | sparwelt |
| scraper-es-chollometro | ES | chollometro |
| scraper-es-cuponation | ES | cuponation |
| scraper-fr-igraal | FR | igraal |
| scraper-fr-mareduc | FR | mareduc |
| scraper-it-codicescontonet | IT | codice-sconto |
| scraper-it-cuponation | IT | cuponation |
| scraper-uk-hotukdeals | UK | hotukdeals |
| scraper-uk-vouchercodes | UK | vouchercodes |
| scraper-us-retailmenot | US | retailmenot |
| scraper-us-simplycodes | US | simplycodes |

## Commands

### Build image (once for all)
```bash
cd c:\Users\nmusicki\Documents\Python_Scripts\scrap_code\Playwright
gcloud builds submit --tag gcr.io/PROJECT_ID/playwright-scrapers:latest .
```

### Update single job
```bash
gcloud run jobs update JOB_NAME \
  --image gcr.io/PROJECT_ID/playwright-scrapers:latest \
  --region europe-west1
```

### Update ALL jobs
```bash
for job in scraper-au-cuponation scraper-de-mydealz scraper-de-sparwelt scraper-es-chollometro scraper-es-cuponation scraper-fr-igraal scraper-fr-mareduc scraper-it-codicescontonet scraper-it-cuponation scraper-uk-hotukdeals scraper-uk-vouchercodes scraper-us-retailmenot scraper-us-simplycodes; do
  gcloud run jobs update $job --image gcr.io/PROJECT_ID/playwright-scrapers:latest --region europe-west1
done
```

### Execute ALL jobs (with --test) - runs in parallel
```bash
for job in scraper-au-cuponation scraper-de-mydealz scraper-de-sparwelt scraper-es-chollometro scraper-es-cuponation scraper-fr-igraal scraper-fr-mareduc scraper-it-codicescontonet scraper-it-cuponation scraper-uk-hotukdeals scraper-uk-vouchercodes scraper-us-retailmenot scraper-us-simplycodes; do
  echo "🚀 Launching $job..."
  gcloud run jobs execute $job --region europe-west1 --async
done
```

## Examples

- `/deploy-gcp scraper-uk-hotukdeals` - Update 1 job
- `/deploy-gcp scraper-uk-hotukdeals --test` - Update + run 1 job
- `/deploy-gcp all` - Update les 13 jobs
- `/deploy-gcp all --test` - Update + run les 13 jobs

## Notes

- `all` exclut lifehacker (non utilisé)
- Une seule image Docker pour tous les jobs
- `--test` lance tous les jobs en parallèle (async) - suivre la progression dans la console GCP
