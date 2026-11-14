def test_annotation_approval_rejects_failed_human_agreement(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    labels = tmp_path / "labels.jsonl"
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    agreement = tmp_path / "agreement.json"
    approval = tmp_path / "approval.json"
    adjudication = tmp_path / "adjudication.md"
    cases.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    labels.write_text("{}\n", encoding="utf-8")
    annotation_rows = (
        {"case_id": "case-1", "label": "SUPPORTED"},
        {"case_id": "case-2", "label": "REFUTED"},
    )
    annotation_a.write_text("\n".join(json.dumps(row) for row in annotation_rows) + "\n", encoding="utf-8")
    annotation_b.write_text("\n".join(json.dumps(row) for row in annotation_rows) + "\n", encoding="utf-8")
    agreement_data = _write_agreement_report(agreement, annotation_a, annotation_b)
    development_cases = tmp_path / "development-cases.jsonl"
    development_labels = tmp_path / "development-labels.jsonl"
    development_cases.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    development_labels.write_text("{}\n", encoding="utf-8")
    adjudication.write_text("synthetic only\n", encoding="utf-8")
    agreement_data = _write_agreement_report(agreement, annotation_a, annotation_b)
    approval.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "APPROVED",
                "approved_by": "Synthetic approver",
                "approved_at": "2026-10-21",
                "cases_sha256": "0" * 64,
                "labels_sha256": "0" * 64,
                "development_cases_sha256": "0" * 64,
                "development_labels_sha256": "0" * 64,
                "agreement_report_sha256": "0" * 64,
                "adjudication_record_sha256": "0" * 64,
                "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
                "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
                "cohen_kappa": agreement_data["cohen_kappa"],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="human annotator agreement gate did not pass"):
        RUNNER["validate_annotation_approval"](
            cases,
            labels,
            development_cases,
            development_labels,
            annotation_a,
            annotation_b,
            agreement,
            approval,
            adjudication,
        )


def test_annotation_approval_binds_final_labels_hash(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    labels = tmp_path / "labels.jsonl"
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    agreement = tmp_path / "agreement.json"
    approval = tmp_path / "approval.json"
    adjudication = tmp_path / "adjudication.md"
    cases.write_text("\n".join(json.dumps({"case_id": case_id}) for case_id in ("case-1", "case-2")) + "\n", encoding="utf-8")
    labels.write_text("{}\n", encoding="utf-8")
    annotation_a.write_text(
        json.dumps({"case_id": "case-1", "label": "SUPPORTED"}) + "\n", encoding="utf-8"
    )
    annotation_b.write_text(
        json.dumps({"case_id": "case-1", "label": "SUPPORTED"}) + "\n", encoding="utf-8"
    )
    development_cases = tmp_path / "development-cases.jsonl"
    development_labels = tmp_path / "development-labels.jsonl"
    development_cases.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    development_labels.write_text("{}\n", encoding="utf-8")
    adjudication.write_text("synthetic only\n", encoding="utf-8")
    agreement.write_text(
        json.dumps(
            {
                "method": "cohen_kappa_unweighted",
                "cohen_kappa": 1.0,
                "gate_passed": True,
                "inputs": {
                    "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
                    "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
                },
            }
        ),
        encoding="utf-8",
    )
    approval.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "APPROVED",
                "approved_by": "Synthetic approver",
                "approved_at": "2026-10-21",
                "cases_sha256": RUNNER["_sha256"](cases),
                "labels_sha256": "0" * 64,
                "development_cases_sha256": RUNNER["_sha256"](development_cases),
                "development_labels_sha256": RUNNER["_sha256"](development_labels),
                "agreement_report_sha256": RUNNER["_sha256"](agreement),
                "adjudication_record_sha256": RUNNER["_sha256"](adjudication),
                "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
                "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
                "cohen_kappa": 1.0,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="labels_sha256 differs from approval manifest"):
        RUNNER["validate_annotation_approval"](
            cases,
            labels,
            development_cases,
            development_labels,
            annotation_a,
            annotation_b,
            agreement,
            approval,
            adjudication,
        )

    manifest = json.loads(approval.read_text(encoding="utf-8"))
    manifest["labels_sha256"] = RUNNER["_sha256"](labels)
    approval.write_text(json.dumps(manifest), encoding="utf-8")
    annotation_a.write_text(
        json.dumps({"case_id": "case-1", "label": "REFUTED"}) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="annotation_a_sha256 differs from approval manifest"):
        RUNNER["validate_annotation_approval"](
            cases,
            labels,
            development_cases,
            development_labels,
            annotation_a,
            annotation_b,
            agreement,
            approval,
            adjudication,
        )


def test_annotation_approval_rejects_tampered_recomputed_statistics(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    labels = tmp_path / "labels.jsonl"
    development_cases = tmp_path / "development-cases.jsonl"
    development_labels = tmp_path / "development-labels.jsonl"
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    agreement = tmp_path / "agreement.json"
    approval = tmp_path / "approval.json"
    adjudication = tmp_path / "adjudication.md"
    cases.write_text("\n".join(json.dumps({"case_id": x}) for x in ("a", "b")) + "\n", encoding="utf-8")
    labels.write_text("{}\n", encoding="utf-8")
    development_cases.write_text("{}\n", encoding="utf-8")
    development_labels.write_text("{}\n", encoding="utf-8")
    adjudication.write_text("synthetic only\n", encoding="utf-8")
    annotation_rows = (
        {"case_id": "a", "label": "SUPPORTED"},
        {"case_id": "b", "label": "REFUTED"},
    )
    annotation_a.write_text("\n".join(json.dumps(row) for row in annotation_rows) + "\n", encoding="utf-8")
    annotation_b.write_text("\n".join(json.dumps(row) for row in annotation_rows) + "\n", encoding="utf-8")
    canonical = _write_agreement_report(agreement, annotation_a, annotation_b)
    manifest = {
        "schema_version": 1,
        "status": "APPROVED",
        "approved_by": "Synthetic approver",
        "approved_at": "2026-10-21",
        "cases_sha256": RUNNER["_sha256"](cases),
        "labels_sha256": RUNNER["_sha256"](labels),
        "development_cases_sha256": RUNNER["_sha256"](development_cases),
        "development_labels_sha256": RUNNER["_sha256"](development_labels),
        "agreement_report_sha256": RUNNER["_sha256"](agreement),
        "adjudication_record_sha256": RUNNER["_sha256"](adjudication),
        "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
        "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
        "cohen_kappa": canonical["cohen_kappa"],
    }
    mutations = (
        lambda report: report["bootstrap"].update(iterations=10),
        lambda report: report["bootstrap"].update(seed=17),
        lambda report: report["bootstrap"].update(generator="legacy-random"),
        lambda report: report["bootstrap"].update(percentile="legacy-order-statistic"),
        lambda report: report["ci95_case_bootstrap"].__setitem__(0, -0.5),
        lambda report: report.update(cohen_kappa=0.9),
    )
    for mutate in mutations:
        report = json.loads(json.dumps(canonical))
        mutate(report)
        agreement.write_text(json.dumps(report), encoding="utf-8")
        manifest["agreement_report_sha256"] = RUNNER["_sha256"](agreement)
        manifest["cohen_kappa"] = report["cohen_kappa"]
        approval.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="differs from canonical recomputation"):
            RUNNER["validate_annotation_approval"](
                cases, labels, development_cases, development_labels,
                annotation_a, annotation_b, agreement, approval, adjudication
            )


def test_protocol_freeze_requires_status_manifest_and_exact_hashes(tmp_path: Path) -> None:
    eval_dir = tmp_path / "docs" / "eval"
    eval_dir.mkdir(parents=True)
    protocol = eval_dir / "PROTOCOL-GOLDEN-V1.md"
    preregistration = eval_dir / "PREREGISTRATION-RGC-v1.md"
    runner_spec = eval_dir / "RUNNER-RGC-v1.md"
    runner_code = tmp_path / "evals" / "ptbr" / "rgc_eval.py"
    runner_code.parent.mkdir(parents=True)
    manifest_path = eval_dir / "PROTOCOL-FREEZE.json"
    protocol.write_text("Status: CONGELADO — aprovado após revisão humana.\n", encoding="utf-8")
    preregistration.write_text(
        "**Estado:** [CONGELADO] — critérios congelados.\n", encoding="utf-8"
    )
    runner_spec.write_text("**Estado:** [CONGELADO] — executor congelado.\n", encoding="utf-8")
    runner_code.write_text(f'RUNNER_VERSION = "{RUNNER["RUNNER_VERSION"]}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="requires both documents"):
        RUNNER["validate_protocol_freeze"](tmp_path)

    manifest = {
        "schema_version": 1,
        "status": "FROZEN",
        "approved_by": "Anderson Leon Ayora",
        "approved_at": "2026-10-21",
        "protocol_sha256": RUNNER["_sha256"](protocol),
        "preregistration_sha256": RUNNER["_sha256"](preregistration),
        "runner_spec_sha256": RUNNER["_sha256"](runner_spec),
        "runner_code_sha256": RUNNER["_sha256"](runner_code),
        "runner_version": RUNNER["RUNNER_VERSION"],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = RUNNER["validate_protocol_freeze"](tmp_path)
    assert result["approved_by"] == "Anderson Leon Ayora"
    assert result["protocol_sha256"] == manifest["protocol_sha256"]
    assert len(result["manifest_sha256"]) == 64

    protocol.write_text("Status: alterado após congelamento.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="protocol is not marked CONGELADO"):
        RUNNER["validate_protocol_freeze"](tmp_path)


def test_protocol_freeze_rejects_stale_document_hash(tmp_path: Path) -> None:
    eval_dir = tmp_path / "docs" / "eval"
    eval_dir.mkdir(parents=True)
    protocol = eval_dir / "PROTOCOL-GOLDEN-V1.md"
    preregistration = eval_dir / "PREREGISTRATION-RGC-v1.md"
    runner_spec = eval_dir / "RUNNER-RGC-v1.md"
    runner_code = tmp_path / "evals" / "ptbr" / "rgc_eval.py"
    runner_code.parent.mkdir(parents=True)
    protocol.write_text("Status: CONGELADO\n", encoding="utf-8")
    preregistration.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_spec.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_code.write_text(f'RUNNER_VERSION = "{RUNNER["RUNNER_VERSION"]}\n', encoding="utf-8")
    manifest_path = eval_dir / "PROTOCOL-FREEZE.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "FROZEN",
                "approved_by": "Anderson Leon Ayora",
                "approved_at": "2026-10-21",
                "protocol_sha256": "0" * 64,
                "preregistration_sha256": RUNNER["_sha256"](preregistration),
                "runner_spec_sha256": RUNNER["_sha256"](runner_spec),
                "runner_code_sha256": "0" * 64,
                "runner_version": RUNNER["RUNNER_VERSION"],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="protocol_sha256 differs"):
        RUNNER["validate_protocol_freeze"](tmp_path)


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("runner_spec_sha256", "0" * 64, "runner_spec_sha256 differs"),
        ("runner_code_sha256", "0" * 64, "runner_code_sha256 differs"),
        ("runner_version", "rgc-eval/9.9.9", "runner version differs"),
    ],
)
def test_protocol_freeze_rejects_runner_artifact_drift(
    tmp_path: Path, field: str, bad_value: str, message: str
) -> None:
    eval_dir = tmp_path / "docs" / "eval"
    eval_dir.mkdir(parents=True)
    protocol = eval_dir / "PROTOCOL-GOLDEN-V1.md"
    preregistration = eval_dir / "PREREGISTRATION-RGC-v1.md"
    runner_spec = eval_dir / "RUNNER-RGC-v1.md"
    runner_code = tmp_path / "evals" / "ptbr" / "rgc_eval.py"
    runner_code.parent.mkdir(parents=True)
    protocol.write_text("Status: CONGELADO\n", encoding="utf-8")
    preregistration.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_spec.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_code.write_text(f'RUNNER_VERSION = "{RUNNER["RUNNER_VERSION"]}"\n', encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "status": "FROZEN",
        "approved_by": "Anderson Leon Ayora",
        "approved_at": "2026-10-21",
        "protocol_sha256": RUNNER["_sha256"](protocol),
        "preregistration_sha256": RUNNER["_sha256"](preregistration),
        "runner_spec_sha256": RUNNER["_sha256"](runner_spec),
        "runner_code_sha256": RUNNER["_sha256"](runner_code),
        "runner_version": RUNNER["RUNNER_VERSION"],
    }
    manifest[field] = bad_value
    (eval_dir / "PROTOCOL-FREEZE.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["validate_protocol_freeze"](tmp_path)


def test_dec018_development_partition_reports_metrics_without_testing_h1() -> None:
    case = _case("dev-scope", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    result = RUNNER["evaluate"](
        [case],
        {"dev-scope": "SUPPORTED"},
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
        partition="development",
    )
    assert result["evaluation_partition"] == "development"
    assert result["metrics"]["primary_criterion"]["h1_supported"] is None
    assert result["metrics"]["primary_criterion"]["not_tested"] is True


# --- DEC-010 option A: annotated atoms for compound claims -------------------

CANCEL = "§ 1º O cancelamento será efetivado em até 2 (dois) dias."


def _compound(case_id: str, claim: str, parts: list[str]) -> dict[str, Any]:
    case = _case(case_id, claim, CANCEL)
    case["atoms"] = [
        {"start_offset": claim.index(part), "end_offset": claim.index(part) + len(part)}
        for part in parts
    ]
    return case


def _predict(case: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = RUNNER["predict"](
        case["claim"],
        RUNNER["oracle_passages"](case, DOCS),
        DOCS,
        atoms=RUNNER["case_atoms"](case),
    )
    return result


def test_compound_claim_with_one_unconfirmed_part_is_partially_supported() -> None:
    claim = "O cancelamento será efetivado em até 2 dias e o plano terá multa de 10%."
    case = _compound(
        "k4", claim, ["O cancelamento será efetivado em até 2 dias", "o plano terá multa de 10%"]
    )
    result = _predict(case)
    assert result["judge_verdict"] == "PARTIALLY_SUPPORTED"
    assert result["stances"] == ["SUPPORTS", "NEUTRAL"]
    # The same text as a single atom cannot reach K4 (the limitation fixed here).
    single = _predict(_case("k4-single", claim, CANCEL))
    assert single["judge_verdict"] != "PARTIALLY_SUPPORTED"


def test_compound_claim_with_a_contradicted_part_is_refuted() -> None:
    claim = "O cancelamento será efetivado em até 9 dias e o plano terá multa de 10%."
    case = _compound(
        "k1", claim, ["O cancelamento será efetivado em até 9 dias", "o plano terá multa de 10%"]
    )
    assert _predict(case)["judge_verdict"] == "REFUTED"


def test_compound_prediction_is_deterministic_and_lists_atoms() -> None:
    claim = "O cancelamento será efetivado em até 2 dias e o plano terá multa de 10%."
    parts = ["O cancelamento será efetivado em até 2 dias", "o plano terá multa de 10%"]
    first = _predict(_compound("d1", claim, parts))
    second = _predict(_compound("d1", claim, parts))
    assert first["output_sha256"] == second["output_sha256"]
    assert first["atoms"] == parts


def test_case_without_atoms_keeps_single_atom_behaviour() -> None:
    case = _case("s1", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    assert RUNNER["case_atoms"](case) is None
    result = _predict(case)
    assert result["atoms"] == [case["claim"]]
    assert result["judge_verdict"] == "SUPPORTED"


@pytest.mark.parametrize(
    ("atoms", "message"),
    [
        ([{"start_offset": 0, "end_offset": 5}], "two or more"),
        (
            [{"start_offset": 0, "end_offset": 5}, {"start_offset": 3, "end_offset": 9}],
            "non-overlapping",
        ),
        (
            [{"start_offset": 0, "end_offset": 5}, {"start_offset": 6, "end_offset": 999}],
            "outside the claim",
        ),
        ([{"start_offset": 0, "end_offset": 5}, {"start_offset": 5, "end_offset": 6}], "blank"),
        (
            [
                {"start_offset": 0, "end_offset": 5, "text": "Outro"},
                {"start_offset": 6, "end_offset": 10},
            ],
            "does not match",
        ),
        (
            [{"start_offset": "0", "end_offset": 5}, {"start_offset": 6, "end_offset": 10}],
            "integers",
        ),
        (
            [{"start_offset": True, "end_offset": 5}, {"start_offset": 6, "end_offset": 10}],
            "integers",
        ),
        (
            [{"start_offset": 0, "end_offset": True}, {"start_offset": 6, "end_offset": 10}],
            "integers",
        ),
        ([None, {"start_offset": 6, "end_offset": 10}], "each atom must be an object"),
    ],
)
def test_invalid_atom_annotation_stops_the_run(atoms: list[Any], message: str) -> None:
    case = _case("bad", "Texto A e texto B.", CANCEL)
    case["atoms"] = atoms
    with pytest.raises(ValueError, match=message):
        RUNNER["case_atoms"](case)


def test_evaluate_uses_annotated_atoms() -> None:
    claim = "O cancelamento será efetivado em até 2 dias e o plano terá multa de 10%."
    case = _compound(
        "e1", claim, ["O cancelamento será efetivado em até 2 dias", "o plano terá multa de 10%"]
    )
    result = RUNNER["evaluate"](
        [case],
        {"e1": "PARTIALLY_SUPPORTED"},
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=10,
    )
    assert result["cases"][0]["predicted"] == "PARTIALLY_SUPPORTED"


# ------------------------------------------- rectified stratum (Amendment 4)


def _rectified_cases() -> list[dict[str, Any]]:
    supported = _case("r1", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    refuted = _case("r2", "O cancelamento será efetivado em até 9 dias.", CANCEL)
    plain = _case("r3", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    supported["rectified"] = True
    refuted["rectified"] = True
    plain["rectified"] = False
    return [supported, refuted, plain]


def test_rectified_mark_defaults_to_false_and_must_be_boolean() -> None:
    case = _case("r0", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    assert RUNNER["case_rectified"](case) is False
    case["rectified"] = True
    assert RUNNER["case_rectified"](case) is True
    for bad in ("true", 1, None, "sim"):
        case["rectified"] = bad
        with pytest.raises(ValueError, match="rectified must be true or false"):
            RUNNER["case_rectified"](case)


def test_rectified_cases_are_reported_as_a_separate_stratum() -> None:
    labels = {"r1": "SUPPORTED", "r2": "SUPPORTED", "r3": "SUPPORTED"}
    result = RUNNER["evaluate"](
        _rectified_cases(),
        labels,
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=50,
    )
    # Primary metrics keep every evaluable case, rectified or not.
    assert result["metrics"]["n"] == 3
    assert [row["rectified"] for row in result["cases"]] == [True, True, False]
    rectified, plain = result["strata"]["rectified"], result["strata"]["not_rectified"]
    assert rectified["n"] == 2
    assert rectified["system"]["accuracy"] == 0.5
    assert rectified["confusion"]["SUPPORTED"]["REFUTED"] == 1
    assert plain["n"] == 1
    assert plain["system"]["accuracy"] == 1.0
    assert "primary_criterion" not in rectified


def test_rectified_mark_does_not_change_the_judge_output() -> None:
    marked = _rectified_cases()
    unmarked = [{k: v for k, v in case.items() if k != "rectified"} for case in marked]
    labels = {"r1": "SUPPORTED", "r2": "REFUTED", "r3": "SUPPORTED"}
    run = RUNNER["evaluate"]
    with_mark = run(
        marked,
        labels,
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
    )
    without = run(
        unmarked,
        labels,
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
    )
    assert [r["output_sha256"] for r in with_mark["cases"]] == [
        r["output_sha256"] for r in without["cases"]
    ]
    assert with_mark["metrics"] == without["metrics"]
    assert without["strata"]["rectified"] == {"n": 0}
    assert without["strata"]["not_rectified"]["n"] == 3


def test_invalid_rectified_mark_stops_the_run() -> None:
    cases = _rectified_cases()
    cases[0]["rectified"] = "true"
    with pytest.raises(ValueError, match="rectified must be true or false"):
        RUNNER["evaluate"](
            cases,
            {"r1": "SUPPORTED", "r2": "REFUTED", "r3": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


@pytest.mark.parametrize(
    ("labels", "case_id"),
    [
        ({"r4": "RULE_GAP"}, "excluded"),
        ({}, "unlabeled"),
    ],
)
def test_invalid_rectified_mark_is_rejected_even_when_case_is_not_scored(
    labels: dict[str, str], case_id: str
) -> None:
    case = _case("r4", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    case["rectified"] = "true"
    with pytest.raises(ValueError, match="rectified must be true or false"):
        RUNNER["evaluate"](
            [case],
            labels,
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ('{"case_id":123,"verdict":"SUPPORTED"}', "case_id must be a non-empty string"),
        (
            '{"case_id":"x","verdict":"SUPPORTED","note":"extra"}',
            "expected exactly case_id and verdict",
        ),
        ('{"case_id":"x"}', "expected exactly case_id and verdict"),
        ('{"case_id":" ","verdict":"SUPPORTED"}', "case_id must be a non-empty string"),
        ('{"case_id":"x","verdict":1}', "label 1"),
    ],
)
def test_load_labels_rejects_noncanonical_records(tmp_path: Path, line: str, message: str) -> None:
    path = tmp_path / "labels.jsonl"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["load_labels"](path, "judge2")


def test_load_labels_rejects_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    path.write_text('{"case_id":"x","verdict":"SUPPORTED"}\n\n', encoding="utf-8")
    with pytest.raises(ValueError, match="blank lines are not allowed"):
        RUNNER["load_labels"](path, "judge2")


def _source_record(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "source_id": "synthetic-source",
        "source_url": "https://example.test/source",
        "retrieved_at": "2026-10-22T00:00:00Z",
        "source_license": "synthetic",
        "text": "Synthetic source text.",
    }
    record.update(overrides)
    return record


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (_source_record(source_id=123), "source_id must be a non-empty string"),
        (_source_record(source_url=" "), "source_url must be a non-empty string"),
        (_source_record(retrieved_at=None), "retrieved_at must be a non-empty string"),
        (
            _source_record(source_license=["synthetic"]),
            "source_license must be a non-empty string",
        ),
        (_source_record(text=42), "text must be a non-empty string"),
        *[
            (
                {key: value for key, value in _source_record().items() if key != missing},
                "expected an object",
            )
            for missing in ("source_id", "source_url", "retrieved_at", "source_license", "text")
        ],
        *[
            (_source_record(**{field: ""}), f"{field} must be a non-empty string")
            for field in ("source_id", "source_url", "retrieved_at", "source_license", "text")
        ],
        (
            _source_record(text_sha256="not-a-hash"),
            "text_sha256 must be 64 lowercase hex characters",
        ),
        (
            _source_record(text_sha256="A" * 64),
            "text_sha256 must be 64 lowercase hex characters",
        ),
        (
            _source_record(text_sha256=None),
            "text_sha256 must be 64 lowercase hex characters",
        ),
        (_source_record(text_sha256="0" * 64), "text_sha256 mismatch"),
    ],
)
def test_load_documents_rejects_malformed_source_records(
    tmp_path: Path, record: dict[str, Any], message: str
) -> None:
    path = tmp_path / "documents.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["load_documents"](path)


def test_load_documents_accepts_additional_provenance_metadata(tmp_path: Path) -> None:
    path = tmp_path / "documents.jsonl"
    record = _source_record(
        title="Synthetic source",
        extraction="synthetic extraction method",
        page_source_ids=["synthetic-page-1"],
    )
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    documents = RUNNER["load_documents"](path)
    assert documents["synthetic-source"].text == "Synthetic source text."


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ('{"source_id":', "invalid JSON"),
        ('{"source_id":"x"}\n', "expected an object"),
        (json.dumps(_source_record()) + "\n\n", "blank lines are not allowed"),
    ],
)
def test_load_documents_rejects_invalid_jsonl_layout(
    tmp_path: Path, contents: str, message: str
) -> None:
    path = tmp_path / "documents.jsonl"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["load_documents"](path)


def test_load_documents_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    path = tmp_path / "documents.jsonl"
    record = _source_record()
    path.write_text(
        json.dumps(record) + "\n" + json.dumps(record) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate document"):
        RUNNER["load_documents"](path)


# --- approval integrity / definitive partition guards -------------------------


def test_annotation_approval_requires_exact_case_id_coverage(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    cases.write_text('{"case_id":"case-1"}\n{"case_id":"case-2"}\n', encoding="utf-8")
    annotation_a.write_text(
        '{"case_id":"case-1","label":"SUPPORTED"}\n{"case_id":"case-2","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    annotation_b.write_text(
        '{"case_id":"case-1","label":"SUPPORTED"}\n{"case_id":"case-2","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    RUNNER["_validate_annotation_case_ids"](cases, annotation_a, annotation_b)

    annotation_a.write_text(
        '{"case_id":"case-1","label":"SUPPORTED"}\n{"case_id":"extra-a","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    annotation_b.write_text(
        '{"case_id":"case-2","label":"REFUTED"}\n{"case_id":"extra-b","label":"SUPPORTED"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as exc_info:
        RUNNER["_validate_annotation_case_ids"](cases, annotation_a, annotation_b)
    message = str(exc_info.value)
    assert "cases-A=['case-2']" in message
    assert "cases-B=['case-1']" in message
    assert "A-cases=['extra-a']" in message
    assert "B-cases=['extra-b']" in message


def test_annotation_case_id_reader_rejects_duplicate_and_blank_records(tmp_path: Path) -> None:
    path = tmp_path / "annotation.jsonl"
    path.write_text(
        '{"case_id":"case-1","label":"SUPPORTED"}\n{"case_id":"case-1","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate case_id"):
        RUNNER["_strict_jsonl_case_ids"](path, annotation=True)

    path.write_text('{"case_id":"case-1","label":"SUPPORTED"}\n\n', encoding="utf-8")
    with pytest.raises(ValueError, match="blank lines are not allowed"):
        RUNNER["_strict_jsonl_case_ids"](path, annotation=True)


def test_evaluate_preflights_all_cases_before_predicting(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = [
        _case(
            "preflight-1",
            "O prazo é de cinco dias úteis.",
            "no prazo máximo de 5 (cinco) dias úteis",
        ),
        _case(
            "preflight-2",
            "O cancelamento ocorre em dois dias.",
            "O cancelamento será efetivado em até 2 (dois) dias",
        ),
        _case(
            "preflight-3",
            "A devolução é em dobro.",
            "A cobrança indevida será devolvida em dobro",
        ),
    ]
    cases[1]["rectified"] = "invalid"
    calls: list[str] = []

    def predictor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(str(args[0]))
        raise AssertionError("predict must not run when preflight fails")

    monkeypatch.setitem(RUNNER["evaluate"].__globals__, "predict", predictor)
    with pytest.raises(ValueError, match="rectified must be true or false"):
        RUNNER["evaluate"](
            cases,
            {case["case_id"]: "SUPPORTED" for case in cases},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    assert calls == []


def test_evaluate_preflights_invalid_gold_label_before_predicting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(
        "invalid-gold-label",
        "O prazo é de cinco dias úteis.",
        "no prazo máximo de 5 (cinco) dias úteis",
    )
    calls: list[str] = []

    def predictor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(str(args[0]))
        raise AssertionError("predict must not run when the gold label is invalid")

    monkeypatch.setitem(RUNNER["evaluate"].__globals__, "predict", predictor)
    with pytest.raises(ValueError, match="invalid gold label"):
        RUNNER["evaluate"](
            [case],
            {"invalid-gold-label": "UNRECOGNIZED_LABEL"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    assert calls == []


def _preflight_cases() -> list[dict[str, Any]]:
    return [
        _case(
            "oracle-preflight-1",
            "O prazo é de cinco dias úteis.",
            "no prazo máximo de 5 (cinco) dias úteis",
        ),
        _case(
            "oracle-preflight-2",
            "O cancelamento ocorre em dois dias.",
            "O cancelamento será efetivado em até 2 (dois) dias",
        ),
    ]


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        (
            lambda case: case["evidence"][0].update(excerpt="trecho divergente"),
            "excerpt does not match document offsets",
        ),
        (
            lambda case: case["evidence"][0].update(document_id="documento-inexistente"),
            "unknown evidence document_id",
        ),
        (lambda case: case.pop("evidence"), "evidence must be a non-empty list"),
        (lambda case: case.update(claim="   "), "claim must be a non-empty string"),
    ],
)
def test_evaluate_preflights_oracle_evidence_before_predicting(
    monkeypatch: pytest.MonkeyPatch,
    corrupt: Callable[[dict[str, Any]], object],
    message: str,
) -> None:
    cases = _preflight_cases()
    corrupt(cases[-1])
    calls: list[str] = []

    def predictor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(str(args[0]))
        raise AssertionError("predict must not run when oracle evidence is invalid")

    monkeypatch.setitem(RUNNER["evaluate"].__globals__, "predict", predictor)
    with pytest.raises(ValueError, match=message):
        RUNNER["evaluate"](
            cases,
            {case["case_id"]: "SUPPORTED" for case in cases},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    assert calls == []


def test_evaluate_rejects_unknown_mode_before_predicting(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = _preflight_cases()

    def predictor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("predict must not run for an unknown mode")

    monkeypatch.setitem(RUNNER["evaluate"].__globals__, "predict", predictor)
    with pytest.raises(ValueError, match="mode must be oracle or retrieval"):
        RUNNER["evaluate"](
            cases,
            {case["case_id"]: "SUPPORTED" for case in cases},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="orcale",
            vocabulary="judge2",
            iterations=10,
        )


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ('{"case_id":', "invalid JSON"),
        ("[]", "expected an object"),
        ('{"case_id":123}', "case_id must be a non-empty string"),
        ('{"case_id":" "}', "case_id must be a non-empty string"),
        ('{"case_id":"case-1"}\n\n', "blank lines are not allowed"),
        (
            '{"case_id":"case-1"}\n{"case_id":"case-1"}\n',
            "duplicate case_id",
        ),
    ],
)
def test_read_jsonl_rejects_malformed_case_records(
    tmp_path: Path, contents: str, message: str
) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["_read_jsonl"](path)


def test_read_jsonl_accepts_valid_case_records(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text('{"case_id":"case-1","claim":"A"}\n', encoding="utf-8")
    assert RUNNER["_read_jsonl"](path) == [{"case_id": "case-1", "claim": "A"}]


def _required_manifest_keys(function_name: str) -> set[str]:
    """Read the validator's literal required-key set without loading any data files."""
    runner_path = ROOT / "evals" / "ptbr" / "rgc_eval.py"
    tree = ast.parse(runner_path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "required" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, set) and all(isinstance(key, str) for key in value):
                return value
    raise AssertionError(f"required-key set not found in {function_name}")


def test_manifest_templates_match_runner_required_keys() -> None:
    """Keep blank JSON templates synchronized with the runner's exact schemas."""
    templates = (
        (
            ROOT / "docs" / "eval" / "templates" / "PROTOCOL-FREEZE.template.json",
            "validate_protocol_freeze",
        ),
        (
            ROOT / "docs" / "eval" / "templates" / "ANNOTATION-APPROVAL.template.json",
            "validate_annotation_approval",
        ),
    )
    for path, validator_name in templates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert set(payload) == _required_manifest_keys(validator_name)
        # A blank template must never look like an already granted human gate.
        assert payload["status"] == "DRAFT"
        if validator_name == "validate_annotation_approval":
            assert payload["cohen_kappa"] is None


def test_blank_annotation_template_is_rejected_by_operational_validator(
    tmp_path: Path,
) -> None:
    """An unfilled template must fail the runner's approval gate."""
    template = ROOT / "docs" / "eval" / "templates" / "ANNOTATION-APPROVAL.template.json"
    manifest_path = tmp_path / "annotation-approval.json"
    manifest_path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    agreement_path = tmp_path / "agreement.json"
    agreement_path.write_text(json.dumps({"method": "cohen_kappa_unweighted"}), encoding="utf-8")

    with pytest.raises(ValueError, match="status must be APPROVED"):
        RUNNER["validate_annotation_approval"](
            cases_path=tmp_path / "cases.jsonl",
            labels_path=tmp_path / "labels.jsonl",
            development_cases_path=tmp_path / "development-cases.jsonl",
            development_labels_path=tmp_path / "development-labels.jsonl",
            annotation_a_path=tmp_path / "annotation-a.jsonl",
            annotation_b_path=tmp_path / "annotation-b.jsonl",
            agreement_report_path=agreement_path,
            approval_manifest_path=manifest_path,
            adjudication_record_path=tmp_path / "adjudication.json",
        )


def test_blank_protocol_freeze_template_is_rejected_by_validator(tmp_path: Path) -> None:
    """A DRAFT freeze template must not pass the operational freeze gate."""
    protocol_dir = tmp_path / "docs" / "eval"
    protocol_dir.mkdir(parents=True)
    (protocol_dir / "PROTOCOL-GOLDEN-V1.md").write_text("Status: CONGELADO\n", encoding="utf-8")
    (protocol_dir / "PREREGISTRATION-RGC-v1.md").write_text(
        "**Estado:** [CONGELADO]\n", encoding="utf-8"
    )
    (protocol_dir / "RUNNER-RGC-v1.md").write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_dir = tmp_path / "evals" / "ptbr"
    runner_dir.mkdir(parents=True)
    (runner_dir / "rgc_eval.py").write_text("# synthetic validator fixture\n", encoding="utf-8")
    manifest_path = protocol_dir / "PROTOCOL-FREEZE.json"
    template_path = ROOT / "docs" / "eval" / "templates" / "PROTOCOL-FREEZE.template.json"
    manifest_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(ValueError, match="freeze manifest status must be FROZEN"):
        RUNNER["validate_protocol_freeze"](root=tmp_path)


@pytest.mark.parametrize(
    ("cited", "cluster", "message"),
    [
        (["syn:a+syn:b"], "syn:a+syn:b", "not a canonical article ID"),
        (["Syn:A"], "Syn:A", "not a canonical article ID"),
        (["syn:a", "syn:b"], "bundle:syn:b+syn:a", "unique, sorted IDs"),
        (["syn:a"], "component:syn:a", "not a canonical article ID"),
    ],
)
def test_hidden_partition_enforces_the_article_id_grammar(
    cited: list[str], cluster: str, message: str
) -> None:
    case = _case("grammar", "O cliente fictício pode cancelar.", "Art. 2º")
    case["cited_article_ids"] = cited
    case["bootstrap_cluster_id"] = cluster
    with pytest.raises(ValueError, match=message):
        RUNNER["evaluate"](
            [case],
            {"grammar": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
            partition="hidden",
        )


def test_runner_uses_the_shared_article_id_validator() -> None:
    from evals.ptbr import rgc_ids

    assert RUNNER["require_article_id"].__code__ is rgc_ids.require_article_id.__code__
    assert RUNNER["cluster_members"].__code__ is rgc_ids.cluster_members.__code__
