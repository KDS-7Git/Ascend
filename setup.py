"""Bundle the canonical pack and web sources into both wheel distributions."""
from pathlib import Path
from shutil import copytree

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        super().run()
        root = Path(__file__).parent
        for source, target in (("web", "web"), ("packs/community", "community")):
            copytree(root / source, Path(self.build_lib) / "ascend" / target, dirs_exist_ok=True)


setup(cmdclass={"build_py": BuildPy})
