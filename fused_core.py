# -*- coding: utf-8 -*-
"""
FusedAuto core engine (GUI-independent).

- scan_folder():      find DICOM files, group by SeriesInstanceUID, sort slices by position
- check_compatible(): geometry / acquisition checks against a reference series
- build_jobs():       create addition conditions (first-N, non-overlapping blocks, random, all)
- run_jobs():         compute all jobs slice-chunk by slice-chunk, reading every file only once,
                      and write each result as a new DICOM series
- compute_slice():    on-demand single-slice preview
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import math
import os
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

APP_NAME = "FusedAuto"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Ryusei Inamori"
APP_CONTACT = "mdai.inamori@gmail.com"
APP_URL = "https://github.com/ryusei-inamori/FusedMaker"
APP_DOI = ""   # set to the Zenodo concept DOI (e.g. "10.5281/zenodo.1234567") once it exists

CT_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.2"
MEDIA_STORAGE_DIRECTORY = "1.2.840.10008.1.3.10"

UNCOMPRESSED_LE = {
    "1.2.840.10008.1.2",      # Implicit VR Little Endian
    "1.2.840.10008.1.2.1",    # Explicit VR Little Endian
}

_HEADER_TAGS = [
    "SOPClassUID", "SeriesInstanceUID", "StudyInstanceUID", "FrameOfReferenceUID",
    "Modality", "ImageType", "SeriesNumber", "SeriesDescription", "ProtocolName",
    "PatientID", "PatientName", "ConvolutionKernel", "KVP", "XRayTubeCurrent", "Exposure",
    "SliceThickness", "ReconstructionDiameter", "Rows", "Columns", "PixelSpacing",
    "ImageOrientationPatient", "ImagePositionPatient", "InstanceNumber",
    "AcquisitionDate", "AcquisitionTime", "SeriesDate", "SeriesTime", "ContentTime",
    "SamplesPerPixel", "BitsAllocated", "PixelRepresentation", "WindowCenter", "WindowWidth",
]


def _workers() -> int:
    return max(2, min(16, (os.cpu_count() or 4) * 2))


# =========================================================
# helpers
# =========================================================
def s(x) -> str:
    if x is None:
        return ""
    if isinstance(x, (list, tuple, pydicom.multival.MultiValue)):
        return "\\".join(str(v) for v in x)
    return str(x)


def first_float(x, default: Optional[float] = None) -> Optional[float]:
    try:
        if isinstance(x, (list, tuple, pydicom.multival.MultiValue)):
            x = x[0]
        return float(x)
    except Exception:
        return default


def has_dicm_preamble(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(132)
        return len(head) == 132 and head[128:132] == b"DICM"
    except OSError:
        return False


def natural_key(text: str):
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text)]


# =========================================================
# data model
# =========================================================
@dataclass
class SeriesInfo:
    uid: str
    folder: str
    files: List[str]                 # sorted along slice normal
    series_number: Optional[int]
    description: str
    modality: str
    sop_class: str
    image_type: str
    patient_id: str
    kernel: str
    kvp: str
    ma: str
    slice_thickness: str
    fov: str
    rows: int
    cols: int
    pixel_spacing: Tuple[float, float]
    iop: Tuple[float, ...]
    for_uid: str
    positions: List[Tuple[float, float, float]]
    acq_time: str                    # "YYYYMMDD HHMMSS.ffffff" for sorting/display
    samples_per_pixel: int
    window: Tuple[Optional[float], Optional[float]] = (None, None)   # (center, width) of 1st slice
    unusable_reason: str = ""        # non-empty -> cannot be used for addition (i18n key)

    @property
    def n(self) -> int:
        return len(self.files)

    @property
    def label(self) -> str:
        num = "" if self.series_number is None else f"#{self.series_number}"
        return f"{num} {Path(self.folder).name}".strip()


@dataclass
class Job:
    name: str
    mode: str                       # "avg" or "sum"
    members: List[int]              # indices into the pool (ordered list of SeriesInfo)
    method: str = "manual"

    @property
    def n(self) -> int:
        return len(self.members)


@dataclass
class SaveOptions:
    series_number_start: int = 1001
    anonymize: bool = False
    anon_patient_id: str = "ANON"
    overwrite: bool = False
    chunk: int = 8                   # max slices per processing chunk
    subfolder: bool = True           # True: out_root/<job.name>/ ; False: write directly into out_root


class Cancelled(Exception):
    pass


# =========================================================
# scanning
# =========================================================
def _read_header(path: str) -> Optional[Tuple[str, Dict[str, object]]]:
    """Read the tags we need and return them as a plain (picklable) dict."""
    if not (has_dicm_preamble(path) or path.lower().endswith((".dcm", ".dicom"))):
        return None
    try:
        ds = pydicom.dcmread(path, stop_before_pixels=True, specific_tags=_HEADER_TAGS)
    except Exception:
        return None
    try:
        if str(ds.file_meta.get("MediaStorageSOPClassUID", "")) == MEDIA_STORAGE_DIRECTORY:
            return None
    except Exception:
        pass
    h: Dict[str, object] = {}
    for kw in _HEADER_TAGS:
        try:
            v = ds.get(kw)
        except Exception:
            continue
        if v is None:
            continue
        if isinstance(v, (list, tuple, pydicom.multival.MultiValue)):
            h[kw] = [str(x) for x in v]
        else:
            h[kw] = str(v)
    if not h.get("SeriesInstanceUID"):
        return None
    return path, h


def _read_headers(paths: List[str]) -> List[Tuple[str, Dict[str, object]]]:
    out = []
    for p in paths:
        r = _read_header(p)
        if r is not None:
            out.append(r)
    return out


def scan_folder(root: str | Path,
                progress: Optional[Callable[[int], None]] = None,
                cancel: Optional[threading.Event] = None,
                workers: Optional[int] = None,
                use_processes: bool = True) -> List[SeriesInfo]:
    root = Path(root)
    candidates: List[str] = []
    for dirpath, _dirs, filenames in os.walk(root):
        for fn in filenames:
            low = fn.lower()
            if low.endswith((".dcm", ".dicom", ".ima")) or "." not in fn:
                candidates.append(os.path.join(dirpath, fn))
    candidates.sort(key=natural_key)

    groups: Dict[str, List[Tuple[str, Dict[str, object]]]] = {}
    batches = [candidates[i:i + 100] for i in range(0, len(candidates), 100)]
    workers = workers or default_workers()
    total = max(1, len(batches))
    done = 0
    if workers > 1 and use_processes and len(batches) > 1:
        from concurrent.futures import ProcessPoolExecutor
        executor = ProcessPoolExecutor(max_workers=workers)
    else:
        executor = ThreadPoolExecutor(max_workers=max(1, workers))
    try:
        futs = [executor.submit(_read_headers, b) for b in batches]
        for f in futs:
            for path, h in f.result():
                groups.setdefault(str(h["SeriesInstanceUID"]), []).append((path, h))
            done += 1
            if progress:
                progress(int(done * 100 / total))
            if cancel is not None and cancel.is_set():
                for g in futs:
                    g.cancel()
                raise Cancelled()
    finally:
        executor.shutdown(wait=True, cancel_futures=True)

    infos = [_make_series_info(uid, items) for uid, items in groups.items()]
    infos.sort(key=lambda i: (i.acq_time or "~", i.series_number if i.series_number is not None else 1 << 30,
                              natural_key(i.folder)))
    if progress:
        progress(100)
    return infos


def _slice_normal(iop: Sequence[float]) -> np.ndarray:
    r = np.array(iop[:3], dtype=float)
    c = np.array(iop[3:6], dtype=float)
    return np.cross(r, c)


def _make_series_info(uid: str, items: List[Tuple[str, Dict[str, object]]]) -> SeriesInfo:
    ds0 = items[0][1]
    iop = tuple(float(v) for v in ds0.get("ImageOrientationPatient", []) or [])

    def sort_key(it):
        ds = it[1]
        ipp = ds.get("ImagePositionPatient")
        if len(iop) == 6 and ipp is not None and len(ipp) == 3:
            return (0, float(np.dot(_slice_normal(iop), [float(v) for v in ipp])), 0)
        inst = ds.get("InstanceNumber")
        try:
            return (1, float(int(inst)), 0)
        except Exception:
            return (2, 0.0, natural_key(it[0]))

    items = sorted(items, key=sort_key)
    # Most viewers / the original app show the cranial slice (largest z) first for
    # Toshiba/Canon data; keep the InstanceNumber direction when it is available.
    try:
        inst_first = int(items[0][1]["InstanceNumber"])
        inst_last = int(items[-1][1]["InstanceNumber"])
        if inst_first > inst_last:
            items.reverse()
    except Exception:
        pass

    positions = []
    for _, ds in items:
        ipp = ds.get("ImagePositionPatient")
        positions.append(tuple(float(v) for v in ipp) if ipp is not None and len(ipp) == 3 else (math.nan,) * 3)

    ps = ds0.get("PixelSpacing")
    pixel_spacing = (float(ps[0]), float(ps[1])) if ps is not None and len(ps) == 2 else (math.nan, math.nan)
    sn = ds0.get("SeriesNumber")
    try:
        sn = int(sn) if sn is not None and s(sn) != "" else None
    except Exception:
        sn = None

    date = s(ds0.get("AcquisitionDate") or ds0.get("SeriesDate"))
    time = s(ds0.get("AcquisitionTime") or ds0.get("SeriesTime"))
    image_type = s(ds0.get("ImageType"))
    info = SeriesInfo(
        uid=uid,
        folder=str(Path(items[0][0]).parent),
        files=[p for p, _ in items],
        series_number=sn,
        description=s(ds0.get("SeriesDescription")),
        modality=s(ds0.get("Modality")),
        sop_class=s(ds0.get("SOPClassUID")),
        image_type=image_type,
        patient_id=s(ds0.get("PatientID")),
        kernel=s(ds0.get("ConvolutionKernel")),
        kvp=s(ds0.get("KVP")),
        ma=s(ds0.get("XRayTubeCurrent")),
        slice_thickness=s(ds0.get("SliceThickness")),
        fov=s(ds0.get("ReconstructionDiameter")),
        rows=int(ds0.get("Rows", 0) or 0),
        cols=int(ds0.get("Columns", 0) or 0),
        pixel_spacing=pixel_spacing,
        iop=iop,
        for_uid=s(ds0.get("FrameOfReferenceUID")),
        positions=positions,
        acq_time=f"{date} {time}".strip(),
        samples_per_pixel=int(ds0.get("SamplesPerPixel", 1) or 1),
        window=(first_float(ds0.get("WindowCenter")), first_float(ds0.get("WindowWidth"))),
    )
    info.unusable_reason = _unusable_reason(info)
    return info


def _unusable_reason(info: SeriesInfo) -> str:
    if info.sop_class != CT_IMAGE_STORAGE:
        return "reason.not_ct_image"
    if "LOCALIZER" in info.image_type.upper():
        return "reason.localizer"
    if info.samples_per_pixel != 1:
        return "reason.color"
    if len(info.iop) != 6 or any(math.isnan(v) for p in info.positions for v in p):
        return "reason.no_geometry"
    return ""


# =========================================================
# compatibility
# =========================================================
@dataclass
class CheckResult:
    ok: bool
    errors: List[Tuple[str, dict]] = field(default_factory=list)    # (i18n key, format args)
    warnings: List[Tuple[str, dict]] = field(default_factory=list)


def check_compatible(ref: SeriesInfo, other: SeriesInfo, pos_tol_mm: float = 0.01) -> CheckResult:
    r = CheckResult(ok=True)
    if other.unusable_reason:
        r.errors.append((other.unusable_reason, {}))
    if ref.unusable_reason:
        r.errors.append(("reason.ref_unusable", {}))
    if r.errors:
        r.ok = False
        return r
    if other.for_uid != ref.for_uid:
        r.errors.append(("check.for_uid", {}))
    if (other.rows, other.cols) != (ref.rows, ref.cols):
        r.errors.append(("check.matrix", {"a": f"{ref.rows}x{ref.cols}", "b": f"{other.rows}x{other.cols}"}))
    if not np.allclose(other.pixel_spacing, ref.pixel_spacing, atol=1e-4):
        r.errors.append(("check.spacing", {"a": ref.pixel_spacing, "b": other.pixel_spacing}))
    if not np.allclose(other.iop, ref.iop, atol=1e-4):
        r.errors.append(("check.orientation", {}))
    if other.n != ref.n:
        r.errors.append(("check.nslices", {"a": ref.n, "b": other.n}))
    elif not r.errors:
        d = np.abs(np.asarray(other.positions) - np.asarray(ref.positions)).max()
        if d > pos_tol_mm:
            r.errors.append(("check.position", {"d": f"{d:.2f}"}))
    # warnings (allowed, but the user should know)
    for key, a, b in (("check.kernel", ref.kernel, other.kernel),
                      ("check.kvp", ref.kvp, other.kvp),
                      ("check.thickness", ref.slice_thickness, other.slice_thickness),
                      ("check.ma", ref.ma, other.ma)):
        if a != b:
            r.warnings.append((key, {"a": a, "b": b}))
    r.ok = not r.errors
    return r


# =========================================================
# condition (job) builder
# =========================================================
METHODS = ("first", "blocks", "random", "all")


def parse_n_list(text: str) -> List[int]:
    """'2,4,8' / '2-5' / '2 4 8' -> [2,4,8]"""
    out: List[int] = []
    for tok in text.replace("、", ",").replace(" ", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if "-" in tok:
            a, b = tok.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(tok))
    seen = set()
    res = []
    for v in out:
        if v >= 1 and v not in seen:
            res.append(v)
            seen.add(v)
    return res


def build_jobs(pool_size: int, n_values: Iterable[int], method: str, mode: str,
               trials: int = 5, seed: int = 0) -> List[Job]:
    """
    pool_size : number of usable series (in acquisition order)
    method    : first  -> 1..N                     (one job per N)
                blocks -> non-overlapping groups      (1..N, N+1..2N, ...)
                random -> `trials` random draws without replacement (reproducible by seed)
                all    -> every series in the pool (n_values ignored)
    """
    mode = mode.lower()
    tag = "AVG" if mode == "avg" else "SUM"
    jobs: List[Job] = []
    if method == "all":
        if pool_size >= 1:
            jobs.append(Job(f"{tag}_N{pool_size}_ALL", mode, list(range(pool_size)), "all"))
        return jobs
    rng = random.Random(seed)
    for n in n_values:
        if n < 1 or n > pool_size:
            continue
        if method == "first":
            jobs.append(Job(f"{tag}_N{n}_F", mode, list(range(n)), method))
        elif method == "blocks":
            for b in range(pool_size // n):
                jobs.append(Job(f"{tag}_N{n}_B{b + 1:02d}", mode, list(range(b * n, (b + 1) * n)), method))
        elif method == "random":
            max_unique = math.comb(pool_size, n)
            seen: set = set()
            for t in range(min(trials, max_unique)):
                for _ in range(1000):          # prefer combinations not drawn yet
                    members = tuple(sorted(rng.sample(range(pool_size), n)))
                    if members not in seen:
                        break
                seen.add(members)
                jobs.append(Job(f"{tag}_N{n}_R{t + 1:02d}", mode, list(members), method))
        else:
            raise ValueError(method)
    return jobs


# =========================================================
# pixel I/O
# =========================================================
def _pixels_hu(ds: Dataset) -> np.ndarray:
    """Return HU image (float32). Fast path for uncompressed little-endian 16-bit data."""
    ts = str(ds.file_meta.get("TransferSyntaxUID", "")) if hasattr(ds, "file_meta") else ""
    ba = int(ds.get("BitsAllocated", 16))
    bs = int(ds.get("BitsStored", ba))
    pr = int(ds.get("PixelRepresentation", 0))
    rows, cols = int(ds.Rows), int(ds.Columns)
    if ts in UNCOMPRESSED_LE and ba == 16 and int(ds.get("SamplesPerPixel", 1)) == 1 and (pr == 0 or bs == 16):
        raw = np.frombuffer(ds.PixelData, dtype="<i2" if pr == 1 else "<u2", count=rows * cols)
        raw = raw.reshape(rows, cols)
    else:
        raw = ds.pixel_array
    slope = first_float(ds.get("RescaleSlope"), 1.0) or 1.0
    icpt = first_float(ds.get("RescaleIntercept"), 0.0) or 0.0
    out = raw.astype(np.float32)
    if slope != 1.0:
        out *= np.float32(slope)
    if icpt != 0.0:
        out += np.float32(icpt)
    return out


def read_slice(path: str, keep_dataset: bool = False):
    ds = pydicom.dcmread(path)
    img = _pixels_hu(ds)
    return (img, ds) if keep_dataset else (img, None)


def compute_slice(pool: Sequence[SeriesInfo], job: Job, z: int,
                  executor: Optional[ThreadPoolExecutor] = None) -> np.ndarray:
    """Single-slice result for preview (HU, float32)."""
    paths = [pool[i].files[z] for i in job.members]
    if executor is None:
        imgs = [read_slice(p)[0] for p in paths]
    else:
        imgs = [r[0] for r in executor.map(read_slice, paths)]
    acc = np.zeros_like(imgs[0])
    for im in imgs:
        acc += im
    if job.mode == "avg":
        acc /= np.float32(len(imgs))
    return acc


def _compute_chunk(task):
    z0, z1, member_files, mode = task
    out = None
    for files in member_files:
        for k, path in enumerate(files):
            img = read_slice(path)[0]
            if out is None:
                out = np.zeros((z1 - z0,) + img.shape, dtype=np.float32)
            out[k] += img
    if mode == "avg":
        out /= np.float32(len(member_files))
    return z0, out


def compute_volume(pool: Sequence[SeriesInfo], job: Job,
                   progress: Optional[Callable[[int], None]] = None,
                   cancel: Optional[threading.Event] = None,
                   workers: Optional[int] = None,
                   use_processes: bool = True) -> np.ndarray:
    """Whole result volume in memory (HU, float32, [Z, H, W]); slice chunks in parallel."""
    nz = pool[job.members[0]].n
    workers = workers or default_workers()
    chunk = max(1, min(8, math.ceil(nz / (workers * 4))))
    tasks = [(z0, min(nz, z0 + chunk), [pool[i].files[z0:min(nz, z0 + chunk)] for i in job.members], job.mode)
             for z0 in range(0, nz, chunk)]
    s0 = pool[job.members[0]]
    vol = np.empty((nz, s0.rows, s0.cols), dtype=np.float32)
    if workers > 1 and use_processes:
        from concurrent.futures import ProcessPoolExecutor
        executor = ProcessPoolExecutor(max_workers=workers)
    else:
        executor = ThreadPoolExecutor(max_workers=max(1, workers))
    from concurrent.futures import FIRST_COMPLETED, wait
    done = 0
    try:
        pending = {executor.submit(_compute_chunk, tk) for tk in tasks}
        while pending:
            finished, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
            for f in finished:
                z0, arr = f.result()
                vol[z0:z0 + arr.shape[0]] = arr
                done += arr.shape[0]
            if progress:
                progress(int(done * 100 / nz))
            if cancel is not None and cancel.is_set():
                for f in pending:
                    f.cancel()
                raise Cancelled()
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
    return vol


# =========================================================
# writing
# =========================================================
_ANON_TAGS = [
    "PatientName", "PatientBirthDate", "PatientSex", "PatientAge", "PatientWeight", "PatientSize",
    "OtherPatientIDs", "OtherPatientNames", "PatientAddress", "PatientTelephoneNumbers",
    "InstitutionName", "InstitutionAddress", "InstitutionalDepartmentName", "ReferringPhysicianName",
    "PerformingPhysicianName", "OperatorsName", "PhysiciansOfRecord", "NameOfPhysiciansReadingStudy",
    "AccessionNumber", "StationName", "DeviceSerialNumber", "RequestingPhysician",
]


def _encode_stored(hu: np.ndarray, pixel_representation: int) -> Tuple[np.ndarray, float, float]:
    """
    HU -> stored 16-bit values without clipping.
    Uses slope 1 / intercept 0 when the values fit; otherwise shifts the intercept and,
    only if the range exceeds 65535, increases the slope.
    Returns (stored array, slope, intercept).
    """
    if pixel_representation == 1:
        smin, smax, dtype = -32768, 32767, np.int16
    else:
        smin, smax, dtype = 0, 65535, np.uint16
    lo = float(np.floor(hu.min()))
    hi = float(np.ceil(hu.max()))
    slope, icpt = 1.0, 0.0
    if lo < smin or hi > smax:
        span = hi - lo
        slope = float(max(1, math.ceil(span / 65535.0)))
        icpt = float(math.floor(lo - smin * slope))
    stored = np.rint((hu - icpt) / slope)
    stored = np.clip(stored, smin, smax).astype(dtype)
    return stored, slope, icpt


def _ds_number(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.6g}"


def make_output_dataset(template: Dataset, hu: np.ndarray, job: Job, pool: Sequence[SeriesInfo],
                        series_uid: str, series_number: int, instance_number: int,
                        opts: SaveOptions, now: _dt.datetime) -> Dataset:
    # Shallow copy of the template: element objects are shared with the template, so every
    # change below goes through _set()/del (which replace elements instead of mutating them).
    ds = Dataset()
    ds._dict.update((tag, el) for tag, el in template._dict.items() if tag != 0x7FE00010)

    def _set(kw, value):
        if kw in ds:
            del ds[kw]
        setattr(ds, kw, value)

    ds.file_meta = FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = template.SOPClassUID
    sop_uid = generate_uid()
    ds.file_meta.MediaStorageSOPInstanceUID = sop_uid
    ds.preamble = b"\x00" * 128

    pr = int(template.get("PixelRepresentation", 1))
    stored, slope, icpt = _encode_stored(hu, pr)

    _set("SOPInstanceUID", sop_uid)
    _set("SeriesInstanceUID", series_uid)
    _set("SeriesNumber", series_number)
    _set("InstanceNumber", instance_number)
    it = list(template.get("ImageType", []) or [])
    _set("ImageType", ["DERIVED", "SECONDARY"] + [str(v) for v in it[2:]])
    base_desc = s(template.get("SeriesDescription"))
    _set("SeriesDescription", (f"{base_desc}_{job.name}" if base_desc else job.name)[:64])
    nums = ",".join(str(pool[i].series_number) for i in job.members)
    _set("DerivationDescription", (
        f"{APP_NAME} {APP_VERSION}: {'average' if job.mode == 'avg' else 'sum'} of {job.n} series "
        f"(SeriesNumber {nums}). Research use only."
    )[:1024])
    _set("SeriesDate", now.strftime("%Y%m%d"))
    _set("SeriesTime", now.strftime("%H%M%S"))
    _set("InstanceCreationDate", ds.SeriesDate)
    _set("InstanceCreationTime", ds.SeriesTime)
    _set("ContentDate", ds.SeriesDate)
    _set("ContentTime", ds.SeriesTime)

    # pixel module
    _set("Rows", int(stored.shape[0]))
    _set("Columns", int(stored.shape[1]))
    _set("SamplesPerPixel", 1)
    _set("PhotometricInterpretation", "MONOCHROME2")
    _set("BitsAllocated", 16)
    _set("BitsStored", 16)
    _set("HighBit", 15)
    _set("PixelRepresentation", pr)
    _set("RescaleSlope", _ds_number(slope))
    _set("RescaleIntercept", _ds_number(icpt))
    if "RescaleType" not in ds:
        _set("RescaleType", "HU")
    for kw in ("SmallestImagePixelValue", "LargestImagePixelValue", "PixelPaddingValue",
               "PixelPaddingRangeLimit", "LossyImageCompression", "LossyImageCompressionRatio",
               "LossyImageCompressionMethod"):
        if kw in ds:
            del ds[kw]
    ds.add_new(0x7FE00010, "OW", stored.tobytes())

    # window: scale for SUM so that the image is not saturated in other viewers
    if job.mode == "sum":
        for kw in ("WindowCenter", "WindowWidth"):
            v = ds.get(kw)
            if v is None:
                continue
            if isinstance(v, (list, tuple, pydicom.multival.MultiValue)):
                _set(kw, [_ds_number(float(x) * job.n) for x in v])
            else:
                _set(kw, _ds_number(float(v) * job.n))

    if opts.anonymize:
        for kw in _ANON_TAGS:
            if kw in ds:
                del ds[kw]
        _set("PatientName", opts.anon_patient_id or "ANON")
        _set("PatientID", opts.anon_patient_id or "ANON")
        _set("PatientIdentityRemoved", "YES")
        _set("DeidentificationMethod", f"{APP_NAME} basic tag removal")
    return ds


def _job_dir(out_root: Path, job: Job, subfolder: bool = True) -> Path:
    return out_root / job.name if subfolder else out_root


def existing_outputs(out_root: str | Path, jobs: Sequence[Job], subfolder: bool = True) -> List[str]:
    out_root = Path(out_root)
    res = []
    if not subfolder:
        if out_root.exists() and any(out_root.glob("IM_*.dcm")):
            res.append(str(out_root))
        return res
    for j in jobs:
        d = _job_dir(out_root, j)
        if d.exists() and any(d.iterdir()):
            res.append(str(d))
    return res


def _process_chunk(task) -> int:
    """
    Worker (runs in a separate process): read the slices z0..z1 of every needed series once,
    compute every job for those slices and write the output files. Returns files written.
    Only small, picklable arguments are passed in; no image data crosses process boundaries.
    """
    (z0, z1, files, jobs, templates, series_uids, series_numbers, dirs, opts, now,
     pool_lite) = task
    written = 0
    for z in range(z0, z1):
        imgs: Dict[int, np.ndarray] = {}
        dss: Dict[int, Dataset] = {}
        for i, paths in files.items():
            img, ds = read_slice(paths[z - z0], keep_dataset=i in templates)
            imgs[i] = img
            if ds is not None:
                dss[i] = ds
        for k, job in enumerate(jobs):
            acc = imgs[job.members[0]].copy()
            for i in job.members[1:]:
                acc += imgs[i]
            if job.mode == "avg":
                acc /= np.float32(job.n)
            out = make_output_dataset(dss[job.members[0]], acc, job, pool_lite,
                                      series_uids[k], series_numbers[k], z + 1, opts, now)
            out.save_as(os.path.join(dirs[k], f"IM_{z + 1:04d}.dcm"), enforce_file_format=True)
            written += 1
    return written


@dataclass
class _SeriesLite:                    # what make_output_dataset needs from SeriesInfo
    series_number: Optional[int]


def default_workers() -> int:
    return max(1, min(32, os.cpu_count() or 2))


def run_jobs(pool: Sequence[SeriesInfo], jobs: Sequence[Job], out_root: str | Path,
             opts: SaveOptions = SaveOptions(),
             progress: Optional[Callable[[int], None]] = None,
             cancel: Optional[threading.Event] = None,
             workers: Optional[int] = None,
             use_processes: bool = True) -> Dict:
    """
    Compute every job and write it as a DICOM series under out_root/<job.name>/.

    - Every input file is read exactly once regardless of how many jobs use it.
    - The volume is split into small z-chunks that are processed in parallel by worker
      processes (DICOM parsing/writing is CPU-bound Python, so processes scale with cores
      where threads would not).
    - Memory per worker ~ chunk * n_used_series * rows * cols * 4 bytes.
    """
    if not jobs:
        raise ValueError("no jobs")
    out_root = Path(out_root)
    nz = pool[jobs[0].members[0]].n
    used = sorted({i for j in jobs for i in j.members})
    templates = {j.members[0] for j in jobs}
    for i in used:
        if pool[i].n != nz:
            raise ValueError("slice count mismatch")

    if not opts.overwrite:
        ex = existing_outputs(out_root, jobs, opts.subfolder)
        if ex:
            raise FileExistsError("\n".join(ex))

    now = _dt.datetime.now()
    series_uids = [generate_uid() for _ in jobs]
    series_numbers = [opts.series_number_start + k for k in range(len(jobs))]
    if not opts.subfolder and len(jobs) != 1:
        raise ValueError("subfolder=False needs exactly one job")
    dirs = [str(_job_dir(out_root, j, opts.subfolder)) for j in jobs]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    pool_lite = [_SeriesLite(p.series_number) for p in pool]
    jobs = list(jobs)

    workers = workers or default_workers()
    chunk = max(1, int(opts.chunk))
    if workers > 1:
        # enough chunks to keep every worker busy and progress smooth
        chunk = max(1, min(chunk, math.ceil(nz / (workers * 4))))
    tasks = []
    for z0 in range(0, nz, chunk):
        z1 = min(nz, z0 + chunk)
        files = {i: pool[i].files[z0:z1] for i in used}
        tasks.append((z0, z1, files, jobs, templates, series_uids, series_numbers, dirs, opts, now,
                      pool_lite))

    total = nz * len(jobs)
    done = 0
    if workers == 1:
        for tk in tasks:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            done += _process_chunk(tk)
            if progress:
                progress(int(done * 100 / total))
    else:
        if use_processes:
            from concurrent.futures import ProcessPoolExecutor
            executor = ProcessPoolExecutor(max_workers=workers)
        else:
            executor = ThreadPoolExecutor(max_workers=workers)
        from concurrent.futures import FIRST_COMPLETED, wait
        try:
            pending = {executor.submit(_process_chunk, tk) for tk in tasks}
            while pending:
                finished, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                for f in finished:
                    done += f.result()          # re-raises worker errors
                if progress:
                    progress(int(done * 100 / total))
                if cancel is not None and cancel.is_set():
                    for f in pending:
                        f.cancel()
                    raise Cancelled()
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    log = write_log(out_root, pool, jobs, series_uids, series_numbers, now)
    if progress:
        progress(100)
    return log


def write_log(out_root: Path, pool: Sequence[SeriesInfo], jobs: Sequence[Job],
              series_uids: List[str], series_numbers: List[int], now: _dt.datetime) -> Dict:
    stamp = now.strftime("%Y%m%d_%H%M%S")
    rows = []
    for j, uid, sn in zip(jobs, series_uids, series_numbers):
        rows.append({
            "job": j.name, "mode": j.mode, "n": j.n, "method": j.method,
            "output_series_number": sn, "output_series_uid": uid,
            "input_series_numbers": " ".join(str(pool[i].series_number) for i in j.members),
            "input_folders": " | ".join(pool[i].folder for i in j.members),
        })
    csv_path = out_root / f"fused_log_{stamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    meta = {"app": APP_NAME, "version": APP_VERSION, "created": now.isoformat(timespec="seconds"),
            "jobs": rows}
    with open(out_root / f"fused_log_{stamp}.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return {"csv": str(csv_path), "jobs": rows}
