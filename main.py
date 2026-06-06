"""
main.py - 程式入口點

這是整個 MotoGP 新聞爬蟲程式的啟動入口。
執行方式：python main.py --limit 10

流程：
1. 從 motogp_scraper.cli 匯入 main 函數
2. 執行 main() 並將回傳值作為程式結束碼
   （回傳 0 代表成功，非 0 代表有錯誤）
"""

# 匯入命令行介面的主函數
from motogp_scraper.cli import main


if __name__ == "__main__":
    # SystemExit 會將 main() 的回傳值作為程式的結束碼
    raise SystemExit(main())
