# -*- coding: utf-8 -*-
"""Builds FusedAuto_manual_ja.pdf / FusedAuto_manual_en.pdf from HTML via headless Chrome."""
import base64
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
VERSION = "2.0.1"
DATE = {"ja": "2026年11月", "en": "November 2026"}


def img(name, caption, width="100%"):
    data = base64.b64encode((HERE / "fig" / name).read_bytes()).decode()
    return (f'<figure><img src="data:image/jpeg;base64,{data}" style="width:{width}">'
            f'<figcaption>{caption}</figcaption></figure>')


CSS = """
@page { size: A4; margin: 18mm 17mm 20mm 17mm;
        @bottom-center { content: counter(page); font-size: 9pt; color: #888; } }
* { box-sizing: border-box; }
body { font-family: 'Noto Sans CJK JP', 'Noto Sans JP', 'DejaVu Sans', sans-serif; font-size: 10.2pt;
       line-height: 1.65; color: #1d232a; }
h1 { font-size: 26pt; margin: 0 0 4mm; color: #0f2a44; letter-spacing: .02em; }
h2 { font-size: 15pt; color: #0f2a44; border-bottom: 2.5px solid #ff7a00; padding-bottom: 1.5mm;
     margin: 9mm 0 3.5mm; page-break-after: avoid; }
h3 { font-size: 11.5pt; color: #0f2a44; margin: 5mm 0 2mm; page-break-after: avoid; }
p { margin: 0 0 2.6mm; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1mm; }
figure { margin: 3mm 0 4.5mm; text-align: center; page-break-inside: avoid; }
figure img { border: 1px solid #c8ced6; border-radius: 4px; }
figcaption { font-size: 8.8pt; color: #5b6673; margin-top: 1.5mm; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; font-size: 9.4pt; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #c8ced6; padding: 1.6mm 2.4mm; vertical-align: top; text-align: left; }
th { background: #eef2f6; color: #0f2a44; }
td.n { width: 9mm; text-align: center; font-weight: bold; color: #ff7a00; }
.cover { height: 245mm; display: flex; flex-direction: column; justify-content: center; }
.cover .sub { font-size: 13pt; color: #3c4a58; margin-bottom: 14mm; }
.cover .meta { font-size: 10pt; color: #5b6673; margin-top: 10mm; }
.note { background: #fff4e8; border-left: 4px solid #ff7a00; padding: 2.5mm 4mm; margin: 3mm 0 4mm;
        page-break-inside: avoid; }
.warn { background: #fdecec; border-left: 4px solid #d23c3c; padding: 2.5mm 4mm; margin: 3mm 0 4mm;
        page-break-inside: avoid; }
.step { display: inline-block; background: #0f2a44; color: #fff; border-radius: 3px; padding: 0 2.2mm;
        margin-right: 2mm; font-size: 9.5pt; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 9pt; background: #f1f3f5; padding: 0 1mm;
       border-radius: 2px; }
.pb { page-break-before: always; }
.toc li { margin-bottom: .6mm; }
"""


def page(lang, body):
    return (f'<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><style>{CSS}</style>'
            f'</head><body>{body}</body></html>')


# ----------------------------------------------------------------------------- Japanese
JA = f"""
<div class="cover">
  <h1>Fused Maker<br><span style="font-size:15pt;color:#5b6673">(FusedAuto)</span></h1>
  <div class="sub">CT画像 加算・平均ツール　取扱説明書</div>
  {img('ja_overview.jpg', '', '100%')}
  <div class="meta">バージョン {VERSION} ／ {DATE['ja']}<br>
  <b>研究用途専用です。診断・治療には使用しないでください。</b></div>
</div>

<h2 class="pb">目次</h2>
<ol class="toc">
<li>このツールでできること</li><li>動作環境と起動</li><li>画面の見方</li><li>使い方（5ステップ）</li>
<li>自動で除外されるシリーズ</li><li>保存されるデータ</li><li>言語の切り替えとヘルプ</li>
<li>よくある質問・困ったとき</li><li>ライセンス・引用・免責事項</li>
</ol>

<h2>1. このツールでできること</h2>
<p>同じ位置で繰り返し撮影した CT シリーズ（例：ファントムの連続スキャン）を、スライスごとに
<b>加算</b>または<b>平均</b>して、新しい DICOM シリーズとして保存します。</p>
<ul>
<li>フォルダを指定するだけで、中の DICOM をシリーズごとに自動で分類します（フォルダ構成は問いません）。</li>
<li>撮影位置・スライス位置・マトリクスなどが合わないシリーズは自動で除外し、理由を表示します。</li>
<li>結果をその場で確認し（スライス送り・WL/WW 調整）、DICOM として保存できます。</li>
<li>日本語 / English の画面に対応しています。</li>
</ul>
<div class="note"><b>加算と平均の違い</b><br>
<b>平均</b>：CT値（HU）は元画像と同じ尺度のまま、ノイズ（SD）が約 1/√N に下がります。<br>
<b>加算</b>：値が N 倍になります（例：水 0 HU → 0、空気 −1000 HU → −1000×N）。保存時は値を切り捨てずに記録し、表示用の WL/WW も N 倍にします。</div>

<h2>2. 動作環境と起動</h2>
<table>
<tr><th style="width:32mm">OS</th><td>Windows 10 / 11（64bit）</td></tr>
<tr><th>インストール</th><td>不要です。<code>FusedAuto.exe</code> を好きな場所（デスクトップ、USB など）に置いてダブルクリックします。</td></tr>
<tr><th>メモリ</th><td>8 GB 以上を推奨します（512×512×320 枚のシリーズで、結果の保持に約 0.4 GB を使います）。</td></tr>
<tr><th>入力データ</th><td>非圧縮・圧縮どちらの CT 画像（DICOM）も読めます。</td></tr>
</table>
<h3>初めて起動するとき</h3>
<ul>
<li>「Windows によって PC が保護されました」と表示された場合は、<b>［詳細情報］→［実行］</b>を押してください（署名のないアプリで表示されるものです）。</li>
<li>起動時に中身を展開するため、画面が出るまで数秒かかります。</li>
<li>最初に免責事項が表示されます。内容を確認して［OK］を押してください（「次回から表示しない」にチェックすると以後は表示されません）。</li>
</ul>

<h2>3. 画面の見方</h2>
{img('ja_overview.jpg', '図1　メイン画面', '62%')}
<table>
<tr><th>No.</th><th style="width:38mm">名前</th><th>説明</th></tr>
<tr><td class="n">1</td><td>メニュー</td><td>［言語 / Language］で表示言語を切り替えます。［ヘルプ］から説明書・免責事項・バージョン情報を開けます。</td></tr>
<tr><td class="n">2</td><td>入力フォルダ</td><td>DICOM が入ったフォルダを指定し、［読み込み］で一覧を作ります。パスを直接入力して Enter でも読み込めます。</td></tr>
<tr><td class="n">3</td><td>シリーズ一覧</td><td>見つかったシリーズを撮影順に表示します。「使用」列のチェックで加算するシリーズを選びます（行のどこをクリックしても切り替わります）。灰色の行は加算に使えないシリーズです。</td></tr>
<tr><td class="n">4</td><td>選択ボタン</td><td>［すべて選択］［選択解除］と、現在の選択数です。</td></tr>
<tr><td class="n">5</td><td>処理と実行</td><td>「加算」または「平均」を選び、［加算/平均して表示］で計算します。</td></tr>
<tr><td class="n">6</td><td>結果表示</td><td>計算結果の画像です。上に「加算 N=6」のように処理と枚数を表示します。マウスホイールでスライスを送れます。</td></tr>
<tr><td class="n">7</td><td>スライス・WL/WW</td><td>表示するスライス番号と、ウィンドウレベル（WL）・幅（WW）です。</td></tr>
<tr><td class="n">8</td><td>保存</td><td>結果を DICOM シリーズとして保存します。</td></tr>
</table>

<h2 class="pb">4. 使い方（5ステップ）</h2>
<h3><span class="step">STEP 1</span>フォルダを読み込む</h3>
<p>［フォルダ選択］で DICOM の入ったフォルダを選び（①）、［読み込み］を押します（②）。サブフォルダも含めて探し、シリーズごとに一覧にします（③）。</p>
{img('ja_step1.jpg', '図2　フォルダを読み込んだところ。灰色の行（位置決め画像・線量レポート）はチェックできません', '66%')}

<h3><span class="step">STEP 2</span>加算するシリーズにチェックを入れる</h3>
<p>「使用」列にチェックを入れます（①）。［すべて選択］で一度にチェックし、不要なものだけ外すと早く選べます（②）。</p>
{img('ja_step2.jpg', '図3　シリーズにチェックを入れたところ', '66%')}
<div class="note"><b>基準シリーズは自動で決まります</b><br>
チェックしたシリーズのうち、撮影位置などが互いに一致するシリーズが最も多いグループから基準が選ばれます。
位置合わせ前のスキャンなどが 1 本混ざっていても、それが基準になることはありません。</div>

<h3><span class="step">STEP 3</span>加算／平均を実行する</h3>
<p>「処理」で<b>加算</b>または<b>平均</b>を選び、［加算/平均して表示］を押します（①）。基準と合わないシリーズがあった場合は、除外したシリーズと理由が表示されます（下図では #2 SE26 が「撮影位置（座標系）が違う」ため除外されています）。［OK］を押すと、残りのシリーズで計算します。</p>
{img('ja_step3.jpg', '図4　合わないシリーズを除外したときのお知らせ', '66%')}

<h3><span class="step">STEP 4</span>結果を確認する</h3>
<p>結果が右側に表示されます（①）。マウスホイールまたはスライス欄でスライスを送り、WL / WW で見やすさを調整します（②）。加算では、元画像の WL/WW を N 倍した値が自動で設定されます。</p>
{img('ja_step4.jpg', '図5　6 シリーズを加算した結果（スライス 209）', '66%')}

<h3><span class="step">STEP 5</span>保存する</h3>
<p>［保存］を押して（①）、保存先フォルダを選びます。<code>IM_0001.dcm</code> から順にファイルが作られ、完了するとメッセージが表示されます。保存先に既に <code>IM_*.dcm</code> がある場合は、上書きしてよいか確認されます。</p>
{img('ja_step5.jpg', '図6　保存が完了したところ', '66%')}
<div class="note">結果ごとに<b>空のフォルダ</b>を用意して保存すると、ファイルが混ざらず管理しやすくなります。</div>

<h2>5. 自動で除外されるシリーズ</h2>
<p>次のシリーズは加算に使いません。灰色で表示されるもの（チェック不可）と、実行時に除外されるものがあります。</p>
<table>
<tr><th style="width:62mm">理由（画面の表示）</th><th>主な例・意味</th></tr>
<tr><td>位置決め画像</td><td>スキャノグラム（スカウト）。一覧で灰色になり、チェックできません。</td></tr>
<tr><td>CT画像ではない（線量レポート等）</td><td>線量サマリなどの画像。一覧で灰色になります。</td></tr>
<tr><td>カラー画像 ／ 位置情報がない</td><td>加算に必要な情報がない画像。一覧で灰色になります。</td></tr>
<tr><td>撮影位置（座標系）が違う</td><td>寝台位置を変えた・位置合わせ前のスキャンなど。FrameOfReferenceUID が異なります。</td></tr>
<tr><td>スライス位置がずれている</td><td>同じ座標系でも、各スライスの位置が 0.01 mm を超えて違うもの。</td></tr>
<tr><td>スライス数 ／ マトリクス ／ ピクセル間隔 ／ 画像の向きが違う</td><td>再構成条件（FOV、枚数など）が異なるシリーズ。</td></tr>
</table>
<p>カーネル・管電圧・管電流・スライス厚が違うだけのシリーズは除外しません（同じ位置であれば加算できます）。条件をそろえたい場合は、一覧の「カーネル」列なども確認してチェックしてください。</p>

<h2>6. 保存されるデータ</h2>
<table>
<tr><th style="width:44mm">項目</th><th>内容</th></tr>
<tr><td>ファイル</td><td><code>IM_0001.dcm</code>〜（スライス順）。元画像と同じ位置・向き・ピクセル間隔です。</td></tr>
<tr><td>Series#</td><td>基準シリーズの番号 + 1000（例：5 → 1005）。元のシリーズと区別できます。</td></tr>
<tr><td>シリーズ説明</td><td>元の説明の後ろに <code>_SUM_N6</code> / <code>_AVG_N6</code> のように処理と枚数を付けます。</td></tr>
<tr><td>UID</td><td>Series Instance UID・SOP Instance UID は新しく作成します。Study（検査）は元のままです。</td></tr>
<tr><td>ImageType</td><td><code>DERIVED\\SECONDARY</code>（派生画像）。DerivationDescription に使用シリーズを記録します。</td></tr>
<tr><td>CT値（HU）</td><td>加算で 16bit の範囲を超えても値を切り捨てず、RescaleSlope / Intercept を自動で調整して正確に保存します。平均は 1 HU 単位に丸めます。</td></tr>
<tr><td>WL / WW</td><td>平均は元のまま、加算は N 倍にします。</td></tr>
<tr><td>記録ファイル</td><td><code>fused_log_日付_時刻.csv</code> と <code>.json</code>。使ったシリーズ番号とフォルダを記録します（論文の方法欄などに利用できます）。</td></tr>
</table>

<h2>7. 言語の切り替えとヘルプ</h2>
<p>［言語 / Language］メニューで、自動（OS の言語に合わせる）・日本語・English を選べます。切り替えはすぐ反映され、次回起動時も同じ言語になります。</p>
{img('ja_lang.jpg', '図7　言語メニュー', '52%')}
<p>［ヘルプ］メニューから、この説明書（F1 キーでも開けます）、ライセンス、免責事項、バージョン情報を表示できます。</p>
{img('ja_help.jpg', '図8　ヘルプメニュー（説明書・ライセンス・免責事項・このアプリについて）', '60%')}

<h2>8. よくある質問・困ったとき</h2>
<table>
<tr><th style="width:62mm">症状</th><th>対処</th></tr>
<tr><td>起動時に「Windows によって PC が保護されました」と出る</td><td>［詳細情報］→［実行］で起動できます。</td></tr>
<tr><td>読み込みがとても遅い</td><td>データが OneDrive などクラウド上にあり「オンラインのみ」になっていると、読み込みのたびにダウンロードが発生します。フォルダを右クリック →「このデバイス上に常に保持する」にするか、ローカルにコピーしてください。</td></tr>
<tr><td>「使えるシリーズが2つ未満です」と出る</td><td>チェックしたシリーズの撮影位置・枚数などがそろっていません。除外の理由を確認し、同じ条件のシリーズを 2 つ以上選んでください。</td></tr>
<tr><td>一覧にシリーズが出てこない</td><td>DICOM ファイル（拡張子 .dcm または拡張子なし）があるフォルダを指定しているか確認してください。</td></tr>
<tr><td>加算画像が真っ白／真っ黒に見える</td><td>WL / WW を調整してください。加算では値が N 倍になるため、WW も大きくする必要があります。</td></tr>
<tr><td>他のビューアで開くと値が大きい</td><td>加算画像は値が N 倍です（仕様）。元と同じ尺度で見たい場合は「平均」を使ってください。</td></tr>
<tr><td>保存先に前の結果が残っている</td><td>上書き確認で［はい］を選ぶと、同じ名前のファイルを上書きします。結果ごとに新しいフォルダを使うことをおすすめします。</td></tr>
</table>

<h2>9. ライセンス・引用・免責事項</h2>
<h3>ライセンス</h3>
<p>© 2026 Ryusei Inamori。本ソフトウェアは <b>PolyForm Noncommercial License 1.0.0</b> で提供しています。</p>
<ul>
<li><b>非商用の研究・教育目的であれば、誰でも無料で利用・改変・再配布できます。</b>大学などの教育機関、公的研究機関、公的な保健医療機関での利用は、資金の出どころに関係なく認められます。</li>
<li><b>商用利用はできません。</b>商用にあたるか迷う場合や商用利用を希望する場合は、mdai.inamori@gmail.com までご相談ください。</li>
<li>再配布するときは、LICENSE ファイル（または https://polyformproject.org/licenses/noncommercial/1.0.0 ）と、その中の「Required Notice」の行を一緒に渡してください。</li>
</ul>
<h3>引用のお願い</h3>
<p>研究成果の発表（論文・学会発表など）に使用した場合は、本ソフトウェアを引用してください。引用情報は GitHub（https://github.com/ryusei-inamori/FusedMaker）の「Cite this repository」または Zenodo の DOI ページから取得できます。</p>
<div class="note">例：Inamori, R. (2026). Fused Maker (FusedAuto): a tool for summing and averaging repeated CT series [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.24337767<br>（この DOI は全バージョン共通です。使用したバージョンの DOI は Zenodo のページで確認できます。）</div>
<h3>免責事項</h3>
<div class="warn">本ソフトウェアは研究・教育目的のツールです。医療機器ではなく、診断・治療その他の臨床判断には使用できません。
作成される画像は元画像を加算・平均した派生画像であり、CT値（HU）は元画像と同じ意味を持ちません（特に加算）。
本ソフトウェアの使用によって生じたいかなる損害についても、作者は責任を負いません。</div>
<h3>同梱ソフトウェア</h3>
<p>Qt / Qt for Python（PySide6 6.12、LGPL v3）、pydicom（MIT）、NumPy（BSD）、Python（PSF）などを利用しています。これらは本ソフトウェアのライセンスの対象外で、それぞれのライセンスが適用されます。ライセンス全文とソースの入手方法は、アプリの［ヘルプ］→［ライセンス］、または THIRD_PARTY_LICENSES.txt を参照してください。</p>
"""

# ----------------------------------------------------------------------------- English
EN = f"""
<div class="cover">
  <h1>Fused Maker<br><span style="font-size:15pt;color:#5b6673">(FusedAuto)</span></h1>
  <div class="sub">CT image summation / averaging tool — User manual</div>
  {img('en_overview.jpg', '', '100%')}
  <div class="meta">Version {VERSION} / {DATE['en']}<br>
  <b>For research use only. Not for diagnostic or therapeutic use.</b></div>
</div>

<h2 class="pb">Contents</h2>
<ol class="toc">
<li>What the tool does</li><li>Requirements and launching</li><li>The main window</li><li>How to use it (5 steps)</li>
<li>Series that are excluded automatically</li><li>What is saved</li><li>Language and Help</li>
<li>FAQ and troubleshooting</li><li>License, citation and disclaimer</li>
</ol>

<h2>1. What the tool does</h2>
<p>Fused Maker <b>sums</b> or <b>averages</b> CT series acquired repeatedly at the same position (for example,
repeated phantom scans), slice by slice, and saves the result as a new DICOM series.</p>
<ul>
<li>Point it at a folder: DICOM files are grouped into series automatically, whatever the folder layout.</li>
<li>Series whose position, slice locations or matrix do not match are excluded automatically, with the reason shown.</li>
<li>Check the result on screen (slice scrolling, WL/WW) and save it as DICOM.</li>
<li>The interface is available in English and Japanese.</li>
</ul>
<div class="note"><b>Sum vs. average</b><br>
<b>Average</b>: CT numbers (HU) stay on the original scale and noise (SD) drops by roughly 1/√N.<br>
<b>Sum</b>: values are multiplied by N (water 0 HU → 0, air −1000 HU → −1000×N). Values are saved without clipping, and the display window (WL/WW) is scaled by N.</div>

<h2>2. Requirements and launching</h2>
<table>
<tr><th style="width:32mm">OS</th><td>Windows 10 / 11 (64-bit)</td></tr>
<tr><th>Installation</th><td>None. Put <code>FusedAuto.exe</code> anywhere (desktop, USB stick, …) and double-click it.</td></tr>
<tr><th>Memory</th><td>8 GB or more recommended (a 512×512×320 result takes about 0.4 GB).</td></tr>
<tr><th>Input</th><td>CT images (DICOM), uncompressed or compressed.</td></tr>
</table>
<h3>First launch</h3>
<ul>
<li>If Windows shows “Windows protected your PC”, click <b>More info → Run anyway</b> (shown for unsigned apps).</li>
<li>The app unpacks itself at start-up, so the window takes a few seconds to appear.</li>
<li>A disclaimer is shown first. Read it and click OK (check “Don’t show again” to hide it next time).</li>
</ul>

<h2>3. The main window</h2>
{img('en_overview.jpg', 'Figure 1. Main window', '74%')}
<table>
<tr><th>No.</th><th style="width:38mm">Part</th><th>Description</th></tr>
<tr><td class="n">1</td><td>Menu</td><td>Language / 言語 switches the language. Help opens this manual, the disclaimer and version information.</td></tr>
<tr><td class="n">2</td><td>Input folder</td><td>Choose the folder containing DICOM files and click Load. You can also type a path and press Enter.</td></tr>
<tr><td class="n">3</td><td>Series list</td><td>Series found, in acquisition order. Check “Use” for the series to combine (clicking anywhere on a row toggles it). Gray rows cannot be used.</td></tr>
<tr><td class="n">4</td><td>Selection</td><td>Select all / Clear, and the number of checked series.</td></tr>
<tr><td class="n">5</td><td>Mode and run</td><td>Choose Sum or Average and click “Sum / average and show”.</td></tr>
<tr><td class="n">6</td><td>Result view</td><td>The result image, labeled like “Sum N=6”. Use the mouse wheel to change the slice.</td></tr>
<tr><td class="n">7</td><td>Slice, WL/WW</td><td>Slice number, window level (WL) and window width (WW).</td></tr>
<tr><td class="n">8</td><td>Save</td><td>Saves the result as a DICOM series.</td></tr>
</table>

<h2 class="pb">4. How to use it (5 steps)</h2>
<h3><span class="step">STEP 1</span>Load a folder</h3>
<p>Click Select folder and choose the folder with the DICOM files (1), then click Load (2). Sub-folders are searched too, and the series are listed (3).</p>
{img('en_step1.jpg', 'Figure 2. After loading. Gray rows (localizer, dose report) cannot be checked', '66%')}

<h3><span class="step">STEP 2</span>Check the series to combine</h3>
<p>Check the “Use” column (1). The quickest way is often Select all, then uncheck the ones you do not want (2).</p>
{img('en_step2.jpg', 'Figure 3. Series checked', '66%')}
<div class="note"><b>The reference series is chosen automatically</b><br>
It is taken from the largest group of checked series that match each other. A single stray series
(for example, a scan taken before repositioning) never becomes the reference.</div>

<h3><span class="step">STEP 3</span>Run the sum / average</h3>
<p>Choose <b>Sum</b> or <b>Average</b> in Mode and click “Sum / average and show” (1). If some series do not match the reference, they are listed with the reason (below, #2 SE26 is excluded because of a different scan position). Click OK and the remaining series are combined.</p>
{img('en_step3.jpg', 'Figure 4. Notice about excluded series', '66%')}

<h3><span class="step">STEP 4</span>Check the result</h3>
<p>The result appears on the right (1). Scroll with the mouse wheel or the Slice box and adjust WL / WW (2). For sums, the original WL/WW multiplied by N is set automatically.</p>
{img('en_step4.jpg', 'Figure 5. Sum of six series (slice 209)', '66%')}

<h3><span class="step">STEP 5</span>Save</h3>
<p>Click Save (1) and choose an output folder. Files <code>IM_0001.dcm</code>, <code>IM_0002.dcm</code>, … are written and a message appears when done.</p>
{img('en_step5.jpg', 'Figure 6. Saving finished', '66%')}
<p>If the folder already contains <code>IM_*.dcm</code> files, you are asked whether to overwrite them:</p>
{img('en_overwrite.jpg', 'Figure 7. Overwrite confirmation', '52%')}
<div class="note">Using a <b>new, empty folder</b> for each result keeps files from getting mixed up.</div>

<h2>5. Series that are excluded automatically</h2>
<p>The following series are not used. Some are grayed out in the list; others are excluded when you run.</p>
<table>
<tr><th style="width:62mm">Reason (as shown)</th><th>Typical cause</th></tr>
<tr><td>localizer</td><td>Scanogram / scout. Grayed out, cannot be checked.</td></tr>
<tr><td>not a CT image (e.g. dose report)</td><td>Dose summary screens etc. Grayed out.</td></tr>
<tr><td>color image / no position information</td><td>Images without the information needed. Grayed out.</td></tr>
<tr><td>different scan position (frame of reference)</td><td>Table moved, or a scan before repositioning (different FrameOfReferenceUID).</td></tr>
<tr><td>slice positions differ</td><td>Same frame of reference but slice positions differ by more than 0.01 mm.</td></tr>
<tr><td>different number of slices / matrix / pixel spacing / orientation</td><td>Different reconstruction settings (FOV, number of images, …).</td></tr>
</table>
<p>Series that differ only in kernel, kVp, mA or slice thickness are not excluded (they can be combined if the position matches). Check the Kernel column etc. if you need identical conditions.</p>

<h2>6. What is saved</h2>
<table>
<tr><th style="width:44mm">Item</th><th>Content</th></tr>
<tr><td>Files</td><td><code>IM_0001.dcm</code> … in slice order, with the same position, orientation and pixel spacing as the originals.</td></tr>
<tr><td>Series#</td><td>Reference series number + 1000 (e.g. 5 → 1005), so it is easy to tell apart.</td></tr>
<tr><td>Series description</td><td>Original description plus <code>_SUM_N6</code> / <code>_AVG_N6</code>.</td></tr>
<tr><td>UIDs</td><td>New Series Instance UID and SOP Instance UIDs. The Study stays the same.</td></tr>
<tr><td>ImageType</td><td><code>DERIVED\\SECONDARY</code>. DerivationDescription records the series used.</td></tr>
<tr><td>CT numbers (HU)</td><td>Sums beyond the 16-bit range are stored exactly, never clipped (RescaleSlope / Intercept are adjusted automatically). Averages are rounded to 1 HU.</td></tr>
<tr><td>WL / WW</td><td>Unchanged for averages; multiplied by N for sums.</td></tr>
<tr><td>Log files</td><td><code>fused_log_date_time.csv</code> and <code>.json</code> list the series numbers and folders used (handy for the methods section of a paper).</td></tr>
</table>

<h2>7. Language and Help</h2>
<p>Use the Language / 言語 menu to choose Automatic (follow the OS), 日本語 or English. The change applies immediately and is remembered.</p>
{img('en_lang.jpg', 'Figure 8. Language menu', '52%')}
<p>The Help menu opens this manual (also F1), the licenses, the disclaimer and version information.</p>
{img('en_help.jpg', 'Figure 9. Help menu (manual, licenses, disclaimer, about)', '60%')}

<h2>8. FAQ and troubleshooting</h2>
<table>
<tr><th style="width:62mm">Problem</th><th>What to do</th></tr>
<tr><td>“Windows protected your PC” at start-up</td><td>Click More info → Run anyway.</td></tr>
<tr><td>Loading is very slow</td><td>If the data is in OneDrive etc. and “online-only”, every read downloads the file. Right-click the folder → “Always keep on this device”, or copy the data to a local disk.</td></tr>
<tr><td>“Fewer than two usable series.”</td><td>The checked series do not match in position, slice count, etc. Check the reasons shown and select at least two matching series.</td></tr>
<tr><td>No series appear in the list</td><td>Make sure the folder contains DICOM files (.dcm or no extension).</td></tr>
<tr><td>The sum looks all white / all black</td><td>Adjust WL / WW. Sums are N times larger, so WW must be larger too.</td></tr>
<tr><td>Values look large in another viewer</td><td>Sums are N times the original values (by design). Use Average to keep the original scale.</td></tr>
<tr><td>Old results remain in the output folder</td><td>Answering Yes to the overwrite question replaces files with the same names. Use a new folder for each result.</td></tr>
</table>

<h2>9. License, citation and disclaimer</h2>
<h3>License</h3>
<p>© 2026 Ryusei Inamori. This software is provided under the <b>PolyForm Noncommercial License 1.0.0</b>.</p>
<ul>
<li><b>Anyone may use, modify and share it free of charge for noncommercial research and education</b>, including educational institutions, public research organizations and public health organizations, regardless of funding.</li>
<li><b>Commercial use is not permitted.</b> If you are unsure whether your use is commercial, or want to use it commercially, contact mdai.inamori@gmail.com.</li>
<li>When you share copies, include the LICENSE file (or https://polyformproject.org/licenses/noncommercial/1.0.0 ) and its “Required Notice” lines.</li>
</ul>
<h3>How to cite</h3>
<p>If you use this software in published research (papers, conference presentations, …), please cite it. Citation information is available from “Cite this repository” on GitHub (https://github.com/ryusei-inamori/FusedMaker) or from the Zenodo DOI page.</p>
<div class="note">Example: Inamori, R. (2026). Fused Maker (FusedAuto): a tool for summing and averaging repeated CT series [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.24337767<br>(This DOI covers all versions; the DOI of each version is listed on the Zenodo page.)</div>
<h3>Disclaimer</h3>
<div class="warn">This software is a research and education tool. It is not a medical device and must not be used for diagnosis,
treatment or any other clinical decision. Output images are derived images (sums/averages of the originals); their CT numbers
(HU) do not have the same meaning as in the originals, especially for sums. The authors accept no liability for any damage
arising from the use of this software.</div>
<h3>Bundled software</h3>
<p>This software uses Qt / Qt for Python (PySide6 6.12, LGPL v3), pydicom (MIT), NumPy (BSD), Python (PSF) and others. They are not covered by the FusedAuto license and remain under their own licenses. For full license texts and how to obtain the source code, see Help &gt; Licenses in the application or THIRD_PARTY_LICENSES.txt.</p>
"""


def build(lang, body):
    html = OUT / f"manual_{lang}.html"
    html.write_text(page(lang, body), encoding="utf-8")
    pdf = OUT / f"FusedAuto_manual_{lang}.pdf"
    subprocess.run(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--no-pdf-header-footer", f"--print-to-pdf={pdf}", html.as_uri()],
                   check=True, capture_output=True, timeout=180)
    print(pdf, pdf.stat().st_size)


if __name__ == "__main__":
    for lang in (sys.argv[1:] or ["ja", "en"]):
        build(lang, JA if lang == "ja" else EN)
