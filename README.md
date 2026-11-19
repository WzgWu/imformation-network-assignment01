# 資訊網路 第一次作業：MiniGit 版本控制與檔案同步系統

本專案依據作業規範第一頁**第 6 項主題「檔案與資料服務」**開發，參考 **GitHub / Git** 系統架構，使用 **Python 原生 Socket** 實現輕量級版本控制與檔案同步系統。

- **`client/` (Local 本機端)**：包含本機工作目錄（Working Directory）、暫存區（Staging Index）、本地版本庫（`.minigit`）與 CLI 指令。
- **`sever/` (Cloud 雲端伺服器)**：提供多執行緒 TCP 服務，集中託管檔案快照物件（Blobs）、版本紀錄（Commits）與分支指標（HEAD）。

---

## 📁 資料夾目錄結構

```text
資訊網路assignment1/
├── client/                     # 本機客戶端 (Local)
│   ├── client.py               # 本地 Git CLI 工具 (init, add, commit, push, pull 等)
│   ├── protocol.py             # 應用層通訊協定封裝模組 (長度前綴、JSON Header)
│   └── README.md               # 客戶端操作指令說明
│
├── sever/                      # 雲端伺服器端 (Cloud)
│   ├── server.py               # 多執行緒 TCP Socket 伺服器
│   ├── protocol.py             # 應用層通訊協定封裝模組
│   ├── cloud_storage/          # 雲端集中式儲存庫 (程式執行後自動生成)
│   └── README.md               # 伺服器啟動與設定指南
│
├── demo_test.py                # 自動化端到端測試腳本 (涵蓋正常流程與異常處理)
├── 專題企畫書_提案計畫書範本.md    # 完整的 10 頁內提案計畫書內容 (包含 IEEE 參考文獻與影片腳本)
└── README.md                   # 專案總覽 (本檔案)
```

---

## ⚡ 快速執行與驗證

### 1. 一鍵自動化測試（推薦）
在主目錄下執行以下指令，系統會自動啟動 Server、執行 Client 各項操作、模擬版本衝突與斷線異常，並產出完整測試紀錄：

```bash
python demo_test.py
```

### 2. 手動互動操作

#### 步驟 1：啟動雲端伺服器 (Cloud)
打開第一個終端機視窗：
```bash
cd sever
python server.py
```
*(伺服器會在 0.0.0.0:8888 啟動，並自動顯示本機與實體區網 IP，如 `192.168.x.x`)*

#### 步驟 2：執行本機操作 (Local)
打開第二個終端機視窗：
```bash
cd client

# 1. 初始化本地儲存庫
python client.py init

# 2. 測試網路連線與 RTT
python client.py ping

# 3. 建立測試檔案
echo "Hello Networks!" > test.txt

# 4. 暫存與提交
python client.py add test.txt
python client.py status
python client.py commit -m "Initial commit: 加入測試檔案"
python client.py log

# 5. 操作一：推送到雲端 (Push)
python client.py push

# 6. 查看雲端伺服器狀態
python client.py remote-status
```

#### 步驟 3：跨主機（兩台電腦）連線測試
若要在兩台不同電腦上進行連線（可獲得作業滿分 10 分）：
1. 在主機 A 啟動 `sever/server.py`。
2. 將 `client/` 資料夾複製到主機 B。
3. 在主機 B 執行設定指令指向主機 A 的 IP：
   ```bash
   python client.py config --host <主機A的IP> --port 8888
   python client.py ping
   python client.py push
   ```

---

## 🏆 作業評分標準對照清單

| 評分項目 | 配分 | 本專案實作與佐證 |
| :--- | :---: | :--- |
| **基本繳交與系統介紹** | 60% | 專題企畫書已完整撰寫於 `專題企畫書_提案計畫書範本.md`，清楚闡述系統用途、使用情境、以及 Local/Cloud 角色分工。 |
| **課堂知識應用與連線說明** | 20% | 1. 採用 TCP 串流通訊（`SOCK_STREAM`），解釋三向交握連線過程。<br>2. 綁定 `0.0.0.0:8888`，解釋 IP 與 Port 意義。<br>3. 設計長度前綴（4-byte Big-Endian Prefix）自訂協定，徹底解決 TCP 串流黏包與拆包問題。 |
| **兩台主機連線與資料交換** | 10% | 程式完全原生解耦，可直接將 `client` 複製至另一台電腦，透過 `config --host` 跨電腦連線，Server 即時輸出對端 IP 與通訊日誌。 |
| **兩項操作與實際結果** | 10% | 實作多於兩種核心操作：`Push`（上傳快照）、`Pull`（差異同步下載）、`Clone`（全庫複製）、`Remote-Status`（雲端查詢）。 |
| **異常情況處理 (加分)** | 5% | 1. 連線拒絕（伺服器未開啟友善提示與排除指南）<br>2. 409 Conflict（多協作者非快進推動衝突阻擋）<br>3. 空暫存區防護（Nothing to commit 檢查）<br>4. 檔案不存在警示。 |
| **Final Project 發想 (加分)** | 5% | 計畫書內詳細規劃延伸方向：Branching、3-Way Merge、Web 前端可視化儀表板與 TLS 安全加密通道。 |
