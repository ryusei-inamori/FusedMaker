#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fused Maker - sum / average CT series (Japanese / English UI)."""
from __future__ import annotations

import multiprocessing
import sys
import threading
import traceback
from pathlib import Path
from typing import List, Optional

import numpy as np
import pydicom

import fused_core as fc
from i18n import LANGS, set_language, tr
from qt_compat import QT_API, QT_VERSION, BINDING_VERSION, QtCore, QtGui, QtWidgets, Signal

Qt = QtCore.Qt
QW = QtWidgets
ORG = APP = "FusedAuto"


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


# =========================================================
# workers
# =========================================================
class ScanWorker(QtCore.QThread):
    progress = Signal(int)
    result = Signal(list)
    failed = Signal(str)

    def __init__(self, root: str):
        super().__init__()
        self.root = root

    def run(self):
        try:
            self.result.emit(fc.scan_folder(self.root, progress=self.progress.emit))
        except Exception:
            self.failed.emit(traceback.format_exc())


class SumWorker(QtCore.QThread):
    progress = Signal(int)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, series, job):
        super().__init__()
        self.series, self.job = series, job

    def run(self):
        try:
            self.done.emit(fc.compute_volume(self.series, self.job, progress=self.progress.emit))
        except Exception:
            self.failed.emit(traceback.format_exc())


class SaveWorker(QtCore.QThread):
    progress = Signal(int)
    done = Signal()
    failed = Signal(str)

    def __init__(self, series, job, out_dir, opts):
        super().__init__()
        self.series, self.job, self.out_dir, self.opts = series, job, out_dir, opts

    def run(self):
        try:
            fc.run_jobs(self.series, [self.job], self.out_dir, self.opts, progress=self.progress.emit)
            self.done.emit()
        except Exception:
            self.failed.emit(traceback.format_exc())


# =========================================================
# image label (square, wheel = slice)
# =========================================================
class ImageLabel(QW.QLabel):
    wheel_sliced = Signal(int)

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Fixed)

    def wheelEvent(self, event):
        d = event.angleDelta().y()
        if d > 0:
            self.wheel_sliced.emit(-1)
        elif d < 0:
            self.wheel_sliced.emit(+1)
        event.accept()


# =========================================================
# main window
# =========================================================
class MainWindow(QW.QMainWindow):
    COLS = ["col.use", "col.number", "col.patient", "col.desc", "col.kernel", "col.n", "col.dir"]

    def __init__(self, settings: QtCore.QSettings):
        super().__init__()
        self.settings = settings
        self.resize(1280, 760)
        icon = resource_path("main.ico")
        if icon.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon)))

        self.series: List[fc.SeriesInfo] = []
        self.out_stack_hu: Optional[np.ndarray] = None
        self.job: Optional[fc.Job] = None
        self.cur_z = 0
        self.wl, self.ww = 40.0, 400.0
        self.worker = None

        root = QW.QWidget()
        self.setCentralWidget(root)
        outer = QW.QVBoxLayout(root)

        # top: folder
        top = QW.QHBoxLayout()
        self.lbl_input = QW.QLabel()
        self.root_edit = QW.QLineEdit(self.settings.value("last_input", "", type=str))
        self.btn_pick = QW.QPushButton()
        self.btn_scan = QW.QPushButton()
        top.addWidget(self.lbl_input)
        top.addWidget(self.root_edit, stretch=1)
        top.addWidget(self.btn_pick)
        top.addWidget(self.btn_scan)
        outer.addLayout(top)

        sp = QW.QSplitter()
        outer.addWidget(sp, stretch=1)

        # left: series table
        left = QW.QWidget()
        left_l = QW.QVBoxLayout(left)
        self.table = QW.QTableWidget(0, len(self.COLS))
        self.table.setSelectionBehavior(QW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QW.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.itemChanged.connect(self.on_item_changed)
        self._filling = False
        left_l.addWidget(self.table)

        sel = QW.QHBoxLayout()
        self.btn_all = QW.QPushButton()
        self.btn_none = QW.QPushButton()
        self.btn_all.clicked.connect(lambda: self.set_all_checked(True))
        self.btn_none.clicked.connect(lambda: self.set_all_checked(False))
        self.lbl_count = QW.QLabel()
        sel.addWidget(self.btn_all)
        sel.addWidget(self.btn_none)
        sel.addWidget(self.lbl_count)
        sel.addStretch(1)
        left_l.addLayout(sel)

        act = QW.QHBoxLayout()
        self.lbl_mode = QW.QLabel()
        self.mode_combo = QW.QComboBox()
        self.btn_sum = QW.QPushButton()
        act.addWidget(self.lbl_mode)
        act.addWidget(self.mode_combo)
        act.addWidget(self.btn_sum, stretch=1)
        left_l.addLayout(act)
        sp.addWidget(left)

        # right: viewer
        right = QW.QWidget()
        right_l = QW.QVBoxLayout(right)
        self.lbl_result = QW.QLabel()
        right_l.addWidget(self.lbl_result)
        self.img_label = ImageLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("QLabel { background: #111; color: #ccc; }")
        self.img_label.wheel_sliced.connect(self.on_wheel_slice)
        right_l.addWidget(self.img_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        ctrl = QW.QHBoxLayout()
        self.lbl_slice = QW.QLabel()
        self.slice_spin = QW.QSpinBox()
        self.slice_spin.setRange(1, 1)
        self.slice_spin.valueChanged.connect(self.on_slice_changed)
        self.wl_spin = QW.QSpinBox()
        self.wl_spin.setRange(-100000, 100000)
        self.wl_spin.setValue(int(self.wl))
        self.wl_spin.valueChanged.connect(self.on_wlww_changed)
        self.ww_spin = QW.QSpinBox()
        self.ww_spin.setRange(1, 200000)
        self.ww_spin.setValue(int(self.ww))
        self.ww_spin.valueChanged.connect(self.on_wlww_changed)
        self.btn_save = QW.QPushButton()
        ctrl.addWidget(self.lbl_slice)
        ctrl.addWidget(self.slice_spin)
        ctrl.addSpacing(10)
        ctrl.addWidget(QW.QLabel("WL:"))
        ctrl.addWidget(self.wl_spin)
        ctrl.addWidget(QW.QLabel("WW:"))
        ctrl.addWidget(self.ww_spin)
        ctrl.addStretch(1)
        ctrl.addWidget(self.btn_save)
        right_l.addLayout(ctrl)
        sp.addWidget(right)
        self.right_panel = right
        self.right_panel.setFixedWidth(650)
        sp.setSizes([9999, 650])

        # bottom: progress
        self.pbar = QW.QProgressBar()
        self.pbar.setRange(0, 100)
        outer.addWidget(self.pbar)

        self.btn_pick.clicked.connect(self.pick_root)
        self.btn_scan.clicked.connect(self.scan)
        self.root_edit.returnPressed.connect(self.scan)
        self.btn_sum.clicked.connect(self.sum_selected)
        self.btn_save.clicked.connect(self.save_dicom_series)

        self._build_menu()
        self.retranslate()
        self._update_square_view()

    # ---------------------------------------------------------- menu / i18n
    def _build_menu(self):
        mb = self.menuBar()
        self.m_lang = mb.addMenu("")
        group = QtGui.QActionGroup(self)
        self.lang_actions = {}
        current = self.settings.value("language", "auto", type=str)
        for code in ["auto"] + list(LANGS):
            a = self.m_lang.addAction("")
            a.setCheckable(True)
            a.setChecked(code == current)
            group.addAction(a)
            a.triggered.connect(lambda _=False, c=code: self.change_language(c))
            self.lang_actions[code] = a
        self.m_help = mb.addMenu("")
        self.a_manual = self.m_help.addAction("")
        self.a_manual.setShortcut(QtGui.QKeySequence("F1"))
        self.a_manual.triggered.connect(self.open_manual)
        self.m_help.addSeparator()
        self.a_licenses = self.m_help.addAction("")
        self.a_licenses.triggered.connect(self.open_licenses)
        self.a_disclaimer = self.m_help.addAction("")
        self.a_disclaimer.triggered.connect(lambda: show_disclaimer(self, self.settings, force=True))
        self.a_about = self.m_help.addAction("")
        self.a_about.triggered.connect(self.show_about)

    def retranslate(self):
        self.setWindowTitle(tr("app.title"))
        self.m_lang.setTitle(tr("menu.language"))
        self.lang_actions["auto"].setText(tr("menu.lang_auto"))
        for code, name in LANGS.items():
            self.lang_actions[code].setText(name)
        self.m_help.setTitle(tr("menu.help"))
        self.a_manual.setText(tr("menu.manual"))
        self.a_licenses.setText(tr("menu.licenses"))
        self.a_disclaimer.setText(tr("menu.disclaimer"))
        self.a_about.setText(tr("menu.about"))
        self.lbl_input.setText(tr("input.label"))
        self.btn_pick.setText(tr("input.pick"))
        self.btn_scan.setText(tr("input.scan"))
        self.table.setHorizontalHeaderLabels([tr(k) for k in self.COLS])
        self.btn_all.setText(tr("sel.all"))
        self.btn_none.setText(tr("sel.none"))
        self.update_count()
        self.lbl_mode.setText(tr("mode.label"))
        cur = self.mode_combo.currentData() or "sum"
        self.mode_combo.clear()
        self.mode_combo.addItem(tr("mode.sum"), "sum")
        self.mode_combo.addItem(tr("mode.avg"), "avg")
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(cur))
        self.btn_sum.setText(tr("btn.run"))
        self.lbl_slice.setText(tr("view.slice"))
        self.btn_save.setText(tr("btn.save"))
        if self.out_stack_hu is None:
            self.img_label.setText(tr("view.empty"))
        self._update_result_label()

    def change_language(self, code: str):
        self.settings.setValue("language", code)
        apply_language(QW.QApplication.instance(), code)
        self.retranslate()

    def open_manual(self):
        from i18n import current_language
        for lang in (current_language(), "en", "ja"):
            pdf = resource_path(f"docs/FusedAuto_manual_{lang}.pdf")
            if pdf.exists():
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(pdf)))
                return
        QW.QMessageBox.information(self, tr("msg.notice"), tr("msg.no_manual"))

    def open_licenses(self):
        folder = resource_path("licenses")
        if folder.is_dir():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))
        else:
            QW.QMessageBox.information(self, tr("msg.notice"), tr("msg.no_licenses", url=fc.APP_URL))

    def show_about(self):
        cite = f"https://doi.org/{fc.APP_DOI}" if fc.APP_DOI else fc.APP_URL
        QW.QMessageBox.about(self, tr("about.title"), tr(
            "about.body", ver=fc.APP_VERSION, api=QT_API, bver=BINDING_VERSION, qt=QT_VERSION,
            pd=pydicom.__version__, np=np.__version__, author=fc.APP_AUTHOR, contact=fc.APP_CONTACT,
            url=fc.APP_URL, cite=cite))

    # ---------------------------------------------------------- UI helpers
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_square_view()
        self.render()

    def _update_square_view(self):
        w = max(200, self.right_panel.width() - 40)
        self.img_label.setFixedSize(QtCore.QSize(w, w))

    def _update_result_label(self):
        if self.job is None:
            self.lbl_result.setText("")
        else:
            self.lbl_result.setText(tr("status.used", mode=tr(f"mode.{self.job.mode}"), n=self.job.n))

    def set_busy(self, busy: bool):
        for w in (self.btn_pick, self.btn_scan, self.btn_sum, self.btn_save, self.table,
                  self.btn_all, self.btn_none):
            w.setEnabled(not busy)
        if busy:
            self.pbar.setValue(0)

    def start_worker(self, worker, on_done):
        self.worker = worker
        worker.progress.connect(self.pbar.setValue)
        (worker.result if isinstance(worker, ScanWorker) else worker.done).connect(on_done)
        worker.failed.connect(self.on_worker_failed)
        self.set_busy(True)
        worker.start()

    def on_worker_failed(self, detail: str):
        self.set_busy(False)
        box = QW.QMessageBox(self)
        box.setIcon(QW.QMessageBox.Icon.Critical)
        box.setWindowTitle(tr("msg.error"))
        last = detail.strip().splitlines()[-1] if detail.strip() else ""
        box.setText(tr("msg.error_detail") + "\n\n" + last)
        box.setDetailedText(detail)
        box.exec()

    # ---------------------------------------------------------- actions
    def pick_root(self):
        d = QW.QFileDialog.getExistingDirectory(self, tr("input.pick_title"), self.root_edit.text())
        if d:
            self.root_edit.setText(d)

    def scan(self):
        root = self.root_edit.text().strip()
        if not root or not Path(root).is_dir():
            QW.QMessageBox.critical(self, tr("msg.error"), tr("msg.input_missing"))
            return
        self.settings.setValue("last_input", root)
        self.table.setRowCount(0)
        self.series = []
        self.start_worker(ScanWorker(root), self.on_scan_result)

    def on_scan_result(self, infos: list):
        self.set_busy(False)
        self.series = infos
        self._filling = True
        self.table.setRowCount(len(infos))
        gray = QtGui.QBrush(QtGui.QColor(150, 150, 150))
        for r, s in enumerate(infos):
            use = QW.QTableWidgetItem()
            flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            if not s.unusable_reason:
                flags |= Qt.ItemFlag.ItemIsUserCheckable
            use.setFlags(flags)
            use.setCheckState(Qt.CheckState.Unchecked)
            if s.unusable_reason:
                use.setToolTip(tr(s.unusable_reason))
            self.table.setItem(r, 0, use)
            num = "" if s.series_number is None else str(s.series_number)
            for c, v in enumerate([num, s.patient_id, s.description, s.kernel, str(s.n), s.folder], start=1):
                it = QW.QTableWidgetItem(v)
                it.setToolTip(tr(s.unusable_reason) if s.unusable_reason else v)
                if s.unusable_reason:
                    it.setForeground(gray)
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self._filling = False
        self.update_count()
        self.pbar.setValue(100)

    def on_cell_clicked(self, row: int, col: int):
        # clicking anywhere on a row toggles its checkbox (the checkbox itself toggles on its own)
        if col == 0:
            return
        it = self.table.item(row, 0)
        if it is not None and it.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            it.setCheckState(Qt.CheckState.Unchecked if it.checkState() == Qt.CheckState.Checked
                             else Qt.CheckState.Checked)

    def on_item_changed(self, item):
        if not self._filling and item.column() == 0:
            self.update_count()

    def set_all_checked(self, on: bool):
        self._filling = True
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it is not None and it.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
        self._filling = False
        self.update_count()

    def update_count(self):
        self.lbl_count.setText(tr("sel.count", n=len(self.selected_indices())))

    def selected_indices(self) -> List[int]:
        out = []
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it is not None and it.checkState() == Qt.CheckState.Checked:
                out.append(r)
        return out

    def sum_selected(self):
        rows = self.selected_indices()
        if len(rows) < 2:
            QW.QMessageBox.information(self, tr("msg.notice"), tr("msg.select2"))
            return
        # reference = the checked series that matches the most other checked series
        # (ties -> the upper one), so one stray series cannot become the reference
        best, best_n = rows[0], -1
        for r in rows:
            n = sum(fc.check_compatible(self.series[r], self.series[o]).ok for o in rows)
            if n > best_n:
                best, best_n = r, n
        ref = self.series[best]
        if ref.unusable_reason:
            QW.QMessageBox.warning(self, tr("msg.notice"), tr("msg.ref_bad", why=tr(ref.unusable_reason)))
            return
        used, excluded = [], []
        for r in rows:
            chk = fc.check_compatible(ref, self.series[r])
            if chk.ok:
                used.append(r)
            else:
                why = ", ".join(tr(k, **a) for k, a in chk.errors)
                excluded.append(f"・{self.series[r].label}: {why}")
        if excluded:
            QW.QMessageBox.information(self, tr("msg.notice"),
                                       tr("msg.excluded", ref=ref.label, list="\n".join(excluded)))
        if len(used) < 2:
            QW.QMessageBox.warning(self, tr("msg.notice"), tr("msg.too_few"))
            return
        mode = self.mode_combo.currentData()
        job = fc.Job(f"{mode.upper()}_N{len(used)}", mode, used)
        self.start_worker(SumWorker(self.series, job), lambda vol, j=job: self.on_sum_done(vol, j))

    def on_sum_done(self, vol, job):
        self.set_busy(False)
        self.out_stack_hu = vol
        self.job = job
        self._update_result_label()
        nz = vol.shape[0]
        self.slice_spin.blockSignals(True)
        self.slice_spin.setRange(1, nz)
        self.slice_spin.setValue(1)
        self.slice_spin.blockSignals(False)
        self.cur_z = 0
        wc, ww = self.series[job.members[0]].window
        wc = 40.0 if wc is None else wc
        ww = 400.0 if ww is None else ww
        if job.mode == "sum":           # widen the window so the sum is not saturated
            wc, ww = wc * job.n, ww * job.n
        for w in (self.wl_spin, self.ww_spin):
            w.blockSignals(True)
        self.wl_spin.setValue(int(round(wc)))
        self.ww_spin.setValue(max(1, int(round(ww))))
        for w in (self.wl_spin, self.ww_spin):
            w.blockSignals(False)
        self.wl, self.ww = float(self.wl_spin.value()), float(self.ww_spin.value())
        self.pbar.setValue(100)
        self.render()

    def on_wheel_slice(self, delta: int):
        if self.out_stack_hu is not None:
            self.slice_spin.setValue(int(np.clip(self.cur_z + delta, 0, self.out_stack_hu.shape[0] - 1)) + 1)

    def on_slice_changed(self, v: int):
        self.cur_z = int(v) - 1
        self.render()

    def on_wlww_changed(self):
        self.wl, self.ww = float(self.wl_spin.value()), float(self.ww_spin.value())
        self.render()

    def render(self):
        if self.out_stack_hu is None:
            return
        z = int(np.clip(self.cur_z, 0, self.out_stack_hu.shape[0] - 1))
        lo = self.wl - self.ww / 2.0
        u8 = np.clip((self.out_stack_hu[z] - lo) * (255.0 / max(1e-6, self.ww)), 0, 255).astype(np.uint8)
        u8 = np.ascontiguousarray(u8)
        h, w = u8.shape
        qimg = QtGui.QImage(u8.data, w, h, w, QtGui.QImage.Format.Format_Grayscale8).copy()
        self.img_label.setPixmap(QtGui.QPixmap.fromImage(qimg).scaled(
            self.img_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def save_dicom_series(self):
        if self.out_stack_hu is None or self.job is None:
            QW.QMessageBox.information(self, tr("msg.notice"), tr("msg.no_result"))
            return
        out_dir = QW.QFileDialog.getExistingDirectory(self, tr("save.title"),
                                                      self.settings.value("last_output", "", type=str))
        if not out_dir:
            return
        self.settings.setValue("last_output", out_dir)
        sn = self.series[self.job.members[0]].series_number
        opts = fc.SaveOptions(series_number_start=(sn or 0) + 1000, subfolder=False)
        if fc.existing_outputs(out_dir, [self.job], subfolder=False):
            ans = QW.QMessageBox.question(self, tr("msg.confirm"), tr("msg.overwrite", dir=out_dir))
            if ans != QW.QMessageBox.StandardButton.Yes:
                return
            opts.overwrite = True
        self.start_worker(SaveWorker(self.series, self.job, out_dir, opts),
                          lambda d=out_dir: self.on_saved(d))

    def on_saved(self, out_dir: str):
        self.set_busy(False)
        self.pbar.setValue(100)
        QW.QMessageBox.information(self, tr("msg.done_title"), tr("msg.saved", dir=out_dir))

    def closeEvent(self, e):
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(10000)
        super().closeEvent(e)


# =========================================================
# language / startup
# =========================================================
_qt_translators: List[QtCore.QTranslator] = []


def resolve_language(code: str) -> str:
    if code in LANGS:
        return code
    return "ja" if QtCore.QLocale.system().name().lower().startswith("ja") else "en"


def apply_language(app: QW.QApplication, code: str) -> str:
    lang = resolve_language(code)
    set_language(lang)
    for t in _qt_translators:
        app.removeTranslator(t)
    _qt_translators.clear()
    # Qt's own dialogs (Yes/No buttons, file dialog, ...)
    path = QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.TranslationsPath)
    t = QtCore.QTranslator(app)
    if t.load(f"qtbase_{lang}", path):
        app.installTranslator(t)
        _qt_translators.append(t)
    return lang


def show_disclaimer(parent, settings: QtCore.QSettings, force: bool = False):
    if not force and settings.value("hide_disclaimer", False, type=bool):
        return
    box = QW.QMessageBox(parent)
    box.setIcon(QW.QMessageBox.Icon.Information)
    box.setWindowTitle(tr("disclaimer.title"))
    box.setText(tr("disclaimer.body"))
    cb = QW.QCheckBox(tr("disclaimer.dont_show"))
    cb.setChecked(settings.value("hide_disclaimer", False, type=bool))
    box.setCheckBox(cb)
    box.exec()
    settings.setValue("hide_disclaimer", cb.isChecked())


def main():
    multiprocessing.freeze_support()     # needed for worker processes in the .exe
    app = QW.QApplication(sys.argv)
    app.setOrganizationName(ORG)
    app.setApplicationName(APP)
    settings = QtCore.QSettings(ORG, APP)
    apply_language(app, settings.value("language", "auto", type=str))
    w = MainWindow(settings)
    w.show()
    show_disclaimer(w, settings)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
