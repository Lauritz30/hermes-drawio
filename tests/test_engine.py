"""Engine tests — end-to-end diagram create/add/update/delete/list/read/write round-trips."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from drawio import engine
from drawio.parse import parse_diagram, validate_xml
from drawio.serialize import serialize_diagram


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hermes-drawio-")
        self.dir = Path(self._tmp.name)
        self.path = str(self.dir / "diagram.drawio")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _create(self, **overrides):
        opts = {
            "path": self.path,
            "title": "Flow",
            "nodes": [
                {"id": "a", "label": "Start", "shape": "terminator"},
                {"id": "b", "label": "Do work", "shape": "rounded"},
                {"id": "c", "label": "Done", "shape": "terminator"},
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "c", "label": "next"},
            ],
            "open": False,
        }
        opts.update(overrides)
        return engine.create_diagram(opts, task_id="default")

    def test_create_diagram_writes_valid_drawio(self) -> None:
        result = self._create()
        self.assertEqual(result["nodes"], 3)
        self.assertEqual(result["edges"], 2)
        self.assertEqual(result["lanes"], 0)
        self.assertTrue(os.path.isfile(self.path))
        xml = Path(self.path).read_text(encoding="utf-8")
        self.assertEqual(validate_xml(xml), True)
        self.assertIn('host="hermes-drawio"', xml)

    def test_create_round_trips_through_the_ir(self) -> None:
        self._create()
        xml = Path(self.path).read_text(encoding="utf-8")
        diagram = parse_diagram(xml)
        self.assertEqual(len(diagram.pages), 1)
        page = diagram.pages[0]
        self.assertEqual(page.name, "Flow")
        labels = {c.value for c in page.cells if c.value}
        self.assertEqual(labels, {"Start", "Do work", "Done", "next"})

    def test_create_with_swimlanes(self) -> None:
        result = self._create(
            lanes=[
                {"id": "cust", "name": "Customer", "role": "customer"},
                {"id": "back", "name": "Backend", "role": "backend"},
            ],
            nodes=[
                {"id": "a", "label": "Ask", "lane": "cust"},
                {"id": "b", "label": "Answer", "lane": "back"},
            ],
            edges=[{"source": "a", "target": "b"}],
        )
        self.assertEqual(result["lanes"], 2)
        diagram = parse_diagram(Path(self.path).read_text(encoding="utf-8"))
        page = diagram.pages[0]
        swimlanes = [c for c in page.cells if c.vertex and "swimlane" in (c.style or "")]
        self.assertEqual(len(swimlanes), 2)
        # Nodes are parented to their lane.
        lane_ids = {c.id for c in swimlanes}
        node_a = next(c for c in page.cells if c.id == "a")
        self.assertIn(node_a.parent, lane_ids)

    def test_add_cells(self) -> None:
        self._create()
        result = engine.add_cells(
            {
                "path": self.path,
                "nodes": [{"id": "d", "label": "Extra"}],
                "edges": [{"source": "c", "target": "d"}],
                "open": False,
            },
            task_id="default",
        )
        self.assertEqual(result["nodes"], 1)
        self.assertEqual(result["edges"], 1)

    def test_add_cells_requires_existing_file(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "No diagram"):
            engine.add_cells({"path": str(self.dir / "missing.drawio"), "open": False})

    def test_list_cells(self) -> None:
        self._create()
        listing = engine.list_cells({"path": self.path}, task_id="default")
        kinds = {c["kind"] for c in listing["cells"]}
        self.assertEqual(kinds, {"root", "layer", "node", "edge"})
        ids = {c["id"] for c in listing["cells"]}
        self.assertEqual(ids, {"0", "1", "a", "b", "c", "e1", "e2"})

    def test_update_cells(self) -> None:
        self._create()
        result = engine.update_cells(
            {"path": self.path, "cells": [{"id": "b", "label": "Renamed", "shape": "diamond"}]},
            task_id="default",
        )
        self.assertEqual(result["updated"], 1)
        diagram = parse_diagram(Path(self.path).read_text(encoding="utf-8"))
        cell_b = next(c for c in diagram.pages[0].cells if c.id == "b")
        self.assertEqual(cell_b.value, "Renamed")
        self.assertIn("rhombus", cell_b.style or "")

    def test_update_unknown_cell_raises(self) -> None:
        self._create()
        with self.assertRaisesRegex(RuntimeError, "not found"):
            engine.update_cells({"path": self.path, "cells": [{"id": "zzz"}]}, task_id="default")

    def test_delete_cells_removes_connected_edges(self) -> None:
        self._create()
        result = engine.delete_cells({"path": self.path, "ids": ["b"]}, task_id="default")
        # b plus the two edges touching b are removed.
        self.assertEqual(result["removed"], 3)
        listing = engine.list_cells({"path": self.path}, task_id="default")
        ids = {c["id"] for c in listing["cells"]}
        self.assertNotIn("b", ids)
        self.assertNotIn("e1", ids)
        self.assertNotIn("e2", ids)

    def test_read_write_xml(self) -> None:
        self._create()
        original = engine.read_xml({"path": self.path}, task_id="default")["xml"]
        engine.write_xml({"path": self.path, "xml": original}, task_id="default")
        again = engine.read_xml({"path": self.path}, task_id="default")["xml"]
        self.assertEqual(original, again)

    def test_write_xml_rejects_malformed_xml(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not well-formed"):
            engine.write_xml({"path": self.path, "xml": "<not-closed>"}, task_id="default")

    def test_serialize_parse_round_trip_preserves_geometry(self) -> None:
        self._create()
        diagram = parse_diagram(Path(self.path).read_text(encoding="utf-8"))
        again = parse_diagram(serialize_diagram(diagram))
        self.assertEqual(
            {(c.id, c.value) for c in diagram.pages[0].cells},
            {(c.id, c.value) for c in again.pages[0].cells},
        )


if __name__ == "__main__":
    unittest.main()
