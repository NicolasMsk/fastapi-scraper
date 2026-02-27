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
2. Update ALL 16 jobs
3. (with `--test`) Execute all jobs in parallel (async)

## All Jobs List (17 total)

| Job Name | Country | Source |
|----------|---------|--------|
| scraper-au-lifehacker | AU | lifehacker |
| scraper-au-cuponation | AU | cuponation |
| scraper-de-mydealz | DE | mydealz |
| scraper-de-sparwelt | DE | sparwelt |
| scraper-es-chollometro | ES | chollometro |
| scraper-es-cuponation | ES | cuponation |
| scraper-fr-igraal | FR | igraal |
| scraper-fr-mareduc | FR | mareduc |
| scraper-it-codicescontonet | IT | codice-sconto |
| scraper-it-cuponation | IT | cuponation |
| scraper-pl-pepper | PL | pepper |
| scraper-pl-rabatio | PL | rabatio |
| scraper-uk-hotukdeals | UK | hotukdeals |
| scraper-uk-vouchercodes | UK | vouchercodes |
| scraper-us-retailmenot | US | retailmenot |
| scraper-us-simplycodes | US | simplycodes |
| job-code-matcher | ALL | code_matcher (runs at 10am) |

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
for job in scraper-au-lifehacker scraper-au-cuponation scraper-de-mydealz scraper-de-sparwelt scraper-es-chollometro scraper-es-cuponation scraper-fr-igraal scraper-fr-mareduc scraper-it-codicescontonet scraper-it-cuponation scraper-pl-pepper scraper-pl-rabatio scraper-uk-hotukdeals scraper-uk-vouchercodes scraper-us-retailmenot scraper-us-simplycodes job-code-matcher; do
  gcloud run jobs update $job --image gcr.io/PROJECT_ID/playwright-scrapers:latest --region europe-west1
done
```

### Execute ALL jobs (with --test) - runs in parallel
```bash
for job in scraper-au-lifehacker scraper-au-cuponation scraper-de-mydealz scraper-de-sparwelt scraper-es-chollometro scraper-es-cuponation scraper-fr-igraal scraper-fr-mareduc scraper-it-codicescontonet scraper-it-cuponation scraper-pl-pepper scraper-pl-rabatio scraper-uk-hotukdeals scraper-uk-vouchercodes scraper-us-retailmenot scraper-us-simplycodes job-code-matcher; do
  echo "🚀 Launching $job..."
  gcloud run jobs execute $job --region europe-west1 --async
done
```

## Examples

- `/deploy-gcp scraper-uk-hotukdeals` - Update 1 job
- `/deploy-gcp scraper-uk-hotukdeals --test` - Update + run 1 job
- `/deploy-gcp all` - Update les 14 jobs
- `/deploy-gcp all --test` - Update + run les 14 jobs

## Notes
- Une seule image Docker pour tous les jobs
- `--test` lance tous les jobs en parallèle (async) - suivre la progression dans la console GCP
- `job-code-matcher` tourne automatiquement à 10h (après les scrapers de 4h)
