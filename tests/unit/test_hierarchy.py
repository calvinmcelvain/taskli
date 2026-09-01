import pytest

from taskli.hierarchy import (
    ancestor_chain,
    child_list_names,
    descendant_list_names,
    parent_list_name,
)


class TestListHierarchyHelpers:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("work", None),
            ("work.meetings", "work"),
            ("work.meetings.notes", "work.meetings"),
        ],
        ids=["top-level", "nested", "deeply-nested"],
    )
    def test_parent_list_name(self, name, expected):
        assert parent_list_name(name) == expected

    def test_child_list_names_excludes_grandchildren(self):
        names = [
            "work",
            "work.meetings",
            "work.meetings.notes",
            "personal",
        ]

        assert child_list_names("work", names) == ["work.meetings"]

    def test_descendant_list_names_includes_all_depths(self):
        names = [
            "work",
            "work.meetings",
            "work.meetings.notes",
            "personal",
        ]

        assert descendant_list_names("work", names) == [
            "work.meetings",
            "work.meetings.notes",
        ]

    def test_descendant_list_names_excludes_unrelated_sibling(self):
        names = ["work", "workshop"]

        assert descendant_list_names("work", names) == []

    def test_ancestor_chain_nested(self):
        assert ancestor_chain("a.b.c") == ["a", "a.b"]

    def test_ancestor_chain_top_level(self):
        assert ancestor_chain("a") == []
