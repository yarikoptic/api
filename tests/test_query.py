"""Test API to query subjects from the Stardog graph who match user-specified criteria."""

import httpx
import pytest
from fastapi import HTTPException

from app.api import crud


@pytest.fixture()
def test_data():
    """Create toy data for two datasets for testing."""
    return [
        {
            "dataset": "http://neurobagel.org/vocab/qpn",
            "dataset_name": "QPN",
            "num_matching_subjects": 5,
            "subject_file_paths": [
                "/my/happy/path/sub-0051/to/session-01",
                "/my/happy/path/sub-0653/to/session-01",
                "/my/happy/path/sub-1063/to/session-01",
                "/my/happy/path/sub-1113/to/session-01",
                "/my/happy/path/sub-1170/to/session-01",
            ],
            "image_modals": [
                "http://purl.org/nidash/nidm#T1Weighted",
                "http://purl.org/nidash/nidm#T2Weighted",
            ],
        },
        {
            "dataset": "http://neurobagel.org/vocab/ppmi",
            "dataset_name": "PPMI",
            "num_matching_subjects": 3,
            "subject_file_paths": [
                "/my/happy/path/sub-719238/to/session-01",
                "/my/happy/path/sub-719341/to/session-01",
                "/my/happy/path/sub-719369/to/session-01",
                "/my/happy/path/sub-719238/to/session-02",
                "/my/happy/path/sub-719341/to/session-02",
            ],
            "image_modals": [
                "http://purl.org/nidash/nidm#FlowWeighted",
                "http://purl.org/nidash/nidm#T1Weighted",
            ],
        },
    ]


@pytest.fixture
def mock_successful_get(test_data):
    """Mock get function that returns non-empty query results."""

    async def mockreturn(
        min_age,
        max_age,
        sex,
        diagnosis,
        is_control,
        min_num_sessions,
        assessment,
        image_modal,
    ):
        return test_data

    return mockreturn


@pytest.fixture
def mock_invalid_get():
    """Mock get function that does not return any response (for testing invalid parameter values)."""

    async def mockreturn(
        min_age,
        max_age,
        sex,
        diagnosis,
        is_control,
        min_num_sessions,
        assessment,
        image_modal,
    ):
        return None

    return mockreturn


def test_start_app_without_environment_vars_fails(test_app, monkeypatch):
    """Given non-existing USERNAME and PASSWORD environment variables, raises an informative RuntimeError."""
    monkeypatch.delenv("USERNAME", raising=False)
    monkeypatch.delenv("PASSWORD", raising=False)

    with pytest.raises(RuntimeError) as e_info:
        with test_app:
            pass
    assert (
        "could not find the USERNAME and / or PASSWORD environment variables"
        in str(e_info.value)
    )


def test_app_with_invalid_environment_vars(test_app, monkeypatch):
    """Given invalid environment variables, returns a 401 status code."""
    monkeypatch.setenv("USERNAME", "something")
    monkeypatch.setenv("PASSWORD", "cool")

    def mock_httpx_post(**kwargs):
        return httpx.Response(status_code=401)

    monkeypatch.setattr(httpx, "post", mock_httpx_post)
    response = test_app.get("/query/")
    assert response.status_code == 401


def test_get_all(test_app, mock_successful_get, monkeypatch):
    """Given no input for the sex parameter, returns a 200 status code and a non-empty list of results (should correspond to all subjects in graph)."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get("/query/")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize(
    "valid_min_age, valid_max_age",
    [(30.5, 60), (23, 23)],
)
def test_get_valid_age_range(
    test_app, mock_successful_get, valid_min_age, valid_max_age, monkeypatch
):
    """Given a valid age range, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(
        f"/query/?min_age={valid_min_age}&max_age={valid_max_age}"
    )
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize(
    "age_keyval",
    ["min_age=20.75", "max_age=50"],
)
def test_get_valid_age_single_bound(
    test_app, mock_successful_get, age_keyval, monkeypatch
):
    """Given only a valid lower/upper age bound, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(f"/query/?{age_keyval}")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize(
    "invalid_min_age, invalid_max_age",
    [
        ("forty", "fifty"),
        (33, 21),
        (-42.5, -40),
    ],
)
def test_get_invalid_age(
    test_app, mock_invalid_get, invalid_min_age, invalid_max_age, monkeypatch
):
    """Given an invalid age range, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_invalid_get)
    response = test_app.get(
        f"/query/?min_age={invalid_min_age}&max_age={invalid_max_age}"
    )
    assert response.status_code == 422


@pytest.mark.parametrize("valid_sex", ["male", "female", "other"])
def test_get_valid_sex(test_app, mock_successful_get, valid_sex, monkeypatch):
    """Given a valid sex string, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(f"/query/?sex={valid_sex}")
    assert response.status_code == 200
    assert response.json() != []


def test_get_invalid_sex(test_app, mock_invalid_get, monkeypatch):
    """Given an invalid sex string (i.e., anything other than ["male", "female", None]), returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_invalid_get)
    response = test_app.get("/query/?sex=apple")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "valid_diagnosis", ["snomed:35489007", "snomed:49049000"]
)
def test_get_valid_diagnosis(
    test_app, mock_successful_get, valid_diagnosis, monkeypatch
):
    """Given a valid diagnosis, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(f"/query/?diagnosis={valid_diagnosis}")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize(
    "invalid_diagnosis", ["sn0med:35489007", "apple", ":123456"]
)
def test_get_invalid_diagnosis(
    test_app, mock_invalid_get, invalid_diagnosis, monkeypatch
):
    """Given an invalid diagnosis, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_invalid_get)
    response = test_app.get(f"/query/?diagnosis={invalid_diagnosis}")
    assert response.status_code == 422


@pytest.mark.parametrize("valid_iscontrol", [True, False])
def test_get_valid_iscontrol(
    test_app, mock_successful_get, valid_iscontrol, monkeypatch
):
    """Given a valid is_control value, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(f"/query/?is_control={valid_iscontrol}")
    assert response.status_code == 200
    assert response.json() != []


def test_get_invalid_iscontrol(test_app, mock_invalid_get, monkeypatch):
    """Given a non-boolean is_control value, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_invalid_get)
    response = test_app.get("/query/?is_control=apple")
    assert response.status_code == 422


def test_get_invalid_control_diagnosis_pair(
    test_app, mock_invalid_get, monkeypatch
):
    """Given a non-default diagnosis value and is_control value of True, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_invalid_get)
    response = test_app.get(
        "/query/?diagnosis=snomed:35489007&is_control=True"
    )
    assert response.status_code == 422
    assert (
        "Subjects cannot both be healthy controls and have a diagnosis"
        in response.text
    )


@pytest.mark.parametrize("valid_min_num_sessions", [1, 2, 4, 7])
def test_get_valid_min_num_sessions(
    test_app, mock_successful_get, valid_min_num_sessions, monkeypatch
):
    """Given a valid minimum number of imaging sessions, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(
        f"/query/?min_num_sessions={valid_min_num_sessions}"
    )
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize("invalid_min_num_sessions", [0, -3, "apple"])
def test_get_invalid_min_num_sessions(
    test_app, mock_invalid_get, invalid_min_num_sessions, monkeypatch
):
    """Given an invalid minimum number of imaging sessions, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_invalid_get)
    response = test_app.get(
        f"/query/?min_num_sessions={invalid_min_num_sessions}"
    )
    response.status_code = 422


def test_get_valid_assessment(test_app, mock_successful_get, monkeypatch):
    """Given a valid assessment, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get("/query/?assessment=bg:cogAtlas-1234")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize(
    "invalid_assessment", ["bg01:cogAtlas-1234", "cogAtlas-1234"]
)
def test_get_invalid_assessment(
    test_app, mock_invalid_get, invalid_assessment, monkeypatch
):
    """Given an invalid assessment, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_invalid_get)
    response = test_app.get(f"/query/?assessment={invalid_assessment}")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "valid_available_image_modal",
    [
        "nidm:DiffusionWeighted",
        "nidm:EEG",
        "nidm:FlowWeighted",
        "nidm:T1Weighted",
        "nidm:T2Weighted",
    ],
)
def test_get_valid_available_image_modal(
    test_app, mock_successful_get, valid_available_image_modal, monkeypatch
):
    """Given a valid and available image modality, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(
        f"/query/?image_modal={valid_available_image_modal}"
    )
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize(
    "valid_unavailable_image_modal",
    ["nidm:Flair", "owl:sameAs", "bg:FlowWeighted", "snomed:something"],
)
def test_get_valid_unavailable_image_modal(
    test_app, valid_unavailable_image_modal, monkeypatch
):
    """Given a valid, pre-defined, and unavailable image modality, returns a 200 status code and an empty list of results."""

    async def mock_get(
        min_age,
        max_age,
        sex,
        diagnosis,
        is_control,
        min_num_sessions,
        assessment,
        image_modal,
    ):
        return []

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(
        f"/query/?image_modal={valid_unavailable_image_modal}"
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "invalid_image_modal", ["2nim:EEG", "apple", "some_thing:cool"]
)
def test_get_invalid_image_modal(
    test_app, mock_invalid_get, invalid_image_modal, monkeypatch
):
    """Given an invalid image modality, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_invalid_get)
    response = test_app.get(f"/query/?image_modal={invalid_image_modal}")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "undefined_prefix_image_modal",
    ["dbo:abstract", "sex:apple", "something:cool"],
)
def test_get_undefined_prefix_image_modal(
    test_app, undefined_prefix_image_modal, monkeypatch
):
    """Given a valid and undefined prefix image modality, returns a 500 status code."""

    async def mock_get(
        min_age,
        max_age,
        sex,
        diagnosis,
        is_control,
        min_num_sessions,
        assessment,
        image_modal,
    ):
        raise HTTPException(500)

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(
        f"/query/?image_modal={undefined_prefix_image_modal}"
    )
    assert response.status_code == 500
