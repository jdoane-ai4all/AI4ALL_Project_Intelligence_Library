PY := PYTHONPATH=src python3
.PHONY: all ingest fetch build resolve linkcheck similarity export report test app-test
all: ingest build resolve linkcheck build similarity export report review
ingest:      ; $(PY) -m aipil.cli ingest
fetch:       ; $(PY) -m aipil.cli fetch
validate:    ; $(PY) -m aipil.extraction.schema all
resolve:     ; $(PY) -m aipil.datasets.resolve_urls
linkcheck:   ; $(PY) -m aipil.datasets.linkcheck
build:       ; $(PY) -m aipil.cli build
similarity:  ; $(PY) -m aipil.embeddings.similarity
export:      ; $(PY) -m aipil.export.exports
report:      ; $(PY) -m aipil.analysis.report
test:        ; python3 -m pytest -q
app-test:    ; cd app && npx vitest run
redact-images: ; $(PY) -m aipil.sources.redact_images
review:      ; $(PY) -m aipil.export.review_workbook
backup:      ; scripts/private_data.sh backup
restore:     ; scripts/private_data.sh restore
