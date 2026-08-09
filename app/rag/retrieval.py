from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable

from app.rag.embeddings import LocalHashEmbedding, cosine_similarity, tokenize
from app.rag.index import HybridIndex
from app.rag.models import QueryPlan, RetrievalResult, SearchHit

MINIMUM_HYBRID_SCORE = 0.16

POLICY_INTENT_TERMS = frozenset(
    {
        "approval",
        "benefit",
        "benefits",
        "case",
        "conduct",
        "employee",
        "equipment",
        "expense",
        "harassment",
        "home-office",
        "hr",
        "international",
        "leave",
        "manager",
        "onboarding",
        "policy",
        "pto",
        "remote",
        "report",
        "security",
        "work",
        "workplace",
    }
)


def plan_query(query: str) -> QueryPlan:
    normalized = query.casefold()
    if "ticket" in normalized and any(
        term in normalized for term in ("create", "prepare", "urgent", "confirm")
    ):
        required = {"POL-HRC-001"}
        facets = [
            query,
            "HR case minimum intake information affected employee summary category priority",
            "confirmation before a mock action explicit confirmation preview ticket",
        ]
        if "harassment" in normalized:
            required.add("POL-CON-001")
            facets.append("workplace concern reporting channels harassment")
        return QueryPlan(
            query=query,
            facets=tuple(facets),
            required_policy_ids=frozenset(required),
            evidence_rule="confirmation_gated_hr_case",
        )
    if "harassment" in normalized or (
        "manager" in normalized and "report" in normalized
    ):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "reporting channels concern raised manager People Operations case portal "
                "Ethics confidentiality anonymous",
                "manager duty to escalate reported concern",
                "HR case intake channels report concern",
                "HR case triage and assignment manager escalation",
            ),
            required_policy_ids=frozenset({"POL-CON-001", "POL-HRC-001"}),
            evidence_rule="conduct_case_routing",
        )
    if all(term in normalized for term in ("employee", "pto", "benefit")) and any(
        term in normalized for term in ("medical", "history", "choices", "show")
    ):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "workplace confidentiality privacy employee records need to know",
                "benefits privacy access minimum necessary employee information",
            ),
            required_policy_ids=frozenset({"POL-CON-001", "POL-BEN-001"}),
            evidence_rule="employee_record_privacy",
        )
    if "leave" in normalized and any(
        term in normalized for term in ("benefit", "pto", "accrual", "medical")
    ):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "benefits during leave continuation premiums coverage",
                "leave pay PTO accrual and benefits during long leave",
            ),
            required_policy_ids=frozenset({"POL-BEN-001", "POL-LEV-001"}),
            evidence_rule="leave_benefits",
        )
    if "leave" in normalized and any(
        term in normalized for term in ("family", "caregiving", "parental", "file")
    ):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "family caregiving parental statutory leave",
                "leave request and notification process what information to file",
            ),
            required_policy_ids=frozenset({"POL-LEV-001"}),
            evidence_rule="family_leave_clarification",
        )
    if any(term in normalized for term in ("chair", "furniture", "home-office")) and any(
        term in normalized for term in ("reimburse", "limit", "eligible", "cad")
    ):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "home-office furniture reimbursement allowance chair normal limit",
                "expense approval thresholds high value director finance approval",
                "business expense home-office equipment connectivity reimbursement",
            ),
            required_policy_ids=frozenset({"POL-EQP-001", "POL-EXP-001"}),
            evidence_rule="equipment_expense",
        )
    if "holiday" in normalized and any(term in normalized for term in ("pto", "leave")):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "PTO rules company holidays not deducted from scheduled time off",
                "company holiday during PTO or leave pay treatment",
            ),
            required_policy_ids=frozenset({"POL-PTO-001", "POL-HOL-001"}),
            evidence_rule="holiday_during_pto",
        )
    if "floating holiday" in normalized:
        return QueryPlan(
            query=query,
            facets=(query, "floating holiday carry over expires calendar year"),
            required_policy_ids=frozenset({"POL-HOL-001"}),
            evidence_rule="floating_holiday",
        )
    international_terms = (
        "international",
        "abroad",
        "another country",
        "outside canada",
        "outside the country",
        "germany",
        "spain",
        "uk ",
        "united kingdom",
    )
    remote_terms = ("remote", "work from", "working from", "work abroad")
    if any(term in normalized for term in ("overseas", "abroad", "international")) and any(
        term in normalized for term in ("a while", "some time", "unsure", "not sure")
    ):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "international work required request information destination dates business days",
            ),
            required_policy_ids=frozenset({"POL-INT-001"}),
            evidence_rule="international_request_clarification",
        )
    if any(term in normalized for term in international_terms) and any(
        term in normalized for term in remote_terms
    ):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "approved work location outside registered province country before travel",
                "international work duration category notice approvals decision path six weeks",
                "six weeks Germany international exceptional approvals conditions",
                "international mobile work security company-managed device VPN restricted data",
            ),
            required_policy_ids=frozenset({"POL-INT-001", "POL-RWK-001", "POL-SEC-001"}),
            evidence_rule="international_remote_work_three_policy",
        )
    if any(term in normalized for term in ("pto", "vacation", "time off", "week off")):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "paid time off eligibility balance",
                "PTO notice request process scheduled workdays",
                "PTO manager approval criteria scheduling conflicts",
                "holiday calendar scheduled working days",
            ),
            required_policy_ids=frozenset({"POL-PTO-001"}),
            evidence_rule="pto_policy",
        )
    if any(term in normalized for term in ("expense", "reimburse", "receipt", "meal")):
        return QueryPlan(
            query=query,
            facets=(query, "business expenses reimbursement receipt preapproval"),
            required_policy_ids=frozenset({"POL-EXP-001"}),
            evidence_rule="expense_policy",
        )
    if any(term in normalized for term in ("benefit", "insurance", "enrollment")):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "employee benefits general eligibility matrix employment category",
                "benefits coverage start waiting period",
                "benefits enrollment window newly eligible deadline",
                "benefits privacy access enrollment status",
            ),
            required_policy_ids=frozenset({"POL-BEN-001"}),
            evidence_rule="benefits_policy",
        )
    if any(term in normalized for term in ("onboarding", "new employee", "first week")):
        return QueryPlan(
            query=query,
            facets=(
                query,
                "new employee day one requirements",
                "onboarding required training deadlines account security phishing",
                "onboarding first-week integration items",
            ),
            required_policy_ids=frozenset({"POL-ONB-001"}),
            evidence_rule="onboarding_policy",
        )
    if any(
        term in normalized
        for term in ("credential", "security incident", "accidental disclosure", "phishing")
    ):
        return QueryPlan(
            query=query,
            facets=(query, "security incidents credential compromise immediate reporting"),
            required_policy_ids=frozenset({"POL-SEC-001"}),
            evidence_rule="security_incident",
        )
    if "holiday" in normalized:
        return QueryPlan(
            query=query,
            facets=(query, "holiday calendar floating holiday observance office closure"),
            required_policy_ids=frozenset({"POL-HOL-001"}),
            evidence_rule="holiday_policy",
        )
    if any(term in normalized for term in ("equipment", "laptop", "computer")):
        return QueryPlan(
            query=query,
            facets=(query, "company equipment approved procurement ownership home office"),
            required_policy_ids=frozenset({"POL-EQP-001"}),
            evidence_rule="equipment_policy",
        )
    if "leave" in normalized:
        return QueryPlan(
            query=query,
            facets=(query, "statutory medical personal leave request notification"),
            required_policy_ids=frozenset({"POL-LEV-001"}),
            evidence_rule="leave_policy",
        )
    return QueryPlan(
        query=query,
        facets=(query,),
        required_policy_ids=frozenset(),
        evidence_rule="general_policy",
    )


def _bm25_scores(query_tokens: list[str], documents: list[list[str]]) -> list[float]:
    if not query_tokens or not documents:
        return [0.0] * len(documents)
    document_frequency: Counter[str] = Counter()
    frequencies = []
    for tokens in documents:
        frequency = Counter(tokens)
        frequencies.append(frequency)
        document_frequency.update(frequency.keys())
    average_length = sum(len(tokens) for tokens in documents) / len(documents)
    k1 = 1.5
    b = 0.75
    scores = []
    for tokens, frequency in zip(documents, frequencies, strict=True):
        score = 0.0
        length_normalizer = k1 * (1 - b + b * len(tokens) / max(average_length, 1))
        for term in set(query_tokens):
            term_frequency = frequency.get(term, 0)
            if not term_frequency:
                continue
            document_count = len(documents)
            inverse_frequency = math.log(
                1 + (document_count - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            score += inverse_frequency * (
                term_frequency * (k1 + 1) / (term_frequency + length_normalizer)
            )
        scores.append(score)
    return scores


def _normalize(scores: Iterable[float]) -> list[float]:
    values = list(scores)
    maximum = max(values, default=0.0)
    if maximum <= 0:
        return [0.0] * len(values)
    return [value / maximum for value in values]


class HybridRetriever:
    def __init__(self, index: HybridIndex) -> None:
        self.index = index
        self.embedding_model = LocalHashEmbedding(index.embedding_dimensions)
        self.document_tokens = [
            tokenize(
                " ".join(
                    (
                        item.chunk.policy_title,
                        item.chunk.section_title,
                        item.chunk.applicability,
                        item.chunk.text,
                    )
                )
            )
            for item in index.indexed_chunks
        ]

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        mode: str = "hybrid",
        policy_ids: set[str] | None = None,
        source_formats: set[str] | None = None,
    ) -> RetrievalResult:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        if mode not in {"hybrid", "dense", "keyword"}:
            raise ValueError("mode must be hybrid, dense, or keyword")

        if not POLICY_INTENT_TERMS.intersection(tokenize(query)):
            return RetrievalResult(
                query=query,
                mode=f"phase5_{mode}",
                hits=(),
                sufficient_evidence=False,
                evidence_rule="out_of_scope",
                missing_policy_ids=(),
                conflicts=(),
                limitation="The question has no supported People Operations policy intent.",
            )

        plan = plan_query(query)
        aggregate: dict[int, dict[str, object]] = {}
        facet_scores_by_chunk: dict[str, dict[str, float]] = defaultdict(dict)
        for facet_number, facet in enumerate(plan.facets, start=1):
            keyword_raw = _bm25_scores(tokenize(facet), self.document_tokens)
            keyword_scores = _normalize(keyword_raw)
            query_embedding = self.embedding_model.embed(facet)
            dense_scores = [
                max(0.0, cosine_similarity(query_embedding, item.embedding))
                for item in self.index.indexed_chunks
            ]
            for index, item in enumerate(self.index.indexed_chunks):
                chunk = item.chunk
                if policy_ids and chunk.policy_id not in policy_ids:
                    continue
                if source_formats and chunk.source_format not in source_formats:
                    continue
                keyword = keyword_scores[index]
                dense = dense_scores[index]
                if mode == "hybrid":
                    score = 0.62 * keyword + 0.38 * dense
                elif mode == "dense":
                    score = dense
                else:
                    score = keyword
                existing = aggregate.setdefault(
                    index,
                    {
                        "score": 0.0,
                        "keyword": 0.0,
                        "dense": 0.0,
                        "facets": set(),
                    },
                )
                rank_bonus = 0.02 / facet_number
                existing["score"] = max(float(existing["score"]), score + rank_bonus)
                existing["keyword"] = max(float(existing["keyword"]), keyword)
                existing["dense"] = max(float(existing["dense"]), dense)
                facet_scores_by_chunk[chunk.chunk_id][facet] = score
                if score >= MINIMUM_HYBRID_SCORE:
                    facets = existing["facets"]
                    assert isinstance(facets, set)
                    facets.add(facet)

        ranked: list[SearchHit] = []
        for chunk_index, score_data in aggregate.items():
            score = float(score_data["score"])
            if score < MINIMUM_HYBRID_SCORE:
                continue
            facets = score_data["facets"]
            assert isinstance(facets, set)
            ranked.append(
                SearchHit(
                    chunk=self.index.indexed_chunks[chunk_index].chunk,
                    score=round(min(score, 1.0), 6),
                    keyword_score=round(float(score_data["keyword"]), 6),
                    embedding_score=round(float(score_data["dense"]), 6),
                    matched_facets=tuple(sorted(str(facet) for facet in facets)),
                )
            )
        ranked.sort(key=lambda hit: (-hit.score, hit.chunk.chunk_id))

        deduplicated: list[SearchHit] = []
        seen_sections: set[tuple[str, str]] = set()
        for hit in ranked:
            section_key = (hit.chunk.policy_id, hit.chunk.section_id)
            if section_key in seen_sections:
                continue
            seen_sections.add(section_key)
            deduplicated.append(hit)

        selected: list[SearchHit] = []
        selected_sections: set[tuple[str, str]] = set()
        for required_policy in sorted(plan.required_policy_ids):
            best = next(
                (hit for hit in deduplicated if hit.chunk.policy_id == required_policy),
                None,
            )
            if best is not None:
                selected.append(best)
                selected_sections.add((best.chunk.policy_id, best.chunk.section_id))
        for facet in plan.facets[1:]:
            if len(selected) >= top_k:
                break
            best = max(
                deduplicated,
                key=lambda hit: facet_scores_by_chunk[hit.chunk.chunk_id].get(facet, 0.0),
                default=None,
            )
            if best is None:
                continue
            facet_score = facet_scores_by_chunk[best.chunk.chunk_id].get(facet, 0.0)
            key = (best.chunk.policy_id, best.chunk.section_id)
            if facet_score >= MINIMUM_HYBRID_SCORE and key not in selected_sections:
                selected.append(best)
                selected_sections.add(key)
        for hit in deduplicated:
            key = (hit.chunk.policy_id, hit.chunk.section_id)
            if key not in selected_sections:
                selected.append(hit)
                selected_sections.add(key)
            if len(selected) >= top_k:
                break
        selected = selected[:top_k]

        retrieved_policies = {hit.chunk.policy_id for hit in selected}
        missing = tuple(sorted(plan.required_policy_ids - retrieved_policies))
        conflicts = detect_index_conflicts(hit.chunk for hit in ranked)
        sufficient = bool(selected) and not missing and not conflicts
        if not plan.required_policy_ids:
            sufficient = bool(selected and selected[0].score >= 0.24) and not conflicts
        limitation = (
            "Evidence is sufficient for grounded guidance."
            if sufficient
            else _limitation(missing, conflicts)
        )
        return RetrievalResult(
            query=query,
            mode=f"phase5_{mode}",
            hits=tuple(selected),
            sufficient_evidence=sufficient,
            evidence_rule=plan.evidence_rule,
            missing_policy_ids=missing,
            conflicts=conflicts,
            limitation=limitation,
        )


def detect_index_conflicts(chunks: Iterable[object]) -> tuple[str, ...]:
    versions: dict[str, set[str]] = defaultdict(set)
    chunk_text: dict[str, set[str]] = defaultdict(set)
    for item in chunks:
        policy_id = str(item.policy_id)
        versions[policy_id].add(str(item.version))
        normalized_text = " ".join(str(item.text).casefold().split())
        chunk_text[str(item.chunk_id)].add(normalized_text)
    conflicts = [
        f"{policy_id} has multiple retrieved versions: {sorted(values)}"
        for policy_id, values in versions.items()
        if len(values) > 1
    ]
    conflicts.extend(
        f"{chunk_id} has inconsistent authoritative text"
        for chunk_id, values in chunk_text.items()
        if len(values) > 1
    )
    return tuple(sorted(conflicts))


def _limitation(missing: tuple[str, ...], conflicts: tuple[str, ...]) -> str:
    if conflicts:
        return "Conflicting policy evidence requires People Operations review: " + "; ".join(
            conflicts
        )
    if missing:
        return "Required policy coverage is missing: " + ", ".join(missing)
    return "The available policy evidence is below the grounded-answer threshold."
