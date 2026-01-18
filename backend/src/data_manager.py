import pandas as pd
import numpy as np
import io
import os  # 需要導入 os 來獲取檔案名

# 全域變數存儲
GLOBAL_DF = None
GLOBAL_FILENAME = "未命名資料集" # [新增] 存儲檔案名

def _preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    [內部函式] 資料預處理流程：
    1. 去除全空行列
    2. 智慧型型別推斷 (object -> numeric)
    3. 缺失值填補
    """
    # 1. 基礎清理：去除全空的行和列
    df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
    
    # 2. 智慧型型別轉換
    # 嘗試將 object 型別的欄位轉換為數值，無法轉換的變成 NaN
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                # 嘗試轉數字，coerce 模式下無法轉換的變為 NaN
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                
                # 如果轉換後的非空值比例超過 50%，我們認為這欄應該是數字欄 (例如: "10", "20", "N/A")
                if numeric_series.notna().sum() > 0.5 * len(df):
                    df[col] = numeric_series
            except Exception:
                pass

    # 3. 缺失值處理 (簡單粗暴策略，適合展示)
    # 數值欄：用平均值填補
    # 類別欄：用 "Unknown" 填補
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].mean())
        else:
            df[col] = df[col].fillna("Unknown").astype(str)

    return df

def load_csv_file(file_path: str):
    """載入並清洗 CSV 檔案"""
    global GLOBAL_DF, GLOBAL_FILENAME # [修改] 引用全域檔案名
    try:
        # [新增] 提取並保存檔案名 (不包含完整路徑，只存檔案名，保護隱私且夠用)
        GLOBAL_FILENAME = os.path.basename(file_path)
        
        raw_df = pd.read_csv(file_path)
        clean_df = _preprocess_data(raw_df)
        GLOBAL_DF = clean_df
        
        rows, cols = GLOBAL_DF.shape
        numeric_cols = list(GLOBAL_DF.select_dtypes(include=[np.number]).columns)
        
        return True, (f"成功載入檔案【{GLOBAL_FILENAME}】！\n"
                      f"包含 {rows} 行，{cols} 列。")
    except Exception as e:
        return False, f"資料載入失敗: {str(e)}"

def get_dataframe():
    """取得當前 DataFrame"""
    return GLOBAL_DF

def get_data_preview(n=10):
    """取得前 N 行資料 (處理 NaN 為 None 以便 JSON 序列化)"""
    if GLOBAL_DF is not None:
        # replace({np.nan: None}) 是為了防止前端 JSON 解析報錯
        return GLOBAL_DF.head(n).replace({np.nan: None}).to_dict(orient='records')
    return []

def get_data_info():
    """取得資料摘要 (Schema)"""
    if GLOBAL_DF is not None:
        buffer = io.StringIO()
        GLOBAL_DF.info(buf=buffer)
        
        # [修改] 在回傳的資訊頭部拼接檔案名
        info_str = f"資料來源檔案: {GLOBAL_FILENAME}\n" 
        info_str += "-" * 30 + "\n"
        info_str += buffer.getvalue()
        
        return info_str
    return "暫無資料"

def calculate_correlation(col1: str, col2: str):
    """
    [增強版] 計算相關性
    支援：數值 vs 數值 (Pearson), 類別 vs 數值 (Label Encoding), 類別 vs 類別
    """
    if GLOBAL_DF is None:
        return 0.0

    if col1 not in GLOBAL_DF.columns or col2 not in GLOBAL_DF.columns:
        return 0.0

    try:
        s1 = GLOBAL_DF[col1]
        s2 = GLOBAL_DF[col2]

        # 輔助函式：將序列轉為數值
        def to_numeric_force(series):
            if pd.api.types.is_numeric_dtype(series):
                return series
            else:
                # 如果是字串/類別，使用 factorize 編碼 (0, 1, 2...)
                codes, uniques = pd.factorize(series)
                return pd.Series(codes)

        # 強制轉換為數值序列
        v1 = to_numeric_force(s1)
        v2 = to_numeric_force(s2)

        # 計算 Pearson 相關係數
        corr = v1.corr(v2)
        
        # 處理計算結果為 NaN 的情況 (例如標準差為0)
        if pd.isna(corr):
            return 0.0
            
        return round(corr, 4)

    except Exception as e:
        print(f"相關性計算出錯: {e}")
        return 0.0