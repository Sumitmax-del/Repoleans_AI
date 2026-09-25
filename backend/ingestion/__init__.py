# Repository ingestion pipeline.
#
# Modules
# -------
# models.py    — shared Pydantic types (IngestionRecord, FileNode, ScanResult, …)
# validator.py — GitHub URL validation
# cloner.py    — shallow git clone + work-directory management
# scanner.py   — file-system walk, language detection, dependency extraction
# metadata.py  — GitHub REST API metadata fetch (unauthenticated, best-effort)
# pipeline.py  — orchestrator that runs all stages in order
