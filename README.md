# DeepSeek Data Agent

<p align="center">
  <b>Demo 影片展示</b><br>
  <video src="demo.mp4" controls width="600" style="max-width:100%"></video>
</p>

一個基於 FastAPI 與 LangChain 1.0 的互動式資料分析後端，結合前端 React/Vite，支援 CSV 上傳、資料摘要、相關性分析、Python 程式碼與繪圖執行，並可與 DeepSeek 3.2 AI 進行自然語言互動。

## 主要功能

- **CSV 上傳與預覽**：前端可直接上傳 CSV 檔案，後端自動清洗、預處理並提供資料預覽。
- **資料摘要**：即時取得目前資料集的摘要資訊（欄位、型別、行列數等）。
- **相關性分析**：支援數值/類別欄位間的相關性計算，回傳易懂的描述。
- **Python 程式碼執行**：可直接執行 Pandas/Numpy 程式碼，回傳執行結果與列印輸出。
- **繪圖支援**：支援 Matplotlib/Seaborn 程式碼執行，圖片自動儲存並可於前端顯示。
- **AI 對話分析**：整合 DeepSeek Chat，透過自然語言指令進行資料探索與分析。

## 專案結構

```
backend/
  src/
    agent.py           # AI Agent 與中介軟體
    data_manager.py    # 資料管理與預處理
    server.py          # FastAPI 主程式
    tools.py           # Python/繪圖執行工具
  static/images/       # 產生的圖片儲存路徑
  temp_data/           # 上傳的暫存資料
frontend/
  src/
    App.tsx            # 前端主程式
    components/        # React 元件
    ...
```

## 快速開始

### 1. 後端建構與啟動

```sh
cd backend
pip install -r requirements.txt
python -m src.server
```

- 預設埠號：`8002`
- API 文件：http://localhost:8002/docs

### 2. 前端建構與啟動

```sh
cd frontend
npm install
npm run dev
```

- 預設埠號：`5173`

### 3. 使用方式

1. 於前端上傳 CSV 檔案，預覽資料。
2. 點擊欄位可查詢相關性。
3. 於 AI 對話框輸入自然語言指令（如「請畫出年齡分布圖」），自動執行 Python 程式碼並顯示結果。

## 主要技術

- FastAPI、Pydantic、Uvicorn
- Pandas、Numpy、Matplotlib、Seaborn
- LangChain、DeepSeek Chat
- React、Vite

## 其他資訊

- 圖片會儲存於 `/static/images/`，前端可直接存取。
- 支援多種資料型別自動推斷與缺失值處理。

## 後端 API 端點說明

| 方法 | 路徑                  | 說明                     | 主要參數/格式 |
|------|----------------------|--------------------------|--------------|
| POST | `/upload`            | 上傳 CSV 檔案            | multipart/form-data，欄位名 `file` |
| GET  | `/data-preview`      | 取得已上傳資料的前 N 行預覽 | 無           |
| POST | `/agent/stream`      | AI 對話（流式回應）        | JSON，需傳入訊息歷史（詳見 BACKEND_INTEGRATION.md） |
| GET  | `/docs`              | Swagger API 文件          | 無           |



---

如需進階設定、原理圖或秘訣，請參考各子目錄內的指南文件。