"""Tests for namespaced plugin ids (e.g. ``image_gen/openai``).

Background: dashboard frontend sends URL-encoded plugin names that may
contain a forward slash (``image_gen%2Fopenai``). Starlette decodes
``%2F``, so the bare ``{name}`` path parameter no longer matched and
the request fell into another route, yielding HTTP 405. Routes now use
``{name:path}`` and ``_validate_plugin_name`` permits embedded slashes
while still rejecting traversal segments.

Validation behaviour (upstream): leading/trailing slashes are normalised
away via ``str.strip("/")``; an empty result, a ``..`` traversal segment
or a backslash is rejected. Embedded single slashes (namespaces) pass.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from hermes_cli.web_server import _validate_plugin_name


@pytest.mark.parametrize(
    "name",
    [
        "image_gen",
        "image_gen/openai",
        "vendor/family/specific",
        "a-b_c.1",
    ],
)
def test_validate_plugin_name_accepts_namespaced(name: str) -> None:
    assert _validate_plugin_name(name) == name


@pytest.mark.parametrize(
    "name,expected",
    [
        ("/abs/path", "abs/path"),
        ("trailing/", "trailing"),
        ("/image_gen/openai/", "image_gen/openai"),
    ],
)
def test_validate_plugin_name_strips_outer_slashes(name: str, expected: str) -> None:
    # Leading/trailing slashes are normalised away rather than rejected.
    assert _validate_plugin_name(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "",
        "..",
        "../etc/passwd",
        "image_gen/../escape",
        "back\\slash",
    ],
)
def test_validate_plugin_name_rejects_unsafe(name: str) -> None:
    with pytest.raises(HTTPException) as exc:
        _validate_plugin_name(name)
    assert exc.value.status_code == 400
