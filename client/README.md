# MiniGit 客戶端 (Client / Local)

本模組為「資訊網路 第一次作業」之本機客戶端（Local Working Directory & Local Repository），模擬 GitHub / Git 本地工作流程（工作目錄、暫存區、本機庫），並透過 TCP Socket 與雲端伺服器進行雙向資料交換。

---

## 🛠️ 指令操作手冊

請在 `client` 資料夾下開啟終端機（CMD / PowerShell）：

### 1. 初始化本機儲存庫 (Init)
```bash
python client.py init
```
會在當前目錄建立 `.minigit/`，包含 `objects/`, `commits/`, `index.json`, `config.json`, `HEAD`。

### 2. 設定或切換伺服器 IP (Config / 跨電腦測試)
```bash
# 查看目前配置
python client.py config

# 修改為遠端伺服器 IP（展示兩台主機連線時使用）
python client.py config --host 192.168.1.100 --port 8888 --author "B11309000_王小明"
```

### 3. 測試連線與延遲 (Ping)
```bash
python client.py ping
```
向伺服器發送 PING 探針，並計算 TCP 往返延遲（Round-Trip Time, RTT）。

### 4. 查看本機工作目錄與暫存狀態 (Status)
```bash
python client.py status
```
顯示目前分支、HEAD 提交、已暫存變更（綠色）、未暫存變更（紅色）及未追蹤檔案。

### 5. 檔案加入暫存區 (Add)
```bash
# 暫存單一檔案
python client.py add test.txt

# 暫存當前目錄所有變更
python client.py add .
```

### 6. 提交版本快照 (Commit)
```bash
python client.py commit -m "你的提交說明訊息"
```
（若暫存區為空，系統會進行異常防護並提示 "無變更可提交"）

### 7. 查看提交歷史紀錄 (Log)
```bash
python client.py log
```
從最新提交開始逐層向上回溯輸出歷史版本。

### 8. 推送至雲端伺服器 (Push - 操作一)
```bash
python client.py push
```
將本機新增的提交與檔案物件打包壓縮，透過 TCP Socket 上傳至 Server。若遠端版本較新，將會觸發 409 Conflict 衝突警告。

### 9. 從雲端伺服器拉取並同步 (Pull - 操作二)
```bash
python client.py pull
```
比對雲端最新 HEAD，下載缺失的檔案物件並更新本機工作目錄檔案。

### 10. 查詢雲端儲存庫狀態 (Remote-Status)
```bash
python client.py remote-status
```
直接向伺服器查詢遠端最新 HEAD Hash 與雲端總提交數。

### 11. 複製遠端倉庫 (Clone)
在一個全新或空目錄執行：
```bash
python client.py clone <Server_IP> <Port> <Repo_Name>
# 範例：
python client.py clone 127.0.0.1 8888 assignment1_repo
```
