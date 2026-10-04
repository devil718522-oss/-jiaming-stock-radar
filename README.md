# 家銘台股趨勢雷達 V1

## 功能
- FinMind 台股日K
- 5/10/20/60 日均線
- 20日均量與量比
- 0–100 趨勢評分
- 5MA 突破進場 / 10MA 跌破出場回測
- Streamlit Web 介面

## 執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

FinMind Token 可先留空；若遇 API 頻率限制，可申請 Token 後填入側欄。

## V1 限制
回測尚未計入手續費、交易稅、滑價、除權息調整及存活者偏誤。
下一版可加入全市場掃描、法人籌碼、基本面、參數最佳化與風控。
