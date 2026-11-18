# -*- coding: utf-8 -*-
"""
Small i18n layer: tr("key", **kwargs). Add a language by adding a dict to TRANSLATIONS
(missing keys fall back to English).
"""
from __future__ import annotations

LANGS = {"ja": "日本語", "en": "English"}
_current = "en"

TRANSLATIONS = {
    "ja": {
        "app.title": "Fused Maker",
        "menu.language": "言語 / Language",
        "menu.lang_auto": "自動（OSに合わせる）",
        "menu.help": "ヘルプ",
        "menu.about": "このアプリについて",
        "menu.manual": "説明書 (PDF)",
        "menu.licenses": "ライセンス",
        "msg.no_licenses": "ライセンスファイルが見つかりません。{url} を参照してください。",
        "msg.no_manual": "説明書が見つかりません。",
        "menu.disclaimer": "免責事項",
        "input.label": "入力:",
        "input.pick": "フォルダ選択",
        "input.scan": "読み込み",
        "input.pick_title": "入力ルートを選択",
        "col.use": "使用",
        "col.number": "Series#",
        "sel.all": "すべて選択",
        "sel.none": "選択解除",
        "sel.count": "選択中: {n}",
        "col.patient": "患者ID",
        "col.desc": "シリーズ説明",
        "col.kernel": "カーネル",
        "col.n": "枚数",
        "col.dir": "フォルダ",
        "mode.label": "処理:",
        "mode.sum": "加算",
        "mode.avg": "平均",
        "btn.run": "加算/平均して表示",
        "view.empty": "ここに加算画像を表示",
        "view.slice": "スライス:",
        "btn.save": "保存",
        "save.title": "保存先フォルダを選択（DICOMシリーズ）",
        # reasons / checks (keys come from fused_core)
        "reason.not_ct_image": "CT画像ではない（線量レポート等）",
        "reason.localizer": "位置決め画像",
        "reason.color": "カラー画像",
        "reason.no_geometry": "位置情報がない",
        "reason.ref_unusable": "先頭のシリーズが使用できない",
        "check.for_uid": "撮影位置（座標系）が違う",
        "check.matrix": "マトリクスが違う ({a} / {b})",
        "check.spacing": "ピクセル間隔が違う",
        "check.orientation": "画像の向きが違う",
        "check.nslices": "スライス数が違う ({a} / {b})",
        "check.position": "スライス位置がずれている (最大 {d} mm)",
        "check.kernel": "カーネルが違う ({a} / {b})",
        "check.kvp": "管電圧が違う ({a} / {b})",
        "check.thickness": "スライス厚が違う ({a} / {b})",
        "check.ma": "管電流が違う ({a} / {b})",
        # messages
        "msg.error": "エラー",
        "msg.notice": "注意",
        "msg.confirm": "確認",
        "msg.done_title": "保存完了",
        "msg.input_missing": "入力ルートが存在しません。",
        "msg.select2": "加算するシリーズを2つ以上チェックしてください。",
        "msg.ref_bad": "選んだシリーズは加算に使えません: {why}",
        "msg.excluded": "次のシリーズは基準のシリーズ（{ref}）と撮影位置などが一致しないため除外しました:\n\n{list}",
        "msg.too_few": "使えるシリーズが2つ未満です。",
        "msg.no_result": "加算結果がありません。",
        "msg.overwrite": "保存先に既に IM_*.dcm があります。上書きしますか？\n{dir}",
        "msg.saved": "DICOMシリーズとして保存しました:\n{dir}",
        "msg.error_detail": "処理中にエラーが発生しました。",
        "status.used": "{mode} N={n}",
        "about.title": "このアプリについて",
        "about.body": (
            "<h3>Fused Maker (FusedAuto {ver})</h3>"
            "<p>同じ位置で繰り返し撮影した CT シリーズを加算・平均して、新しい DICOM シリーズとして保存します。</p>"
            "<p><b>研究用途専用です。診断・治療には使用しないでください。</b></p>"
            "<p>© 2026 {author}<br>"
            "ライセンス：PolyForm Noncommercial License 1.0.0<br>"
            "非商用の研究・教育目的であれば、誰でも無料で利用・改変・再配布できます。"
            "商用利用はできません（ご相談：{contact}）。</p>"
            "<p><b>引用のお願い：</b>研究成果の発表に使用した場合は、次を引用してください。<br>"
            "{author}. Fused Maker (FusedAuto), version {ver} [Software]. {cite}</p>"
            "<p>{api} {bver} / Qt {qt}（LGPL v3）/ pydicom {pd} / NumPy {np}<br>"
            "同梱ソフトウェアのライセンスとソース入手先は［ヘルプ］→［ライセンス］を参照してください。<br>"
            "{url}</p>"
        ),
        "disclaimer.title": "免責事項",
        "disclaimer.body": (
            "本ソフトウェアは研究・教育目的のツールです。医療機器ではなく、診断・治療その他の臨床判断には使用できません。\n\n"
            "作成される画像は元画像を加算・平均した派生画像であり、CT値（HU）は元画像と同じ意味を持ちません（特に加算）。\n\n"
            "本ソフトウェアの使用によって生じたいかなる損害についても、作者は責任を負いません。"
        ),
        "disclaimer.dont_show": "次回から表示しない",
    },
    "en": {
        "app.title": "Fused Maker",
        "menu.language": "Language / 言語",
        "menu.lang_auto": "Automatic (follow OS)",
        "menu.help": "Help",
        "menu.about": "About",
        "menu.manual": "User manual (PDF)",
        "menu.licenses": "Licenses",
        "msg.no_licenses": "License files were not found. See {url}.",
        "msg.no_manual": "The manual was not found.",
        "menu.disclaimer": "Disclaimer",
        "input.label": "Input:",
        "input.pick": "Select folder",
        "input.scan": "Load",
        "input.pick_title": "Select input root",
        "col.use": "Use",
        "col.number": "Series#",
        "sel.all": "Select all",
        "sel.none": "Clear",
        "sel.count": "Selected: {n}",
        "col.patient": "PatientID",
        "col.desc": "SeriesDescription",
        "col.kernel": "Kernel",
        "col.n": "Slices",
        "col.dir": "SeriesDir",
        "mode.label": "Mode:",
        "mode.sum": "Sum",
        "mode.avg": "Average",
        "btn.run": "Sum / average and show",
        "view.empty": "The result is shown here",
        "view.slice": "Slice:",
        "btn.save": "Save",
        "save.title": "Select output folder (DICOM series)",
        "reason.not_ct_image": "not a CT image (e.g. dose report)",
        "reason.localizer": "localizer",
        "reason.color": "color image",
        "reason.no_geometry": "no position information",
        "reason.ref_unusable": "first selected series is not usable",
        "check.for_uid": "different scan position (frame of reference)",
        "check.matrix": "different matrix ({a} / {b})",
        "check.spacing": "different pixel spacing",
        "check.orientation": "different image orientation",
        "check.nslices": "different number of slices ({a} / {b})",
        "check.position": "slice positions differ (max {d} mm)",
        "check.kernel": "different kernel ({a} / {b})",
        "check.kvp": "different kVp ({a} / {b})",
        "check.thickness": "different slice thickness ({a} / {b})",
        "check.ma": "different tube current ({a} / {b})",
        "msg.error": "Error",
        "msg.notice": "Notice",
        "msg.confirm": "Confirm",
        "msg.done_title": "Saved",
        "msg.input_missing": "The input folder does not exist.",
        "msg.select2": "Check two or more series to combine.",
        "msg.ref_bad": "The selected series cannot be used: {why}",
        "msg.excluded": "These series do not match the reference series ({ref}) and were excluded:\n\n{list}",
        "msg.too_few": "Fewer than two usable series.",
        "msg.no_result": "There is no result yet.",
        "msg.overwrite": "The folder already contains IM_*.dcm files. Overwrite?\n{dir}",
        "msg.saved": "Saved as a DICOM series:\n{dir}",
        "msg.error_detail": "An error occurred during processing.",
        "status.used": "{mode} N={n}",
        "about.title": "About",
        "about.body": (
            "<h3>Fused Maker (FusedAuto {ver})</h3>"
            "<p>Sums or averages CT series acquired repeatedly at the same position and saves the result "
            "as a new DICOM series.</p>"
            "<p><b>For research use only. Not for diagnostic or therapeutic use.</b></p>"
            "<p>© 2026 {author}<br>"
            "License: PolyForm Noncommercial License 1.0.0<br>"
            "Free for anyone to use, modify and share for noncommercial research and education. "
            "Commercial use is not permitted (inquiries: {contact}).</p>"
            "<p><b>Please cite</b> this software when you use it in published research:<br>"
            "{author}. Fused Maker (FusedAuto), version {ver} [Software]. {cite}</p>"
            "<p>{api} {bver} / Qt {qt} (LGPL v3) / pydicom {pd} / NumPy {np}<br>"
            "For bundled software licenses and source code, see Help &gt; Licenses.<br>"
            "{url}</p>"
        ),
        "disclaimer.title": "Disclaimer",
        "disclaimer.body": (
            "This software is a research and education tool. It is not a medical device and must not be used "
            "for diagnosis, treatment or any other clinical decision.\n\n"
            "Output images are derived images (sums/averages of the originals); their CT numbers (HU) do not "
            "have the same meaning as in the originals, especially for sums.\n\n"
            "The authors accept no liability for any damage arising from the use of this software."
        ),
        "disclaimer.dont_show": "Don't show again",
    },
}


def set_language(lang: str) -> None:
    global _current
    _current = lang if lang in TRANSLATIONS else "en"


def current_language() -> str:
    return _current


def tr(key: str, **kwargs) -> str:
    text = TRANSLATIONS.get(_current, {}).get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def missing_keys() -> dict:
    ja, en = set(TRANSLATIONS["ja"]), set(TRANSLATIONS["en"])
    return {"missing_in_ja": sorted(en - ja), "missing_in_en": sorted(ja - en)}
