# ruff: noqa
# ruff: noqa: I001
from __future__ import annotations
import hashlib,json,os,time
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any
from ayorai_attractor.evaluation.stats import balanced_accuracy,bootstrap_accuracy,confusion_matrix,mcnemar_exact_pvalue
from ayorai_attractor.models import SearchRequest
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.base import Provider,ProviderResponse
from ayorai_attractor.verification.claim_pipeline import ClaimVerificationPipeline,RuleScopeClassifier
from ayorai_attractor.verification.extraction import RetrievedDocument
from ayorai_attractor.verification.stance import RuleStanceDetector

class FixtureSearchProvider(Provider):
    id="fixture-golden-v0"; capabilities=frozenset({"search","research","evidence"})
    def __init__(self,documents:dict[str,dict[str,Any]],evidence_pool:list[str])->None:self.documents,self.evidence_pool=documents,evidence_pool
    def execute(self,prompt:str)->ProviderResponse:
        del prompt
        selected=[self.documents[x] for x in self.evidence_pool]
        text="\n\n".join(str(x["content"]) for x in selected); ids=",".join(str(x["doc_id"]) for x in selected)
        return ProviderResponse(text=text,source=f"fixture://golden-v0/{ids or 'empty'}",excerpt=text,independent=bool(selected))

class FixtureRetriever:
    def __init__(self,documents:dict[str,dict[str,Any]],evidence_pool:list[str])->None:self.documents,self.evidence_pool=documents,evidence_pool
    def retrieve(self,query:str)->list[RetrievedDocument]:
        del query; output=[]
        from datetime import datetime
        for doc_id in self.evidence_pool:
            item=self.documents[doc_id]; content=str(item["content"])
            output.append(RetrievedDocument(id=doc_id,content=content,source_id=doc_id,source_location=str(item["url"]),retrieved_at=datetime.fromisoformat(str(item.get("retrieved_at","2026-09-30T12:00:00+00:00")).replace("Z","+00:00")),end_offset=len(content),origin_id=str(item["origin_id"]),canonical_url=str(item["url"])))
        return output

def _load_jsonl(path:Path)->list[dict[str,Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def _accuracy(correct:int,total:int)->dict[str,float|int]:
    return {"correct":correct,"total":total,"accuracy":round(correct/total,6) if total else 0.0}

def _content_digest(report:dict[str,Any])->str:
    stable={k:v for k,v in report.items() if k not in {"latency_ms","git_sha","content_sha256"}}
    return hashlib.sha256(json.dumps(stable,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def _legacy_prediction(case:dict[str,Any],documents:dict[str,dict[str,Any]])->str:
    provider=FixtureSearchProvider(documents,[str(x) for x in case.get("evidence_pool",[])])
    response=Attractor(search_provider=provider).run(SearchRequest(query=str(case["query"]),max_agents=5))
    return response.verification.value.upper()

def evaluate_golden_v0(golden_path:Path,corpus_path:Path,suite:str="golden-v0")->dict[str,Any]:
    cases=_load_jsonl(golden_path); corpus=_load_jsonl(corpus_path)
    if suite=="smoke-v0":
        wanted={"factual","conflict","injection","no-answer","out-of-scope"}
        cases=[next(c for c in cases if c.get("category")==category) for category in sorted(wanted)]
    elif suite!="golden-v0": raise ValueError(f"Unsupported suite: {suite}")
    documents={str(x["doc_id"]):x for x in corpus}
    scope=RuleScopeClassifier(("medical diagnosis","diagnóstico","legal strategy","estratégia jurídica"))
    pipeline=ClaimVerificationPipeline(RuleStanceDetector(),scope_classifier=scope)
    expected=[]; predicted=[]; legacy=[]; results=[]; abstain_expected=[]; abstain_actual=[]; latencies=[]
    category_totals=Counter(); category_correct=Counter(); state_totals=Counter(); state_correct=Counter()
    for case in cases:
        claims=[str(item["text"]) for item in case.get("expected_claims",[])]
        if not claims: claims=[str(case["query"])]
        docs=FixtureRetriever(documents,[str(x) for x in case.get("evidence_pool",[])]).retrieve(str(case["query"]))
        started=time.perf_counter(); result=pipeline.verify(claims,docs); latency=(time.perf_counter()-started)*1000; latencies.append(latency)
        actual_status=result.status.value.upper(); expected_status=case.get("response_status")
        if expected_status is not None:
            abstain_expected.append(str(expected_status).upper()); abstain_actual.append(actual_status)
        item={"id":str(case["id"]),"category":str(case["category"]),"expected":case.get("global"),"predicted":result.verdict.value.upper() if result.verdict else None,"response_status":actual_status,"expected_response_status":expected_status,"correct":False,"latency_ms":round(latency,3)}
        if "global" in case:
            gold=str(case["global"]).upper(); guess=item["predicted"]; correct=gold==guess; item["correct"]=correct
            expected.append(gold); predicted.append(guess); legacy.append(_legacy_prediction(case,documents))
            category=str(case["category"]); category_totals[category]+=1; state_totals[gold]+=1
            if correct: category_correct[category]+=1; state_correct[gold]+=1
        elif expected_status is not None:
            item["correct"]=str(expected_status).upper()==actual_status
        results.append(item)
    majority=Counter(expected).most_common(1)[0]
    bacc=balanced_accuracy(expected,predicted)
    boot=bootstrap_accuracy(expected,predicted,iterations=10000,seed=20261003)
    report={
        "suite":suite,"system":"claim-verification-pipeline","network":False,
        "case_count":len(cases),"corpus_document_count":len(corpus),"cases_with_global_verdict":len(expected),
        "majority_class_baseline":{"label":majority[0],**_accuracy(majority[1],len(expected))},
        "global_accuracy":_accuracy(sum(x==y for x,y in zip(expected,predicted,strict=True)),len(expected)),
        "balanced_accuracy":round(bacc,6),"bootstrap_95_ci":{"lower":boot[0],"upper":boot[1],"iterations":10000,"seed":20261003},
        "confusion_matrix":confusion_matrix(expected,predicted),
        "legacy_accuracy":_accuracy(sum(x==y for x,y in zip(expected,legacy,strict=True)),len(expected)),
        "mcnemar_vs_legacy":{"legacy_correct_new_wrong":sum(g==a and g!=b for g,a,b in zip(expected,legacy,predicted,strict=True)),"new_correct_legacy_wrong":sum(g!=a and g==b for g,a,b in zip(expected,legacy,predicted,strict=True)),"exact_p":mcnemar_exact_pvalue(expected,legacy,predicted)},
        "abstention_contracts":{"case_count":len(abstain_expected),"correct":sum(a==b for a,b in zip(abstain_expected,abstain_actual,strict=True)),"evaluated":True,"expected_statuses":dict(Counter(abstain_expected))},
        "accuracy_by_category":{c:_accuracy(category_correct[c],category_totals[c]) for c in sorted(category_totals)},
        "accuracy_by_state":{s:_accuracy(state_correct[s],state_totals[s]) for s in sorted(state_totals)},
        "latency_ms":{"p50":round(sorted(latencies)[len(latencies)//2],3),"p95":round(sorted(latencies)[min(len(latencies)-1,int(len(latencies)*.95))],3)},
        "results":results,"git_sha":os.getenv("GITHUB_SHA","unknown"),
    }
    report["content_sha256"]=_content_digest(report); return report
