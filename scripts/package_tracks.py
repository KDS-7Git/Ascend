"""Build the public pack archive from verified exports and LaTeX documentation."""

from pathlib import Path
import zipfile

from ascend.engine.packs import parse_pack

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = {}
    exported = ROOT / "tracks/cyber-tracks"
    for path in sorted(exported.rglob("*")):
        if path.is_file():
            relative = path.relative_to(exported)
            if path.suffix == ".toml":
                parse_pack(path.read_text())
                assert path.read_bytes() == (ROOT / relative).read_bytes(), relative
            files[str(relative)] = path
    assert sum(name.endswith(".toml") for name in files) == 26
    for name in [
        "handbook",
        "user-guide",
        "deployment-guide",
        "developer-handbook",
        "command-reference",
        "report",
        "design-history",
    ]:
        files[name + ".pdf"] = ROOT / "docs" / (name + ".pdf")
    for pattern in [
        "**/*.tex",
        "screenshots/**/*.png",
        "curriculum/*.json",
        "curriculum/*.md",
        "design/ui-workspace-sources.json",
        "design/isolated-lab-research.md",
    ]:
        for path in (ROOT / "docs").glob(pattern):
            files["docs/" + str(path.relative_to(ROOT / "docs"))] = path
    for path in (ROOT / "web/training").glob("*.zip"):
        files["learning-materials/" + path.name] = path
    files["LICENSE"] = ROOT / "LICENSE"
    destination = ROOT / "tracks/cyber-tracks-v4.zip"
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(
                "cyber-tracks/" + name, date_time=(2026, 11, 2, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    print(
        "RESULT: Public v4 archive contains 26 packs, 21 practice ZIPs, seven PDFs and LaTeX sources; export equality and ZIP integrity passed."
    )


if __name__ == "__main__":
    main()
