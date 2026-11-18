"""
Engine test (no GUI).  Usage:  python tests/test_core.py <folder with DICOM series> [N]

Checks that
- series are grouped and incompatible ones are excluded,
- every output slice equals the direct sum/average of the inputs (within rounding),
- UIDs / Series# / ImageType / window are written as expected.
"""
import os
import sys
import tempfile
import time
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np
import pydicom

import fused_core as fc


def main():
    root = sys.argv[1]
    n_max = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    t = time.time()
    infos = fc.scan_folder(root)
    print(f"scan: {len(infos)} series in {time.time() - t:.1f} s")
    usable = [i for i in infos if not i.unusable_reason]
    ref = max(usable, key=lambda r: sum(fc.check_compatible(r, o).ok for o in usable))
    pool = []
    for i in infos:
        c = fc.check_compatible(ref, i)
        print(f"  {i.label:12s} n={i.n:4d}  {'OK ' if c.ok else 'NG '} {c.errors or ''} {c.warnings or ''}")
        if c.ok:
            pool.append(i)
    pool = pool[:n_max]
    jobs = (fc.build_jobs(len(pool), [1, 2, len(pool)], "first", "avg")
            + fc.build_jobs(len(pool), [2], "blocks", "sum"))
    out = tempfile.mkdtemp(prefix="fused_test_")
    try:
        t = time.time()
        fc.run_jobs(pool, jobs, out)
        print(f"run: {len(jobs)} jobs in {time.time() - t:.1f} s (workers={fc.default_workers()})")
        nz = pool[0].n
        for j in jobs:
            for z in (0, nz // 2, nz - 1):
                ds = pydicom.dcmread(os.path.join(out, j.name, f"IM_{z + 1:04d}.dcm"))
                got = ds.pixel_array * float(ds.RescaleSlope) + float(ds.RescaleIntercept)
                src = [pydicom.dcmread(pool[i].files[z]) for i in j.members]
                exp = sum(s.pixel_array * float(s.RescaleSlope) + float(s.RescaleIntercept) for s in src)
                if j.mode == "avg":
                    exp = exp / j.n
                err = float(np.abs(got - exp).max())
                assert err <= 0.5 * float(ds.RescaleSlope) + 1e-6, (j.name, z, err)
                assert ds.SOPInstanceUID == ds.file_meta.MediaStorageSOPInstanceUID
                assert list(ds.ImageType)[:2] == ["DERIVED", "SECONDARY"]
            print(f"  {j.name:14s} OK  Series#={ds.SeriesNumber}  WC/WW={ds.WindowCenter}/{ds.WindowWidth}")
        print("ALL TESTS PASSED")
    finally:
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    main()
