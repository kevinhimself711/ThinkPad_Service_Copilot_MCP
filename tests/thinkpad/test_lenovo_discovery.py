from src.thinkpad.lenovo import (
    build_recommend_manual_url,
    extract_manual_candidates,
    extract_product_guid_chain,
)


def test_extract_product_guid_chain_from_lenovo_product_html():
    html = (
        '"Guid":"2AA808DB-F88D-405E-A583-56AEA488D4CF",'
        '"Images":"https://download.lenovo.com/images/thinkpad.jpg",'
        '"ParentGuids":["83ABF382-A2F1-4761-A51E-E92E4AE75D1B",'
        '"5B1D3F6E-67A6-4537-BF07-B0A1F6C07ED3"]'
    )

    assert extract_product_guid_chain(html) == [
        "83ABF382-A2F1-4761-A51E-E92E4AE75D1B",
        "5B1D3F6E-67A6-4537-BF07-B0A1F6C07ED3",
        "2AA808DB-F88D-405E-A583-56AEA488D4CF",
    ]


def test_build_recommend_manual_url_contains_encoded_guid_chain():
    url = build_recommend_manual_url(["GUID-1", "GUID-2"])

    assert "recommendmanual" in url
    assert "pids=GUID-1,GUID-2" in url
    assert "remove-count-limit=true" in url


def test_extract_manual_candidates_filters_to_official_lenovo_documents():
    payload = {
        "userGuide": {
            "pdfs": [
                {
                    "title": "(English) User Guide",
                    "docid": "UM1",
                    "url": "https://download.lenovo.com/pccbbs/mobiles_pdf/user_guide.pdf",
                    "language": "en",
                }
            ]
        },
        "hardwareMaintenanceManual": {
            "pdfs": [
                {
                    "title": "(English) Hardware Maintenance Manual - ThinkPad T14 Gen 2",
                    "docid": "UM2",
                    "url": "https://download.lenovo.com/pccbbs/mobiles_pdf/t14_gen2_hmm_en.pdf",
                    "language": "en",
                    "updated": "2023-08-30T04:23:56.000+00:00",
                },
                {
                    "title": "Mirror copy",
                    "docid": "BAD",
                    "url": "https://example.com/t14_gen2_hmm_en.pdf",
                    "language": "en",
                },
            ]
        },
    }

    candidates = extract_manual_candidates(payload)

    assert len(candidates) == 2
    hmm = [candidate for candidate in candidates if candidate.is_hmm]
    assert len(hmm) == 1
    assert hmm[0].docid == "UM2"
