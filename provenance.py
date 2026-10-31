"""Provenance helpers shared by the notebooks.

Every notebook that writes data records which code (git tag and commit), which notebook and which
Python environment produced it, and adds one entry to manifests/data_versions.json in the bucket.
That index links each dataset version to the code version that made it and to the inputs it was built from.

The notebooks download this file from the same git tag as requirements.txt, so it is pinned too.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata

INDEX_PATH = "manifests/data_versions.json"
RUN_INFO = {}
_FREEZE = ""

# One random seed for the whole project. start_run() applies it and records it in every manifest.
# Also pass it explicitly wherever a library takes one, e.g. random_state=SEED in pandas and scikit-learn.
SEED = 42


def set_seeds(seed=SEED):
    """Seed Python's and NumPy's random generators, and PyTorch / TensorFlow if they are already imported.
    In a training notebook, call it again after importing those libraries."""
    import random
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    if "torch" in sys.modules:
        sys.modules["torch"].manual_seed(seed)          # also seeds the GPU
    if "tensorflow" in sys.modules:
        sys.modules["tensorflow"].random.set_seed(seed)
    return seed


def utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _tag_commit(repo_url, tag):
    """The commit a git tag points to, read from GitHub (no clone needed)."""
    out = subprocess.run(["git", "ls-remote", repo_url, f"refs/tags/{tag}*"],
                         capture_output=True, text=True, check=True).stdout
    refs = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        refs[ref] = sha
    # an annotated tag has its own ID; the line ending in ^{} gives the commit it points to
    return refs.get(f"refs/tags/{tag}^{{}}") or refs.get(f"refs/tags/{tag}")


def start_run(repo_url, code_version, notebook, seed=SEED):
    """Record the code version, Python environment and random seed of this run, and apply the seed.
    Call once, near the top of a notebook."""
    global _FREEZE
    set_seeds(seed)
    commit = _tag_commit(repo_url, code_version)
    assert commit, f"Tag {code_version} was not found on GitHub. Create it (git tag {code_version}; git push --tags) before running."

    # the full list of installed packages (a pip freeze), so the environment can be rebuilt exactly
    names = set()
    for d in metadata.distributions():
        name = d.metadata["Name"]
        if name:
            names.add(f"{name}=={d.version}")
    _FREEZE = "\n".join(sorted(names, key=str.lower)) + "\n"
    env_sha = sha256(_FREEZE)

    RUN_INFO.clear()
    RUN_INFO.update({
        "code_version": code_version,
        "code_commit": commit,
        "notebook": notebook,
        "python": sys.version.split()[0],
        "environment_sha256": env_sha,
        "environment_file": f"manifests/environments/{env_sha[:12]}.txt",
        "random_seed": seed,
    })
    print(f"Code {code_version} ({commit[:8]}) | notebook {notebook} | Python {RUN_INFO['python']} | "
          f"environment {env_sha[:12]} | seed {seed}")
    return dict(RUN_INFO)


def table_version(bq, table):
    """Row count and content fingerprint of a BigQuery table or view (same fingerprint as notebooks 09 and 10)."""
    from google.cloud import bigquery
    cfg = bigquery.QueryJobConfig(maximum_bytes_billed=1_000_000_000)
    r = bq.query(f"SELECT COUNT(*) AS n, CAST(BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(t))) AS STRING) AS fp "
                 f"FROM `{table}` t", job_config=cfg).to_dataframe().iloc[0]
    return {"table": table.split(".", 1)[1], "rows": int(r["n"]), "fingerprint": r["fp"]}


def register(bucket, dataset, version, outputs, parents=(), manifest_path=None):
    """Add one entry to the index of dataset versions (manifests/data_versions.json).

    outputs: the files ({"file", "bytes", "sha256"}) or tables (from table_version) this version consists of
    parents: the inputs it was built from (same shapes, or a short text such as a source commit)
    """
    assert RUN_INFO, "Call start_run() first"

    env = bucket.blob(RUN_INFO["environment_file"])
    if not env.exists():
        env.upload_from_string(_FREEZE, content_type="text/plain", if_generation_match=0)

    entry = {"dataset": dataset, "version": str(version), "created_utc": utc_stamp(),
             "manifest": manifest_path, "outputs": list(outputs), "parents": list(parents), **RUN_INFO}

    index = bucket.blob(INDEX_PATH)
    if index.exists():
        index.reload()
        generation = index.generation
        entries = json.loads(index.download_as_text(if_generation_match=generation))
    else:
        generation, entries = 0, []

    same = [e for e in entries if e["dataset"] == dataset and e["version"] == str(version)
            and e["code_commit"] == RUN_INFO["code_commit"]]
    if same:
        print(f"{dataset} {version}: already in the index for this code version")
        return same[-1]

    entries.append(entry)
    # if_generation_match: fails instead of overwriting if someone else changed the index meanwhile
    index.upload_from_string(json.dumps(entries, indent=1), content_type="application/json",
                             if_generation_match=generation)
    print(f"{dataset} {version}: added to {INDEX_PATH} ({len(entries)} entries)")
    return entry
