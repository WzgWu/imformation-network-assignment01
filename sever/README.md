# MiniGit 雲端伺服器 (Server / Cloud)

本模組為「資訊網路 第一次作業」之雲端伺服器端（Cloud Remote Repository），負責集中管理檔案物件（Blobs）、版本快照（Commits）與分支指標（Refs/HEAD）。

---

## 🚀 啟動方式

在命令提示字元（CMD）或 PowerShell 中進入本目錄：

```bash
cd sever
python server.py
```

### 自訂 IP 與 Port（跨電腦連線測試時使用）

```bash
python server.py --host 0.0.0.0 --port 8888
```

- `--host 0.0.0.0`：代表伺服器會監聽本機所有網路介面卡（包含 127.0.0.1 與區域網路實體 IP 如 `192.168.x.x`）。
- `--port 8888`：預設監聽連接埠。

---

## 📂 檔案目錄結構

- `server.py`：多執行緒 TCP Socket 伺服器主程式，支援同時多客戶端連線。
- `protocol.py`：自訂應用層通訊協定（MGC-Protocol）模組，實作長度前綴（Length-Prefixed Framing）。
- `cloud_storage/`（執行後自動生成）：
  - `repositories/<repo_name>/objects/`：儲存檔案內容快照（以 SHA-1 雜湊命名之 Blob）。
  - `repositories/<repo_name>/commits/`：儲存每次提交的 JSON 物件（作者、時間、變更清單）。
  - `repositories/<repo_name>/refs/heads/main`：記錄 main 分支最新提交 Hash（HEAD 指標）。

---

## 📡 伺服器即時日誌（Console Log）

伺服器運行時會以標準格式輸出網路互動日誌，便於 Demo 影片錄製與作業截圖：

- `[CONNECT]`：記錄客戶端 IP 與 Port（TCP 三向交握成功）。
- `[REQUEST]`：接收並解析客戶端指令（PING / PUSH / PULL / CLONE / STATUS）。
- `[STORAGE]`：解壓並儲存檔案物件與快照。
- `[CONFLICT]`：偵測到非 Fast-Forward 提交衝突並主動拒絕（回傳 409 Conflict）。
- `[DISCONNECT]`：連線正常關閉。
