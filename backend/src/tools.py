import os
import io
import contextlib
import platform
import matplotlib
# 【關鍵】永久設定非互動後端，避免伺服器錯誤
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from src.data_manager import get_dataframe

load_dotenv()

# --- 解決中文亂碼 ---
def configure_fonts():
    system_name = platform.system()
    if system_name == 'Windows':
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
        plt.rcParams['font.family'] = 'Microsoft YaHei'  # 強制指定
    elif system_name == 'Darwin':
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC']
        plt.rcParams['font.family'] = 'Arial Unicode MS'
    else:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'DejaVu Sans']
        plt.rcParams['font.family'] = 'WenQuanYi Micro Hei'
    plt.rcParams['axes.unicode_minus'] = False
configure_fonts()

# -----------------------------------------------------------------------------
# 工具 1：Python 計算（回歸你的單一作用域邏輯，但增加 stdout 捕獲）
# -----------------------------------------------------------------------------
class PythonCodeInput(BaseModel):
    py_code: str = Field(description="Python 程式碼。可使用變數 df。")

@tool(args_schema=PythonCodeInput)
def python_inter(py_code: str):
    """
    執行 Python 程式碼。
    """
    df = get_dataframe()
    if df is None:
        return "錯誤：目前沒有載入任何資料。"

    # 【回歸原始邏輯】：只使用一個 env 字典，同時作為 globals 與 locals
    # 這樣列表生成式就不會出錯了
    env = {
        "df": df, 
        "pd": pd, 
        "np": np, 
        "result": None
    }
    
    output_buffer = io.StringIO()
    
    try:
        # 使用 contextlib 捕獲 print() 的內容
        with contextlib.redirect_stdout(output_buffer):
            # [關鍵] 只傳一個字典！
            exec(py_code, env)
            
        # 1. 優先取得 stdout（print 的內容）
        stdout_content = output_buffer.getvalue().strip()
        
        # 2. 其次取得 result 變數（如果使用者寫了 result=...）
        result_content = ""
        if "result" in env and env["result"] is not None:
            result_content = str(env["result"])

        # 3. 實在不行，嘗試 eval 最後一行 (模仿你原始程式碼的邏輯)
        # 這是一個保底策略，讓 '2+2' 這種能直接回傳 4
        eval_result = ""
        if not stdout_content and not result_content:
            try:
                # 嘗試計算最後一行運算式
                last_line = py_code.strip().split('\n')[-1]
                # 只有最後一行看起來像運算式時才 eval
                if not last_line.startswith('print') and '=' not in last_line:
                    eval_result = str(eval(last_line, env))
            except:
                pass

        # 組合輸出
        final_output = []
        if stdout_content: final_output.append(f"【列印輸出】\n{stdout_content}")
        if result_content: final_output.append(f"【計算結果】\n{result_content}")
        if eval_result: final_output.append(f"【運算式值】\n{eval_result}")
        
        if not final_output:
            return "程式碼執行成功，但沒有輸出。請使用 print() 列印結果。"
            
        return "\n\n".join(final_output)

    except Exception as e:
        return f"程式碼執行報錯: {e}"

# -----------------------------------------------------------------------------
# 工具 2：繪圖（回歸簡單邏輯，保留路徑設定）
# -----------------------------------------------------------------------------
class FigCodeInput(BaseModel):
    py_code: str = Field(description="繪圖程式碼。需產生 fig 物件。")
    fname: str = Field(description="圖像變數名稱，例如 'fig'。")

@tool(args_schema=FigCodeInput)
def fig_inter(py_code: str, fname: str) -> str:
    """
    執行繪圖程式碼並保存。
    """
    df = get_dataframe()
    if df is None: return "錯誤：無資料。"
    
    print(f">>> 開始繪圖: {fname}")
    
    # 清理畫布
    plt.clf()
    plt.close('all')

    # 【回歸原始邏輯】：單一字典作用域
    env = {
        "df": df, 
        "pd": pd, 
        "plt": plt, 
        "sns": sns
    }
    
    # 路徑設定（保留這部分，因為必須存到 static 目錄前端才能讀取）
    # 確保這個路徑與 server.py 掛載的路徑一致
    save_dir = os.path.join(os.getcwd(), "static", "images")
    os.makedirs(save_dir, exist_ok=True)

    try:
        # [關鍵] 只傳一個字典！
        exec(py_code, env)
        
        fig = env.get(fname)
        # 容錯：如果使用者沒賦值給 fname，嘗試取得目前 fig
        if not fig:
            fig = plt.gcf()
            
        if fig:
            # 檔案名稱處理
            file_name = f"{fname}.png"
            abs_path = os.path.join(save_dir, file_name)
            
            # 保存
            fig.savefig(abs_path, bbox_inches='tight', dpi=100)
            print(f">>> 圖片儲存成功: {abs_path}")
            
            # 回傳前端標記
            return f"IMAGE_GENERATED: {file_name}"
        else:
            return "繪圖程式碼執行完畢，但未找到圖像物件。"
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"繪圖報錯: {e}"
    finally:
        plt.close('all')