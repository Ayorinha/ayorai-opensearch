# ruff: noqa
"""Deterministic benchmark statistics."""

from __future__ import annotations
from collections import Counter
from math import comb
from random import Random
from collections.abc import Sequence
from ayorai_attractor.verification.models import Verdict

VERDICT_ORDER=tuple(item.value.upper() for item in Verdict)

def confusion_matrix(expected:Sequence[str],predicted:Sequence[str])->dict[str,dict[str,int]]:
    if len(expected)!=len(predicted): raise ValueError("expected and predicted must have the same length")
    allowed=set(VERDICT_ORDER)
    if any(x not in allowed for x in expected) or any(x not in allowed for x in predicted): raise ValueError("labels must be Judge verdict states")
    counts=Counter(zip(expected,predicted,strict=True))
    return {gold:{guess:counts[(gold,guess)] for guess in VERDICT_ORDER} for gold in VERDICT_ORDER}

def balanced_accuracy(expected:Sequence[str],predicted:Sequence[str])->float:
    if len(expected)!=len(predicted) or not expected: raise ValueError("expected and predicted must be non-empty and equal")
    recalls=[]
    for label in VERDICT_ORDER:
        total=sum(x==label for x in expected)
        if total: recalls.append(sum(x==label and y==label for x,y in zip(expected,predicted,strict=True))/total)
    return sum(recalls)/len(recalls)

def bootstrap_accuracy(expected:Sequence[str],predicted:Sequence[str],*,iterations:int=10000,seed:int=20261003)->tuple[float,float]:
    if len(expected)!=len(predicted): raise ValueError("expected and predicted must have the same length")
    if not expected or iterations<1: raise ValueError("invalid bootstrap inputs")
    outcomes=[a==b for a,b in zip(expected,predicted,strict=True)]; rng=Random(seed)  # nosec B311 - deterministic statistical bootstrap, not cryptography
    samples=[]
    for _ in range(iterations):
        samples.append(sum(outcomes[rng.randrange(len(outcomes))] for _ in outcomes)/len(outcomes))
    samples.sort(); return samples[int(.025*(iterations-1))],samples[int(.975*(iterations-1))]

def mcnemar_exact_pvalue(expected:Sequence[str],predicted_a:Sequence[str],predicted_b:Sequence[str])->float:
    if not(len(expected)==len(predicted_a)==len(predicted_b)): raise ValueError("all sequences must have same length")
    b=sum(a==g and c!=g for g,a,c in zip(expected,predicted_a,predicted_b,strict=True))
    c=sum(a!=g and d==g for g,a,d in zip(expected,predicted_a,predicted_b,strict=True))
    n=b+c
    if n==0:return 1.0
    return min(1.0,2*sum(comb(n,k) for k in range(min(b,c)+1))/2**n)
