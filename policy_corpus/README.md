# Northstar Technologies Policy Corpus V1.0

This package contains 12 coherent, synthetic HR policy and procedure documents for the **PeopleOps Assistant** agentic RAG project.

## Important

- Northstar Technologies Inc. is fictional.
- All examples, addresses, employee concepts, and operational records are synthetic.
- The policies are designed for educational system testing and are not legal advice.
- The authoritative ingestion folder is **`runtime_corpus/`**.
- Do **not** ingest `master_markdown/`, `review_pdfs/`, or the combined handbook together with `runtime_corpus/`; doing so would duplicate policy content and distort retrieval.

## Folder structure

- `runtime_corpus/`: 12 unique policy sources used by the RAG application. It intentionally contains 10 Markdown files and 2 PDF files to exercise two parser types.
- `master_markdown/`: editable Markdown source for all 12 policies.
- `review_pdfs/`: human-review PDF rendering of all 12 policies; not intended for indexing.
- `corpus_docs/`: manifest, consistency matrix, glossary, and validation report.
- `Northstar_Policy_Handbook_V1.0.pdf`: combined human-review handbook; not intended for indexing.

## Shared policy assumptions

- Effective date: 2026-09-01
- Review date: 2027-09-01
- Regular Full-Time (RFT): normally 30 or more scheduled hours per week.
- Regular Part-Time (RPT): normally 20-29 scheduled hours per week.
- Registered Home Office: office/jurisdiction stored in the HR system.
- Business day: Monday-Friday excluding the employee's assigned company holiday.
- Applicable law, formal benefit plan documents, and signed employment agreements take precedence when they provide a different or greater right.

## Recommended RAG metadata

Preserve `policy_id`, `policy_title`, `version`, `effective_date`, heading/section ID, source filename, page where available, and a supporting snippet. The section identifiers embedded in headings, such as `PTO-6` or `INT-5`, are stable citation anchors.
