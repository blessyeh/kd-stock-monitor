如果把 2330 台積電納入你前面正在做的「台股大盤決策系統」，我不建議把它當成一般個股，用 KD、MACD、法人買賣超各自判斷「買／賣」。

台積電更適合建立一個「基本面 × 預期 × 技術面 × 籌碼 × 大盤環境」的五層模型。

而且有一個很重要的觀念：台積電的股價通常不是等到財報公布才反應基本面，而是提前交易「未來獲利預期的變化」。因此法說會與月營收不能單獨使用，必須和股價反應結合。

以目前資料來看，台積電 2026 年 1～6 月累計營收為 2.404 兆元、年增 35.6%；6 月單月 4426.8 億元、年增 67.9%。7 月營收則預定於 8 月 10 日公布。

另外，台積電 2Q26 營收 1.270 兆元、年增 36%，EPS 27.25 元、年增 77.4%，毛利率 67.7%；公司對 3Q26 的營收指引為 446～458 億美元。

這正好可以拿來說明我建議你的模型怎麼做。

一、先把 2330 的投資模型分成五層

我會設計成：

                 2330 台積電
                      │
       ┌──────────────┼──────────────┐
       ↓              ↓              ↓
   基本面          市場預期          技術面
   30分            25分             20分
       │              │              │
       └──────────────┼──────────────┘
                      ↓
                 籌碼 / 資金
                    15分
                      ↓
                 大盤環境
                    10分
                      ↓
              TSMC Investment Score
                    0～100

最後不是直接輸出：

買 / 賣

而是：

80～100   強勢加碼區
65～80    偏多持有
50～65    中性持有
35～50    減碼 / 等待
0～35     防守

但這個分數不能現在就隨便指定權重；必須經過歷史回測校準。這點很重要。

二、第一層：基本面 Score

台積電最重要的基本面，我會抓 6 個東西。

① 月營收 YoY

不是只看：

本月營收年增多少？

而是：

Revenue YoY
Revenue 3M average YoY
Revenue acceleration

例如：

1月 +36.8%
2月 +22.2%
3月 +45.2%
4月 +17.5%
5月 +30.1%
6月 +67.9%

目前台積電營收呈現很強的年增，但月與月之間波動很大，因此不能只用單月 YoY 判斷趨勢。

我會建立：

Revenue Momentum

       本月YoY
          +
       3M平均YoY
          +
       3M加速度

例如：

Revenue YoY > 30%
且
3M Avg > 25%
且
3M Avg 正在上升

→ 基本面強勢。

反過來：

YoY > 30%
但
3M Avg ↓
且
連續2～3月下降

→ 營收仍然很好，但景氣動能正在惡化。

這兩種情況股價反應可能完全不同。

三、第二個非常重要：營收「是否超過市場預期」

這比 YoY 更重要。

假設：

市場預期：4000億
實際營收：4300億

這是利多。

但如果：

市場預期：4500億
實際營收：4300億

即使 YoY +40%，股價仍然可能跌。

所以你的程式不能只有：

revenue_yoy

最好加入：

revenue_actual
revenue_consensus
revenue_surprise

公式：

Revenue Surprise
=
(Actual - Consensus) / Consensus

例如：

+5% → Strong Beat
+2% → Beat
0~2% → Inline
-2% → Miss
<-2% → Strong Miss

這是我認為你目前系統非常值得增加的一個欄位。

四、法說會：不要只讀「利多／利空」

這可能是整個 2330 模型最重要的部分。

台積電每季法說會公布：

當季營收
毛利率
營業利益率
下一季營收指引
毛利率指引
資本支出
先進製程
AI/HPC需求
產能利用率
海外廠進度
技術節點
客戶需求

例如最新 2Q26：

2Q26 Actual
Revenue       $40.20B
Gross Margin  67.7%
Operating     60.3%

3Q26 公司指引：

Revenue       $44.6～45.8B
Gross Margin  65.0～67.0%
Operating     56.0～58.0%

因此你應該建立一個非常重要的：

Guidance Surprise

例如：

市場預期
      ↓
TSMC Guidance
      ↓
Actual

而不是只看 Actual。

五、法說會最重要的是「Guidance Direction」

我會特別做：

Next Quarter Revenue Guidance
QoQ
YoY
vs Previous Guidance
vs Street Consensus

例如：

上季指引：$39B～40.2B
本季指引：$44.6B～45.8B

這代表公司對下一季需求的展望明顯提高。

因此：

Guidance ↑
+
Consensus ↑
+
Gross Margin stable
+
Capex ↑

通常是很強的基本面組合。

反過來：

Revenue ↑
但
Guidance ↓
Margin ↓
Capex ↓

就要高度警戒。

六、毛利率其實是台積電非常重要的領先指標

我會把：

Revenue
EPS
Gross Margin

分開處理。

原因是：

營收成長 ≠ 獲利品質。

例如：

Revenue +30%
Gross Margin 68% → 63%

這和：

Revenue +30%
Gross Margin 68% → 69%

完全不同。

因此建立：

GM Momentum
=
Current GM - Previous GM

再加：

GM vs Guidance

如果：

Actual GM > Guidance

通常代表執行能力／產品組合／產能利用率優於預期。

七、第三層：技術分析不要只用 KD

這裡就可以直接接你前面的 KD 系統。

我會把 2330 技術面分成：

Trend
Momentum
Overbought/Oversold
Volume
Relative Strength
Trend

至少：

MA20
MA60
MA120
MA200

並判斷：

Price > MA20 > MA60 > MA120

這種是強勢多頭結構。

Momentum

加入：

MACD
RSI
KD
ROC

但不要讓四個指標各算一次。

因為：

KD、RSI、MACD 並不是三個完全獨立的訊號。

如果：

KD + RSI + MACD

同時看多，不能說：

三個指標都看多，所以信心三倍。

它們有高度相關性。

這是你的模型非常容易犯的「重複計分」。

八、2330 特別值得加入「相對強弱」

這是我認為你現在的系統很值得加入的東西。

不要只問：

台積電漲不漲？

而要問：

台積電是不是比大盤強？

建立：

TSMC / TAIEX

以及：

TSMC / SOX
TSMC / NDX

例如：

台積電 -2%
台股 -5%

其實台積電是相對強勢。

反過來：

台積電 -5%
台股 -2%

就是相對弱勢。

所以建立：

RS_TW
RS_SOX
RS_NDX

我會把這個列為 2330 專屬指標。

九、第四層：籌碼

2330 的籌碼建議不要只看「外資買賣超」。

至少：

Foreign Net Buy
Investment Trust
Dealer
Foreign Futures
Foreign Ownership %
Lending / Short Interest

其中我最重視：

外資買賣超 × 股價

例如：

股價 ↑
外資 ↑

→ 趨勢確認。

股價 ↑
外資 ↓

→ 背離。

股價 ↓
外資 ↓

→ 空方確認。

股價 ↓
外資 ↑

→ 有可能正在吸收賣壓。

但是仍然不能直接說：

外資買超 = 主力買進。

這是需要避免的過度解讀。

十、把「台積電 ADR」放進來

2330 是台灣上市股票，但 TSMC 在 NYSE 有 ADR。

所以你可以建立：

TSM ADR
+
USD/TWD

估算：

Implied 2330 price

概念上：

ADR price
÷ ADR conversion ratio
× USD/TWD

然後比較：

2330 actual
vs
ADR implied

形成：

ADR Premium / Discount

例如：

ADR implied = 2,300
2330 = 2,200

代表台股相對 ADR 折價。

反過來：

ADR implied = 2,200
2330 = 2,350

台股相對偏貴。

這對你原本的「台股盤前／盤後模型」非常有用。

十一、第五層：大盤環境

這是 2330 最容易被忽略的地方。

因為：

台積電不是獨立交易。

至少要加入：

TAIEX
SOX
NDX
US10Y
DXY
USD/TWD
VIX

尤其你前面建立的 Signal Confluence 可以直接當作：

Market Regime

例如：

情境 A
2330 基本面       +++
2330 技術面       +++
外資              ++
SOX               +++
TAIEX             +++

→ 可以積極。

情境 B
2330 基本面       +++
2330 技術面       -
SOX               --
外資              --
TAIEX             --

→ 不是基本面不好，而是估值／市場風險正在壓制股價。

這時候比較適合等待，而不是因為基本面好就一路加碼。

十二、最後形成「2330 Investment Score」

我會建議第一版先做成：

模組	分數
營收動能	15
法說／Guidance	20
毛利率／EPS	10
技術趨勢	15
Momentum	10
相對強弱	10
外資／籌碼	10
ADR / 匯率	5
大盤環境	5
合計	100

但我要強調：

這個權重只是初始模型，不應直接視為最佳權重。

後面應該利用歷史資料做：

2018～2026

每一天：
    計算 Score
    ↓
    觀察未來 5 / 20 / 60 日報酬
    ↓
    找最佳權重

這樣才是真正的量化模型。

十三、最重要：把投資策略分成「加碼」而不是「買賣」

對你這種比較適合中長期累積 2330 的策略，我反而不建議：

Score 75 → 買
Score 74 → 賣

這會過度交易。

比較好的方法是：

Score 80+
→ 核心持有 + 加碼

Score 65~80
→ 持有

Score 50~65
→ 不追價

Score 35~50
→ 減少新增資金

Score <35
→ 防守 / 等待

再加入：

Valuation

這一層我認為你一定要加。

因為：

好公司 ≠ 好價格。

例如台積電基本面 Score = 90。

如果：

Forward PE
處於歷史 90 percentile

那麼不能因為基本面 90 分就直接重壓。

應該變成：

Fundamental Score = 90
Valuation Score   = 40
Technical Score   = 75
Market Score      = 60

最後：

Investment Score = 65

這才比較接近真正的投資決策。

十四、我會特別建立「三種台積電買點」

這比單純技術指標更實用。

A. 基本面回撤買點
基本面 Score > 75
+
營收仍成長
+
Guidance 沒有下修
+
股價跌破 MA60
+
KD < 30
+
SOX 沒有結構性破壞

→ 基本面正常，但市場錯殺。

這是我最喜歡的買點。

B. 趨勢突破買點
Revenue ↑
Guidance ↑
Gross Margin ↑
+
Price > MA20 > MA60
+
Volume > 20D Avg
+
TSM ADR 強
+
Foreign buying

→ 基本面＋技術面同步確認。

這是「確認後追價」。

C. 恐慌反轉買點
基本面 Score > 70
+
VIX 高位回落
+
SOX 止跌
+
2330 跌深
+
KD Oversold
+
Foreign selling → buying
+
Futures short covering
+
USD/TWD stabilizing

→ 市場恐慌，但台積電基本面沒有同步惡化。

這個其實非常適合接你目前的 Signal Confluence。

你現在 B1～B3 已經有：

VIX 高位反轉
融資斷頭
匯率止穩
外資轉買
期貨空單回補

這些條件。

因此我會把 2330 當成「大盤恐慌訊號的主要觀察標的」，而不是另外再做一套完全獨立的系統。

十五、最終我會把 2330 做成這個架構
                 2330 TSMC
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
   FUNDAMENTAL    TECHNICAL     POSITIONING
       │             │             │
   Revenue         MA20/60       Foreign
   EPS             KD            TSM ADR
   GM              MACD          Futures
   Guidance        RSI           Short
   Capex           Volume
       │             │             │
       └─────────────┼─────────────┘
                     ↓
               MARKET REGIME
                     │
          TAIEX / SOX / NDX
          VIX / US10Y / DXY
          USD/TWD
                     ↓
              VALUATION
                     ↓
          ┌─────────────────┐
          │ 2330 Score 0~100│
          └────────┬────────┘
                   ↓
        ┌──────────┼──────────┐
        ↓          ↓          ↓
     加碼       持有       防守

而且這個模型有一個很大的優勢：

法說會是季度資料；營收是月資料；籌碼是日資料；技術指標是日／盤中資料；大盤風險甚至可以是小時資料。

因此你前面正在開發的系統，其實非常適合做成一個「多頻率決策模型」，而不是把所有資料硬塞在同一張表裡。

目前 2026 年台積電的基本面本身仍然很強：上半年營收年增 35.6%，2Q EPS 年增 77.4%，3Q26 公司營收指引又明顯高於 2Q26。 所以現在最值得研究的問題已經不是「台積電基本面好不好」，而是「市場目前給這個基本面多少價格，以及股價是否已經提前反映未來成長」。

這也是為什麼我會把「估值＋市場預期差」放進 2330 模型；單純把 KD、MACD、營收、外資加總，仍然不足以形成真正可靠的投資策略。

如果把這套模型實作進你目前的程式，我建議下一步直接新增一個 tsmc_analyzer.py，輸出 「2330 基本面分數、技術分數、籌碼分數、ADR 分數、大盤環境分數、估值分數、總分，以及目前屬於哪一種買點」。這會比繼續擴充現有的 KD Calculator 更有實際價值