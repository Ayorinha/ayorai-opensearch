from __future__ import annotations
import hashlib,json,re
from dataclasses import dataclass
from typing import Any,Protocol,Sequence
from pydantic import BaseModel,ConfigDict,Field
from .extraction import ComponentProvenance,ExtractedClaim
from .models import Evidence,Stance,StanceEdge
from .numeric import DEFAULT_RELATIVE_TOLERANCE,NumericLocale,numeric_conflicts
_NUMBER_RE=re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+|[.,]\d{3})*(?:\s*%)?")
_DATE_RE=re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TOKEN_RE=re.compile(r"[\wÀ-ÿ]+",re.UNICODE)
_NEGATION_TOKENS=frozenset({"not","no","didn't","doesn't","never","não","nao","nunca","sem"})
_STOPWORDS=frozenset({"the","a","an","and","or","of","for","in","on","at","to","was","were","is","are","reported","reports","year","fiscal","de","da","do","e","em","no","na","foi","era","é"})
_UNIT_WORDS=frozenset({"usd","eur","brl","ms","million","millions","billion","billions","employees","people","customers","offices","percent","rate","year"})
def _sha256(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
def _has_negation(t:str)->bool:return bool({x.casefold() for x in _TOKEN_RE.findall(t)}&_NEGATION_TOKENS)
def _numeric_facts(t:str)->list[tuple[str,str,str]]:
    tokens=_TOKEN_RE.findall(t.casefold()); facts=[]
    for i,token in enumerate(tokens):
        if not _NUMBER_RE.fullmatch(token): continue
        before=tokens[max(0,i-6):i]; context=before+tokens[i+1:i+4]
        if "%" in token or "percent" in context: unit="percent"
        elif any(v in context for v in ("usd","eur","brl")):
            cur=next(v for v in ("usd","eur","brl") if v in context); scale=next((v for v in ("million","millions","billion","billions") if v in context),""); unit=f"{cur}:{scale or 'base'}"
        elif "ms" in context: unit="ms"
        elif "year" in context: unit="year"
        elif any(v in context for v in ("employees","people","customers","offices")):
            word=next(v for v in ("employees","people","customers","offices") if v in context); unit=f"count:{word}"
        else: unit="scalar"
        attr="year" if unit=="year" else next((v for v in reversed(before) if v not in _STOPWORDS and v not in _UNIT_WORDS),"unknown")
        facts.append((token,unit,attr))
    return facts
def _numeric_conflict(c:str,e:str)->bool:
    return any(lu==ru and la==ra and numeric_conflicts(l,r,locale=NumericLocale.EN_US,tolerance=DEFAULT_RELATIVE_TOLERANCE) for l,lu,la in _numeric_facts(c) for r,ru,ra in _numeric_facts(e))
@dataclass(frozen=True)
class DetectedStance:
    edge:StanceEdge; confidence:float; provenance:ComponentProvenance
@dataclass(frozen=True)
class StanceDetectionResult:
    edges:tuple[DetectedStance,...]
class StanceDetector(Protocol):
    def detect(self,claims:Sequence[ExtractedClaim],evidence:Sequence[Evidence])->StanceDetectionResult:...
class _LLMStance(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    evidence_id:str=Field(min_length=1)
    stance:Stance
    confidence:float=Field(ge=0,le=1)
class RuleStanceDetector:
    component="stance_detector.rule";model="rule-fixture";version="4"
    def detect(self,claims:Sequence[ExtractedClaim],evidence:Sequence[Evidence])->StanceDetectionResult:
        out=[]
        for c in claims:
            ct={x.casefold() for x in _TOKEN_RE.findall(c.claim.text) if len(x)>2}
            for item in (x for x in evidence if x.claim_id==c.claim.id):
                et={x.casefold() for x in _TOKEN_RE.findall(item.excerpt) if len(x)>2}; lexical=len(ct&et)/max(len(ct),1)
                if lexical<.25: stance=Stance.NEUTRAL
                else: stance=Stance.CONTRADICTS if (_numeric_conflict(c.claim.text,item.excerpt) or bool(set(_DATE_RE.findall(c.claim.text))&set(_DATE_RE.findall(item.excerpt)) and set(_DATE_RE.findall(c.claim.text)).isdisjoint(set(_DATE_RE.findall(item.excerpt)))) or _has_negation(c.claim.text)!=_has_negation(item.excerpt)) else Stance.SUPPORTS
                out.append(DetectedStance(StanceEdge(id=f"ste_{c.claim.id}_{item.id}",claim_id=c.claim.id,evidence_id=item.id,stance=stance),min(1.,max(.5,.5+lexical/2)),ComponentProvenance(self.component,self.model,self.version,_sha256(c.claim.text+"\n"+item.excerpt),_sha256(f"{c.claim.id}|{item.id}|{stance.value}"))))
        return StanceDetectionResult(tuple(out))
class NLIStanceDetector:
    component="stance_detector.nli"
    def __init__(self,backend:Any,*,model:str,version:str)->None:self.backend,self.model,self.version=backend,model,version
    def detect(self,claims:Sequence[ExtractedClaim],evidence:Sequence[Evidence])->StanceDetectionResult:
        out=[]
        for c in claims:
            for item in (x for x in evidence if x.claim_id==c.claim.id):
                result=self.backend.classify(c.claim.text,item.excerpt)
                parsed=_LLMStance.model_validate({**result,"evidence_id":result.get("evidence_id",item.id)})
                if parsed.evidence_id!=item.id: raise ValueError(f"unknown evidence id: {parsed.evidence_id}")
                out.append(DetectedStance(StanceEdge(id=f"ste_{c.claim.id}_{item.id}",claim_id=c.claim.id,evidence_id=item.id,stance=parsed.stance),parsed.confidence,ComponentProvenance(self.component,self.model,self.version,_sha256(c.claim.text+"\n"+item.excerpt),_sha256(parsed.model_dump_json()))))
        return StanceDetectionResult(tuple(out))
class LLMStanceDetector:
    component="stance_detector.llm"
    def __init__(self,provider:Any,*,model:str,version:str)->None:self.provider,self.model,self.version=provider,model,version
    def detect(self,claims:Sequence[ExtractedClaim],evidence:Sequence[Evidence])->StanceDetectionResult:
        out=[]
        for c in claims:
            for item in (x for x in evidence if x.claim_id==c.claim.id):
                prompt=json.dumps({"task":"classify stance only","claim":c.claim.text,"evidence":{"id":item.id,"text":item.excerpt},"allowed_stance":["supports","contradicts","neutral"],"allowed_evidence_ids":[item.id],"output_schema":{"evidence_id":"string","stance":"supports|contradicts|neutral","confidence":"number"}},ensure_ascii=False,sort_keys=True)
                response=self.provider.execute(prompt); parsed=_LLMStance.model_validate_json(response.text)
                if parsed.evidence_id!=item.id: raise ValueError(f"unknown evidence id: {parsed.evidence_id}")
                out.append(DetectedStance(StanceEdge(id=f"ste_{c.claim.id}_{item.id}",claim_id=c.claim.id,evidence_id=item.id,stance=parsed.stance),parsed.confidence,ComponentProvenance(self.component,self.model,self.version,_sha256(prompt),_sha256(response.text))))
        return StanceDetectionResult(tuple(out))
