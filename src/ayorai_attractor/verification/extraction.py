"""Claim extraction: response decomposition only."""

from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from pydantic import BaseModel, ConfigDict, Field
from .models import Claim, Evidence

_SENTENCE_RE=re.compile(r"(?<=[.!?])\s+")

def _sha256(value:str)->str: return hashlib.sha256(value.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class ComponentProvenance:
    component:str; model:str; version:str; input_sha256:str; output_sha256:str
    def as_dict(self)->dict[str,str]:
        return {"component":self.component,"model":self.model,"version":self.version,"input_sha256":self.input_sha256,"output_sha256":self.output_sha256}

@dataclass(frozen=True)
class RetrievedDocument:
    id:str; content:str; source_id:str; source_location:str; retrieved_at:datetime
    start_offset:int=0; end_offset:int|None=None; origin_id:str|None=None
    canonical_url:str|None=None; normalized_content_hash:str|None=None
    cited_origin_id:str|None=None; locale:str="en-US"; provenance_complete:bool=True
    def to_evidence(self,claim_id:str,*,evidence_id:str|None=None)->Evidence:
        end=self.end_offset if self.end_offset is not None else len(self.content)
        return Evidence(id=evidence_id or self.id,claim_id=claim_id,source_id=self.source_id,source_location=self.source_location,retrieved_at=self.retrieved_at,start_offset=self.start_offset,end_offset=end,excerpt=self.content,origin_id=self.origin_id,canonical_url=self.canonical_url,normalized_content_hash=self.normalized_content_hash or _sha256(self.content),cited_origin_id=self.cited_origin_id,provenance_complete=self.provenance_complete)

@dataclass(frozen=True)
class ExtractedClaim:
    claim:Claim; confidence:float; provenance:ComponentProvenance

@dataclass(frozen=True)
class ClaimExtractionResult:
    claims:tuple[ExtractedClaim,...]

class ClaimExtractor(Protocol):
    def extract(self,response:str)->ClaimExtractionResult: ...

class RuleClaimExtractor:
    component="claim_extractor.rule"; model="rule-fixture"; version="2"
    def extract(self,response:str)->ClaimExtractionResult:
        claims=[]
        for i,text in enumerate((p.strip() for p in _SENTENCE_RE.split(response.strip()) if p.strip()),1):
            payload=json.dumps({"text":text},ensure_ascii=False,sort_keys=True)
            claims.append(ExtractedClaim(Claim(f"clm_{i:03d}",text),1.0,ComponentProvenance(self.component,self.model,self.version,_sha256(response),_sha256(payload))))
        return ClaimExtractionResult(tuple(claims))

class _LLMClaim(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    text:str=Field(min_length=1)
    confidence:float=Field(ge=0,le=1)

class _LLMClaims(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    claims:list[_LLMClaim]

class NLIClaimExtractor:
    component="claim_extractor.nli"
    def __init__(self,backend:Any,*,model:str,version:str)->None: self.backend,self.model,self.version=backend,model,version
    def extract(self,response:str)->ClaimExtractionResult:
        raw=self.backend.extract_claims(response)
        payload=_LLMClaims.model_validate({"claims":raw})
        return ClaimExtractionResult(tuple(ExtractedClaim(Claim(f"clm_{i:03d}",item.text),item.confidence,ComponentProvenance(self.component,self.model,self.version,_sha256(response),_sha256(json.dumps(item.model_dump(mode="json"),sort_keys=True)))) for i,item in enumerate(payload.claims,1)))

class LLMClaimExtractor:
    component="claim_extractor.llm"
    def __init__(self,provider:Any,*,model:str,version:str)->None: self.provider,self.model,self.version=provider,model,version
    def extract(self,response:str)->ClaimExtractionResult:
        prompt=json.dumps({"task":"decompose the model response into atomic factual claims","response":response,"output_schema":{"claims":[{"text":"string","confidence":"number"}]}},ensure_ascii=False,sort_keys=True)
        provider_response=self.provider.execute(prompt)
        payload=_LLMClaims.model_validate_json(provider_response.text)
        return ClaimExtractionResult(tuple(ExtractedClaim(Claim(f"clm_{i:03d}",item.text),item.confidence,ComponentProvenance(self.component,self.model,self.version,_sha256(response),_sha256(provider_response.text))) for i,item in enumerate(payload.claims,1)))
