import os
from langchain_deepseek import ChatDeepSeek
# [關鍵] 使用 LangChain 1.1 標準 API 和 中介軟體工具
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt

# 匯入工具與資料管理器
from src.tools import python_inter, fig_inter
from src.data_manager import get_data_info

# =============================================================================
# 1. 初始化模型
# =============================================================================
model = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0,
    api_key=os.getenv("DEEPSEEK_API_KEY"), # type: ignore
    api_base="https://api.deepseek.com"
)

tools = [python_inter, fig_inter]

# =============================================================================
# 2. 定義動態 System Prompt 中介軟體
# =============================================================================

@dynamic_prompt
def dataset_context_middleware(request) -> str:
    """
    [中介軟體] 動態提示詞產生器
    LangChain 會在每次呼叫 Agent 之前自動執行這個函式。
    
    request: 包含了當前的 ModelRequest (如 input, messages 等)
    回傳：最新的 System Prompt 字串
    """
    
    # 1. 即時從記憶體取得最新的資料摘要（包含檔案名稱、行列數、欄位名稱等）
    # 只要使用者上傳新檔案，get_data_info() 的回傳結果就會立即變化
    data_context = get_data_info()
    
    # 2. 回傳完整的 System Prompt
    return f"""你是一名精通 Python 的資料分析專家 DataAgent。

        【目前資料集即時狀態】
        {data_context}

        【你的職責】
        1. 使用 `python_inter` 執行 Pandas 分析，或 `fig_inter` 進行繪圖。
        2. 變數 `df` 已內建，可直接使用。
        3. 繪圖時請將物件賦值給變數，並呼叫繪圖工具。
        4. 遇到問題請先嘗試分析錯誤訊息。
        """

# =============================================================================
# 3. 建立 Agent (帶中介軟體)
# =============================================================================

# 使用 LangChain 1.1 的 create_agent
# 注意：我們不再直接傳 system_prompt="..." 字串，
# 而是透過 middleware 參數傳入動態產生器。
graph = create_agent(
    model=model,
    tools=tools,
    middleware=[dataset_context_middleware], # 注入中介軟體
)