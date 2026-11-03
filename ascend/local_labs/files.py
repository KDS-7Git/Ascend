"""The first small Linux audit exercise. Source bytes are never executed."""

import shutil

from ascend.local_labs.assets import AssetStore, atomic_json
from ascend.local_labs.catalog import DATA
from ascend.local_labs.checks import answer_check


class FileLab:
    def __init__(self, runtime):
        self.runtime = runtime

    def prepare(self, row):
        recipe = row["recipe"]
        target = self.runtime.runtime_dir(row)
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        store = AssetStore(self.runtime.cache)
        downloaded = 0
        for asset in recipe["assets"]:
            source, size = store.fetch(asset)
            downloaded += size
            if asset["role"] == "evidence":
                store.selected_zip(source, asset, target / "evidence.log")
            elif asset["role"] == "license":
                shutil.copyfile(source, target / "UPSTREAM-LICENSE.txt")
        shutil.copyfile(DATA / "audit-control.json", target / "benign-control.json")
        work = self.runtime.work_dir(row)
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not (work / "answers.json").exists():
            atomic_json(work / "answers.json", recipe["answer_template"])
            (work / "TASK.txt").write_text(recipe["instructions"] + "\n")
        row["files"] = {"evidence": str(target / "evidence.log"), "benign_control": str(target / "benign-control.json"), "answers": str(work / "answers.json")}
        return {"download_bytes": downloaded, "runtime_bytes": sum(p.stat().st_size for p in target.iterdir())}

    def check(self, row):
        return answer_check(self.runtime.read_work(row, "answers.json"))

    def alive(self, row):
        return (self.runtime.runtime_dir(row) / "evidence.log").is_file()

    def stop(self, row):
        pass  # Files use no persistent process; the attempt clock remains unchanged.

    def destroy(self, row):
        target = self.runtime.runtime_dir(row)
        if target.is_symlink():
            raise ValueError("Runtime directory is a symlink")
        if target.exists():
            shutil.rmtree(target)

    def submission(self, row):
        return {"answers": self.runtime.read_work(row, "answers.json")}
