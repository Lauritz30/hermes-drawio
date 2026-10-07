"""Registration tests — what ``register(ctx)`` wires into Hermes."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.plugin import FakeCtx, PLUGIN_ROOT, load_plugin, parse_provides_tools

plugin = load_plugin()
settings = plugin.drawio.settings


class RegisterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = FakeCtx()
        plugin.register(self.ctx)
        self.addCleanup(settings.set_drawio_path, None)

    def test_every_schema_is_registered_as_a_drawio_tool(self) -> None:
        schema_names = {schema["name"] for schema in plugin.schemas.TOOL_SCHEMAS}
        self.assertEqual(set(self.ctx.tools), schema_names)
        for name, entry in self.ctx.tools.items():
            with self.subTest(tool=name):
                self.assertEqual(entry["toolset"], plugin.TOOLSET)
                self.assertEqual(entry["schema"]["name"], name)
                self.assertTrue(callable(entry["handler"]))
                self.assertIn("description", entry["schema"])
                self.assertIn("parameters", entry["schema"])

    def test_the_manifest_declares_exactly_the_registered_tools(self) -> None:
        declared = set(parse_provides_tools((PLUGIN_ROOT / "plugin.yaml").read_text(encoding="utf-8")))
        self.assertEqual(declared, set(self.ctx.tools))

    def test_no_hooks_are_registered(self) -> None:
        self.assertEqual(self.ctx.hooks, {})

    def test_slash_command_is_registered(self) -> None:
        self.assertEqual(sorted(self.ctx.commands), ["drawio"])
        entry = self.ctx.commands["drawio"]
        self.assertTrue(callable(entry["handler"]))
        self.assertTrue(entry["description"])

    def test_the_cli_command_tree_is_registered(self) -> None:
        self.assertIn("drawio", self.ctx.cli_commands)
        self.assertTrue(callable(self.ctx.cli_commands["drawio"]["setup_fn"]))
        self.assertTrue(callable(self.ctx.cli_commands["drawio"]["handler_fn"]))

    def test_bundled_skills_are_registered(self) -> None:
        expected = {path.parent.name for path in plugin.SKILLS_DIR.glob("*/SKILL.md")}
        self.assertTrue(expected)
        self.assertEqual(set(self.ctx.skills), expected)
        for path in self.ctx.skills.values():
            self.assertTrue(path.exists())

    def test_a_schema_handler_mismatch_fails_registration_loudly(self) -> None:
        incomplete = dict(plugin.drawio.tools.HANDLERS)
        incomplete.pop("drawio_status")
        with mock.patch.object(plugin, "HANDLERS", incomplete):
            with self.assertRaisesRegex(RuntimeError, "drawio_status"):
                plugin.register(FakeCtx())

    def test_drawio_path_setting_is_honoured(self) -> None:
        ctx = FakeCtx(config={"drawio_path": "/Applications/draw.io.app/Contents/MacOS/draw.io"})
        plugin.register(ctx)
        self.assertEqual(settings.drawio_path_override(), "/Applications/draw.io.app/Contents/MacOS/draw.io")


class SurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = FakeCtx()
        plugin.register(self.ctx)
        self.addCleanup(settings.set_drawio_path, None)

    def test_slash_command_usage(self) -> None:
        self.assertIn("Usage: /drawio", self.ctx.commands["drawio"]["handler"](""))

    def test_slash_command_status(self) -> None:
        text = self.ctx.commands["drawio"]["handler"]("status")
        self.assertIn("draw.io CLI:", text)

    def test_slash_command_missing_file(self) -> None:
        self.assertEqual("Missing file path.", self.ctx.commands["drawio"]["handler"]("open"))

    def test_cli_tree_prints_status(self) -> None:
        parser = argparse.ArgumentParser(prog="hermes")
        subparsers = parser.add_subparsers(dest="command")
        drawio_parser = subparsers.add_parser("drawio")
        self.ctx.cli_commands["drawio"]["setup_fn"](drawio_parser)
        args = parser.parse_args(["drawio", "status"])
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            args.func(args)
        self.assertIn("draw.io", buf.getvalue())

    def test_a_status_tool_call_returns_json(self) -> None:
        handler = self.ctx.tools["drawio_status"]["handler"]
        result = handler({})
        payload = json.loads(result)
        self.assertTrue(payload["ok"])
        self.assertIn("Shapes:", payload["summary"])
        self.assertIn("cliAvailable", payload["data"])


if __name__ == "__main__":
    unittest.main()
