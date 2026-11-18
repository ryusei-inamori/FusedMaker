# Fused Maker (FusedAuto)

[![Latest release](https://img.shields.io/github/v/release/ryusei-inamori/FusedMaker)](https://github.com/ryusei-inamori/FusedMaker/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/ryusei-inamori/FusedMaker/total?label=downloads)](https://github.com/ryusei-inamori/FusedMaker/releases)
[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24337767.svg)](https://doi.org/10.5281/zenodo.24337767)

**日本語** | [English](#english)

同じ位置で繰り返し撮影した CT シリーズを **加算** または **平均** して、新しい DICOM シリーズとして保存する研究用ツールです（Windows 10 / 11）。

> ⚠️ **研究・教育用途専用です。** 医療機器ではありません。診断・治療には使用しないでください。

## ダウンロード

[**Releases**](https://github.com/ryusei-inamori/FusedMaker/releases/latest) から `FusedAuto.exe` をダウンロードしてください。インストールは不要で、ダブルクリックで起動します。説明書（PDF、日本語・英語）も同じページにあり、アプリの［ヘルプ］→［説明書］（F1）からも開けます。

初回起動時に「Windows によって PC が保護されました」と表示された場合は、［詳細情報］→［実行］を押してください。

## 主な機能

- フォルダを指定するだけで、DICOM をシリーズごとに自動で分類します
- 撮影位置・スライス位置・マトリクス・枚数が合わないシリーズ（位置決め画像、線量レポート、位置合わせ前のスキャンなど）を自動で除外し、理由を表示します
- 加算で 16bit の範囲を超えても値を切り捨てずに保存します（RescaleIntercept/Slope を自動調整）
- 新しい UID、Series#（元の番号 + 1000）、ImageType=DERIVED\SECONDARY を付けて保存し、使ったシリーズの記録（CSV/JSON）も残します
- 並列処理で高速に計算します
- 日本語 / English

## ライセンス

© 2026 Ryusei Inamori — [PolyForm Noncommercial License 1.0.0](LICENSE)

- **非商用の研究・教育目的であれば、誰でも無料で利用・改変・再配布できます。** 大学などの教育機関、公的研究機関、公的な保健医療機関での利用は、資金の出どころに関係なく認められます。
- **商用利用はできません。** 企業での利用など商用にあたるか迷う場合や、商用利用を希望する場合は mdai.inamori@gmail.com までご相談ください。
- 同梱している Qt / Qt for Python（LGPL v3）などのサードパーティ部品は、このライセンスの対象外です。詳しくは [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt) を参照してください。

## 引用のお願い

研究成果の発表（論文・学会発表など）に使用した場合は、本ソフトウェアを引用してください。

> Inamori, R. (2026). *Fused Maker (FusedAuto): a tool for summing and averaging repeated CT series* [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.24337767

- 上の DOI（10.5281/zenodo.24337767）は全バージョン共通で、常に最新版を指します。
- 使用したバージョンを正確に示したい場合は、[Zenodo のページ](https://doi.org/10.5281/zenodo.24337767)で各バージョンの DOI を確認してください（例：v2.0.0 は 10.5281/zenodo.24337768）。
- GitHub の「Cite this repository」ボタンから、APA / BibTeX 形式の引用文を取得できます。
- Zenodo には各リリースのソースコードが保存されています。実行ファイル（exe）は GitHub の Releases から入手してください。

## ソースからの実行・ビルド

```bat
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py
```

1 ファイルの exe は `build_onefile.bat`（出力は `dist\FusedAuto.exe`）、フォルダ版は `build.bat` でビルドできます。別のバージョンの Qt / Qt for Python でビルドし直すこともできます（LGPL v3）。

---

## English

A research tool that **sums** or **averages** CT series acquired repeatedly at the same position and saves the result as a new DICOM series (Windows 10 / 11).

> ⚠️ **For research and education use only.** Not a medical device. Do not use it for diagnosis or treatment.

### Download

Download `FusedAuto.exe` from [**Releases**](https://github.com/ryusei-inamori/FusedMaker/releases/latest). No installation is needed. The user manuals (PDF, English / Japanese) are on the same page and can be opened from Help > User manual (F1). If Windows shows "Windows protected your PC", click More info > Run anyway.

### License

© 2026 Ryusei Inamori — [PolyForm Noncommercial License 1.0.0](LICENSE)

- **Free for anyone to use, modify and share for noncommercial research and education**, including use by universities, public research organizations and public health organizations regardless of funding.
- **Commercial use is not permitted.** For commercial use or if you are unsure whether your use is commercial, contact mdai.inamori@gmail.com.
- Bundled third-party components such as Qt / Qt for Python (LGPL v3) are not covered by this license; see [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt).

### How to cite

If you use this software in published research, please cite it:

> Inamori, R. (2026). *Fused Maker (FusedAuto): a tool for summing and averaging repeated CT series* [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.24337767

The DOI above (10.5281/zenodo.24337767) covers all versions and always resolves to the latest one. To cite the exact version you used, take its version DOI from the [Zenodo record](https://doi.org/10.5281/zenodo.24337767) (e.g. v2.0.0: 10.5281/zenodo.24337768). The "Cite this repository" button on GitHub gives APA / BibTeX formats. Zenodo archives the source code of each release; the executable is distributed on GitHub Releases.

### Build from source

`pip install -r requirements.txt`, then `python main.py`. `build_onefile.bat` builds `dist\FusedAuto.exe`; `build.bat` builds a one-folder version. You may rebuild with a different Qt / Qt for Python version (LGPL v3).

### Download statistics

A GitHub Actions workflow records the release download counts every day in [`stats/downloads.csv`](stats/downloads.csv) and draws [`stats/downloads.svg`](stats/downloads.svg).
