# FTIR 自動 Annotation 工具 — 規格書

版本：v1.2.1（2026-06-12）— 資料庫範本更新為 Database_EMC.csv（格式不變）；Step 5 採下拉單選＋第二名參考；Δν 改為容差縮放係數
平台：Streamlit 本機網頁應用（Python）
範圍：單一光譜處理，無批次

---

## 1. 概述

讀取單一 FTIR 光譜 CSV（%T），自動偵測吸收峰，與官能基資料庫比對打分，先預覽比對結果，再由用戶逐峰確認，最後輸出含參數紀錄的標註 CSV 與 PNG 光譜圖。流程為六步 wizard。

---

## 2. 輸入規格（依範例檔固定，不提供手動欄位對應；不符即報錯）

### 2.1 光譜檔（Spectra）

| 項目 | 規格 |
|---|---|
| 結構 | 第 1 列為儀器 metadata，**一律忽略**；第 2 列為標頭 `cm-1,%T`；其後為資料 |
| 編碼 | UTF-8（含 BOM），以 `utf-8-sig` 讀取 |
| 訊號 | 僅 %T，無吸光度、無轉換功能；峰方向朝下 |
| 波數順序 | 接受升/降冪（範例為 4000→650 降冪），載入後內部統一升冪 |
| 重複波數 | 取平均並提示（已確認） |
| 驗證 | 標頭須含 `cm-1` 與 `%T`（容許大小寫與空白差異）、兩欄皆數值、資料點 ≥ 50；不符顯示具體錯誤訊息並擋下 |

內部訊號處理約定：所有基線校正、平滑、峰偵測、FWHM 計算皆在反轉訊號 y = 100 − %T（峰朝上）上進行；圖面顯示一律為原始 %T 方向。

### 2.2 資料庫檔（Database）— 中心值 ± 容差格式

| 欄位 | 必填 | 範例（取自 EMC 範本） |
|---|---|---|
| Functional Group | ✔ | BMI |
| Vibration Mode | ✔ | C=O Symmetric Stretching |
| Peak Position (cm-1) | ✔ | 1771 |
| Peak Position Tolerance (cm-1) | ✔ | 15 |
| FWHM (cm-1) | ✘（可留空） | 30 |
| FWHM Tolerance (cm-1) | ✘（可留空） | 20 |

- 範圍由中心值與容差推導：位置範圍 = P ± T_p；FWHM 範圍 = W ± T_w。
- FWHM 與其 Tolerance 須成對填寫或成對留空；留空者該筆只計位置分。
- 編碼：先試 `utf-8-sig`，失敗改 `cp950`（Big5）。資料庫可能為 Big5 編碼並含科學符號（如 CE 的 `O-C≡N` 三鍵符號 ≡）；輸出 CSV 為 utf-8-sig，此類字元在 Excel 可正常顯示。
- 一個官能基可有多筆震動模式列；同一組（Functional Group, Vibration Mode）標籤亦可合法重複出現（例如 Long C-C Chain 的 CH2 Asymmetric Stretching 同時列於 2925 與 2853）。**驗證不可將重複列視為錯誤**，每一列皆為獨立候選。
- 驗證：六欄名齊全（容許大小寫/空白差異）、數值合法、容差 > 0；不符即報錯。
- 來源：`databases/` 內建清單下拉選擇（內建 `Database_EMC.csv`，含 BMI／Anhydride／Ester／Acrylate／Isocyanurate／CE／Methyl／Methylene／SiO2 等 26 筆），或用戶上傳。載入後以表格顯示全部內容供預覽。


---

## 3. 流程與導航（六步）

```
Step 1 載入光譜 → Step 2 選擇資料庫 → Step 3 Peak picking
→ Step 4 Annotation 預覽 → Step 5 確認 Annotation → Step 6 匯出
```

單頁 wizard，以 `session_state["step"]` 控制；所有參數存自管 session_state dict，返回不重設參數。

### 倒回與狀態規則

| 動作 | 行為 |
|---|---|
| **Step 5 → Step 4**（唯一警告點） | 跳確認警告：「返回後目前所有 annotation 選擇將遺失，並重設為預設值。」確認後返回並清空選擇 |
| Step 6 → Step 5 | 保留所有選擇，不警告 |
| Step 4 內調整比對參數 | 即時重算候選、分數與排名；此步為唯讀預覽，使用者無法手動調整 annotation，故無選擇可失 |
| 進入 Step 5 | 依當下 Step 4 的結果初始化預設選擇 |
| 其他返回 | 直接返回，不警告 |

---

## 4. 前處理（Step 3 內，皆可開關；預設值取自範例輸出）

處理順序：基線校正 → 平滑（皆作用於反轉訊號）。

| 功能 | 方法 | 參數（預設） | 預設狀態 |
|---|---|---|---|
| 基線校正 | pybaselines ALS (asls) | lam = 1e6（log 滑桿 1e3–1e9）、p = 0.01（0.001–0.1）、diff_order = 2（1–3） | 開 |
| 平滑 | Savitzky–Golay | window = 11 點（奇數 5–51）、polyorder = 3（2–5） | 關 |

預覽圖同時顯示原始 %T 與處理後曲線（映回 %T 方向）。

---

## 5. Peak picking（Step 3）

演算法：`scipy.signal.find_peaks`（作用於處理後反轉訊號），FWHM 以 `peak_widths(rel_height=0.5)` 計算並換算 cm⁻¹。

| 參數 | 範圍 | 預設（取自範例） | 備註 |
|---|---|---|---|
| Prominence | 0.05–20%（反轉訊號全幅相對值） | 0.5% | 主要靈敏度參數 |
| Minimum Peak Height | 絕對值，選用 | 關閉（Not Used） | |
| Minimum Peak Spacing | 0–50 cm⁻¹ | 5 | 內部換算為資料點數 |
| FWHM Filter | min~max (cm⁻¹) | 開，2~250 | 排除過窄雜訊與過寬殘留 |

每峰輸出：峰編號、峰位 (cm⁻¹)、強度（基線校正後峰深，%T 單位）、FWHM (cm⁻¹)、prominence。

預覽：Plotly 互動光譜（縮放、hover）＋峰標記與編號＋peak list 表格。偵測 0 峰時提示調低 prominence 並擋下一步。

---

## 6. 比對與打分（核心邏輯）

容差皆使用資料庫**每筆自帶**的 T_p、T_w。

### 6.1 候選資格

單一規則：**位置分 > 0 即為候選**。FWHM 永不影響候選資格，僅影響分數與排名。

### 6.2 位置分（嚴苛）

峰位 p，資料庫中心 P、容差 T_p。距離 d = max(|p − P| − T_p, 0)（即超出範圍邊界的距離）。

```
score_pos = 1                    （d = 0，落在 P ± T_p 內）
score_pos = 1 − d / (k_pos·T_p)  （線性衰減）
score_pos = 0                    （d ≥ k_pos·T_p）
```

k_pos 預設 2（可調 1–5）。範例：1780 ± 20 → 超出邊界 40 cm⁻¹（即 < 1720 或 > 1840）歸零。

### 6.3 FWHM 分（寬鬆，可歸零）

峰寬 w，資料庫中心 W、容差 T_w。距離 d_w = max(|w − W| − T_w, 0)。

```
score_fwhm = 1                      （d_w = 0，落在 W ± T_w 內）
score_fwhm = 1 − d_w / (k_fwhm·T_w) （線性衰減）
score_fwhm = 0                      （d_w ≥ k_fwhm·T_w）
```

k_fwhm 預設 3（可調 1–6）。驗算：理想 10 ± 5 → 邊界 15 ＋ 3×5 ＝ 實測 30 cm⁻¹ 歸零 ✓。

### 6.4 總分、排序與門檻

```
S = (1 − w_f) · score_pos + w_f · score_fwhm
```

- w_f：FWHM 權重滑桿 0–1，預設 0.2；調 0 即完全忽略寬度。
- 資料庫該筆未填 FWHM → 該候選 S = score_pos。
- 候選依 S 高至低排序；同分以 score_pos 高者優先。
- Score Threshold（預設 0.5）：決定 Step 5 的**預設選擇**，不過濾候選清單——所有候選照列，最終由用戶決定。

### 6.5 容差縮放係數（已定案）

全域參數 **Tolerance Scale s**（預設 1.0，範圍 0.5–3）：比對時每筆容差一律以 T_p′ = s·T_p、T_w′ = s·T_w 代入 6.2／6.3 公式，讓用戶不改資料庫即可整體放寬或收緊。匯出參數區原 Δν 列改名為 `Tolerance Scale`。

### 6.6 無候選的峰

標記 Unassigned，保留於 peak list 與輸出。

---

## 7. Step 4 — Annotation 預覽（唯讀）

- **參數區**：w_f、Tolerance Scale、Score Threshold、k_pos、k_fwhm。調整即重算。
- **Plotly 光譜**：每峰標示第 1 名 annotation 與分數；Unassigned 以灰色標示。
- **候選總表**（唯讀）：每峰列出全部候選——排名、Functional Group、Vibration Mode、總分 S、score_pos、score_fwhm。
- 本步**不提供任何手動選擇**，純參數調整與結果檢視。

---

## 8. Step 5 — 確認 Annotation（逐峰確認區）

### 確認機制（已定案：下拉單選）

- 每峰一列：峰位、強度、FWHM ＋ **下拉單選**。選項為該峰全部候選（顯示排名、官能基、震動模式、總分），末端固定「不標註」。
- 預設選擇：第 1 名 S ≥ Score Threshold → 預選第 1 名；否則預選「不標註」。
- Unassigned 峰：無下拉，僅顯示資訊。
- 快捷按鈕：「全部採用第一名」「全部重設為自動建議」。
- Plotly 光譜即時反映目前選擇；與自動建議不同（用戶改過）的峰以強調色標示，不標註／Unassigned 以灰色標示。

---

## 9. 輸出（Step 6）

### 9.1 CSV（多區段，結構照 Output_example.csv）

```
Peak Picking Parameter
Prominence,0.50%
Minimum Peak Height,Not Used        ← 關閉時寫 Not Used；範例拼字 Mininum 修正為 Minimum
Minimum Peak Spacing,5
FWHM Filter,2~250                   ← 關閉時寫 Not Used
Baseline Calibration Lamda,1000000  ← 基線關閉時三列皆寫 Baseline Off
Baseline Calibration P,0.01
Baseline Diff_Order,2
Smoothing Window,Smoothing Off      ← 開啟時寫實際值
Polyorder,Smoothing Off
（空列）
Peak Annotation Parameter
w_f,…
Tolerance Scale,…
Score Threshold,…
k_pos,…
k_fwhm,…
（空列）
Annotation Result
Peak Position (cm-1),Annotation 1,Annotation 1 Score,Vibration Mode,Functional Group,Annotation 2,Annotation 2 score,Vibration Mode,Functional Group,…
```

- 結果列：峰位四捨五入至整數；annotation 欄組固定 2 組，每組 =（官能基名、分數〔至多 2 位小數〕、Vibration Mode、Functional Group）。
- **Annotation 1 = 用戶於 Step 5 選定者**；**Annotation 2 = 排名最高且非所選的候選**，自動附作參考（不存在則留空）。
- Unassigned 峰：Annotation 1 寫 `Unassigned`，其餘留空。
- 用戶選「不標註」的峰：Annotation 1 寫 `Not Annotated`，Annotation 2 照常附最高分候選作參考。
- 編碼 `utf-8-sig`（Excel 直接開啟）。

### 9.2 PNG 光譜圖

- matplotlib 繪製：原始 %T 光譜，x 軸依 FTIR 慣例 4000→650 由左至右遞減。
- 每峰標記＋**峰位數字**（cm⁻¹），**不標 annotation 文字**。
- 300 dpi。不輸出互動 HTML。

---

## 10. 技術規格

- Python ≥ 3.10；套件：streamlit, pandas, numpy, scipy, plotly, matplotlib, pybaselines。
- 結構：`core/`（data_io / preprocess / peak_picking / matching / export，純函式、零 Streamlit 依賴）＋ `ui/`（每步驟一個 render 函式）＋ `app.py` ＋ `databases/`。
- 重算策略：毫秒級運算，每次 rerun 由參數即時重算；檔案解析以 `@st.cache_data` 快取。
- Session state 主要鍵：`step`、`spectrum`、`database`、`params_pre`、`params_peak`、`params_match`、`selections`（{峰編號: 選定名次 int 或 None＝不標註}）。
- Widget 防失憶：參數存自管 dict，widget 初始值由 dict 讀入、變動寫回。

---

## 11. 錯誤處理與邊界

- 光譜/資料庫格式不符 → 載入階段擋下，顯示具體缺漏（無手動欄位對應）。
- 0 峰 → 提示並阻擋進入 Step 4。
- 全部峰皆 Unassigned → 正常進行，輸出照產生。
- 範例資料規模（3351 點）下全流程即時運算無壓力。

---

## 12. 決議紀錄

已確認：僅 %T 無轉換｜無手動欄位對應｜重複波數取平均｜不需手動輸入 annotation 選項｜匯出僅 CSV + PNG（峰位標註）｜Step 5→4 為唯一警告點。

本輪定案：Step 5 採下拉單選，輸出 Annotation 2 自動附「排名最高且非所選」之候選作參考｜Δν 改為 Tolerance Scale 容差縮放係數（預設 1.0，乘上每筆 T_p、T_w）。

資料庫範本更新（v1.2.1）：內建範本改為 `Database_EMC.csv`（26 筆、多官能基、Big5 編碼、含 ≡ 符號）。欄位格式不變（中心值 ± 容差六欄），故 core 邏輯與計分公式不變。以範例光譜（預設參數）驗證：被標註峰由 2 增為 13，且兩錨點維持——1780→BMI C=O Symmetric（Ann2 = Anhydride C=O Asymmetric），1714→BMI C=O Asymmetric（Ann2 = Acrylate/Methacrylate C=O），後者重現原始 Output_example 的 BMI／Acrylate 情境。

→ 規格凍結，依此實作。
