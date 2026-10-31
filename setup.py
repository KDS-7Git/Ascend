"""Bundle the canonical pack and web sources into both wheel distributions."""

from pathlib import Path
from shutil import copytree, rmtree

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        super().run()
        root = Path(__file__).parent
        for source, target in (("web", "web"), ("packs/community", "community")):
            destination = Path(self.build_lib) / "ascend" / target
            if destination.exists():
                rmtree(destination)
            copytree(root / source, destination)


setup(cmdclass={"build_py": BuildPy})
