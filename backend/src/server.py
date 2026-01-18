import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langserve import add_routes
from dotenv import load_dotenv

# 1. 強制載入環境變數（確保 API Key 能被讀取）
load_dotenv(override=True)

# 匯入專案模組
# 注意：確保你的目錄結構正確，且在根目錄下執行 python -m src.server
from src.agent import graph
from src.data_manager import (
    load_csv_file, 
    get_dataframe, 
    get_data_preview, 
    calculate_correlation
)

# =============================================================================
# 2. 初始化 FastAPI 應用
# =============================================================================
app = FastAPI(
    title="Data Agent Backend",
    version="1.0",
    description="DeepSeek Data Analysis Agent API with LangGraph"
)

# =============================================================================
# 3. 設定 CORS（解決 Figma 跨域的關鍵）
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    # ❌ 不要用 allow_origins=["*"]，因為我們需要 allow_credentials=True
    allow_origins=[], 
    
    # ✅ 使用正則動態匹配：
    # 1. Figma 動態沙盒網域 (https://...figma.site)
    # 2. 本地除錯（localhost, 127.0.0.1）
    allow_origin_regex=r"https://.*\.figma\.site|http://localhost.*|http://127\.0\.0\.1.*",
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 4. 掛載靜態檔案（用於圖片顯示）
# =============================================================================
# 確保目錄存在
static_dir = os.path.join(os.getcwd(), "static")
images_dir = os.path.join(static_dir, "images")
os.makedirs(images_dir, exist_ok=True)

# 掛載 /static 路徑
# 前端透過 http://localhost:8002/static/images/xxx.png 存取圖片
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# =============================================================================
# 5. 定義請求模型
# =============================================================================
class CorrelationRequest(BaseModel):
    col1: str
    col2: str

# =============================================================================
# 6. 核心接口定義
# =============================================================================

@app.get("/")
async def root():
    return {"status": "ok", "message": "Data Agent Backend 執行中"}

# --- 接口 A: 上傳 CSV ---
@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """
    前端上傳 CSV 檔案，後端儲存並載入到記憶體 DataFrame
    """
    if not file.filename.endswith(".csv"): # type: ignore
        raise HTTPException(status_code=400, detail="只支援 CSV 檔案")

    # 臨時儲存路徑
    temp_dir = "temp_data"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename) # pyright: ignore[reportArgumentType, reportCallIssue]

    try:
        # 寫入磁碟
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 呼叫 data_manager 載入資料
        success, message = load_csv_file(file_path)
        
        if success:
            # 取得預覽資料回傳給前端
            preview = get_data_preview()
            return JSONResponse(content={
                "status": "success",
                "message": message,
                "preview": preview,  # 前端表格資料來源
                "filename": file.filename
            })
        else:
            raise HTTPException(status_code=500, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 接口 B: 計算相關性 ---
@app.post("/calculate-correlation")
async def get_correlation(request: CorrelationRequest):
    """
    前端點擊兩個變數時呼叫此接口，快速回傳相關係數
    """
    # 呼叫 data_manager 中的純邏輯函式
    result = calculate_correlation(request.col1, request.col2)
    
    # 產生簡單的描述文案
    desc = "無相關性"
    try:
        corr_val = float(result)
        if abs(corr_val) > 0.8: desc = "極強相關"
        elif abs(corr_val) > 0.6: desc = "強相關"
        elif abs(corr_val) > 0.4: desc = "中等相關"
        elif abs(corr_val) > 0.2: desc = "弱相關"
    except:
        pass

    return {
        "status": "success",
        "correlation": result,
        "description": desc
    }

# --- 接口 C: Agent 對話 (LangServe) ---
# 自動掛載 /agent/invoke, /agent/stream 等接口
add_routes(
    app,
    graph,
    path="/agent",
)

# =============================================================================
# 7. 啟動入口
# =============================================================================
if __name__ == "__main__":
    print(">>> 啟動 Data Agent 後端服務...")
    print(">>> API 文件位置: http://localhost:8002/docs")
    print(">>> 圖片儲存路徑:", images_dir)
    
    # 啟動服務，埠號 8002
    uvicorn.run("src.server:app", host="0.0.0.0", port=8002, reload=True)