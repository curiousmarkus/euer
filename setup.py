"""Kopiert beim Build die kanonische Skill-Quelle in das Python-Paket."""

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithSkill(build_py):
    def run(self):
        super().run()
        source = Path(__file__).parent / "docs" / "skills" / "euer-buchhaltung"
        target = Path(self.build_lib) / "euercli" / "assets" / "skill"
        shutil.copytree(source, target, dirs_exist_ok=True)

    def get_outputs(self, include_bytecode=1):
        outputs = super().get_outputs(include_bytecode)
        source = Path(__file__).parent / "docs" / "skills" / "euer-buchhaltung"
        target = Path(self.build_lib) / "euercli" / "assets" / "skill"
        outputs.extend(
            str(target / path.relative_to(source)) for path in source.rglob("*") if path.is_file()
        )
        return outputs


setup(cmdclass={"build_py": BuildWithSkill})
