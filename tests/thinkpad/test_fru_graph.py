from src.thinkpad.fru_graph import build_fru_dependency_graph

MANUAL_ID = "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm"
SOURCE_URL = "https://download.lenovo.com/pccbbs/mobiles_pdf/tp_x1_carbon_gen9_x1_yoga_gen6_hmm_en.pdf"


def _citation(fru_id: str, page: int) -> dict:
    return {
        "manual_id": MANUAL_ID,
        "source_url": SOURCE_URL,
        "page_start": page,
        "page_end": page,
        "section": f"{fru_id} Test FRU",
        "section_id": fru_id,
    }


def _procedure(fru_id: str, name: str, page: int) -> dict:
    return {
        "procedure_id": f"{MANUAL_ID}_fru_{fru_id}",
        "manual_id": MANUAL_ID,
        "fru_id": fru_id,
        "fru_name": name,
        "steps": [f"Remove {name}."],
        "prerequisites": [],
        "warnings": [],
        "related_image_ids": [],
        "citation": _citation(fru_id, page),
    }


def _edge(source: str, required: str, page: int = 70) -> dict:
    return {
        "manual_id": MANUAL_ID,
        "source_fru_id": source,
        "required_fru_id": required,
        "relation_type": "FRU_REQUIRES_PREREQUISITE_FRU",
        "citation": _citation(source, page),
    }


def test_dependency_graph_preserves_direct_prerequisite_citation() -> None:
    graph = build_fru_dependency_graph(
        procedures=[
            _procedure("1010", "Base cover assembly", 67),
            _procedure("1050", "Built-in battery", 70),
        ],
        dependency_edges=[_edge("1050", "1010")],
    )

    result = graph.get_dependency_chain(MANUAL_ID, "1050")

    assert result["found"] is True
    assert result["target"]["fru_id"] == "1050"
    assert result["dependency_chain"][0]["fru_id"] == "1010"
    assert result["dependency_chain"][0]["depth"] == 1
    assert result["dependency_chain"][0]["citation"]["page_start"] == 67
    assert result["edge_count"] == 1


def test_dependency_graph_returns_deterministic_multi_hop_chain() -> None:
    graph = build_fru_dependency_graph(
        procedures=[
            _procedure("1010", "Base cover assembly", 67),
            _procedure("1020", "Battery pack", 68),
            _procedure("1080", "System board", 90),
        ],
        dependency_edges=[_edge("1080", "1020"), _edge("1020", "1010")],
    )

    result = graph.get_dependency_chain(MANUAL_ID, "1080")

    assert [item["fru_id"] for item in result["dependency_chain"]] == ["1020", "1010"]
    assert [item["depth"] for item in result["dependency_chain"]] == [1, 2]
    assert result["dependency_chain"][1]["edge_path"] == ["1080", "1020", "1010"]


def test_dependency_graph_reports_missing_prerequisite_node() -> None:
    graph = build_fru_dependency_graph(
        procedures=[_procedure("1050", "Built-in battery", 70)],
        dependency_edges=[_edge("1050", "1010")],
    )

    result = graph.get_dependency_chain(MANUAL_ID, "1050")

    assert result["dependency_chain"] == []
    assert result["missing_prerequisites"][0]["fru_id"] == "1010"
    assert result["missing_prerequisites"][0]["required_by"] == "1050"
    assert result["edge_count"] == 1


def test_dependency_graph_detects_cycles_without_recursing_forever() -> None:
    graph = build_fru_dependency_graph(
        procedures=[
            _procedure("1010", "Base cover assembly", 67),
            _procedure("1050", "Built-in battery", 70),
        ],
        dependency_edges=[_edge("1050", "1010"), _edge("1010", "1050")],
    )

    result = graph.get_dependency_chain(MANUAL_ID, "1050")

    assert result["cycle_detected"] is True
    assert result["cycles"][0]["path"] == ["1050", "1010", "1050"]
    assert [item["fru_id"] for item in result["dependency_chain"]] == ["1010"]


def test_dependency_graph_reports_missing_target() -> None:
    graph = build_fru_dependency_graph(procedures=[], dependency_edges=[])

    result = graph.get_dependency_chain(MANUAL_ID, "9999")

    assert result["found"] is False
    assert result["target"] == {"manual_id": MANUAL_ID, "fru_id": "9999"}
    assert result["dependency_chain"] == []
