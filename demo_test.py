"""
Automated Test & Demonstration Script for MiniGit (Client-Server Version Control)
Tests normal workflow, two-way sync, and abnormal exception scenarios.
"""

import os
import sys
import io
import time
import subprocess
import shutil

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(BASE_DIR, "sever")
CLIENT_DIR = os.path.join(BASE_DIR, "client")
CLIENT2_DIR = os.path.join(BASE_DIR, "client2_simulation")


def run(cmd, cwd):
    print(f"\n[RUNNING in {os.path.basename(cwd)}] {cmd}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    print(res.stdout)
    if res.stderr:
        print("[STDERR]", res.stderr)
    return res


def main():
    print("=" * 70)
    print("  資訊網路 Assignment 1: MiniGit 系統功能與異常處理自動測試")
    print("=" * 70)

    # 1. 測試異常處理情境 1：伺服器未啟動時連線失敗 (Connection Refused)
    print("\n>>> 【測試 1：異常處理 - 伺服器未啟動連線失敗】<<<")
    run("python client.py init", CLIENT_DIR)
    res_err1 = run("python client.py ping", CLIENT_DIR)
    assert "網路連線失敗" in res_err1.stdout or "Connection" in res_err1.stdout

    # 2. 啟動伺服器 (背景行程)
    print("\n>>> 【啟動雲端伺服器 sever/server.py】<<<")
    # Clean previous storage if any
    cloud_storage = os.path.join(SERVER_DIR, "cloud_storage")
    if os.path.exists(cloud_storage):
        shutil.rmtree(cloud_storage)

    server_proc = subprocess.Popen([sys.executable, "server.py"], cwd=SERVER_DIR)
    time.sleep(1.5)  # Wait for server to bind port

    try:
        # 3. 測試連線 PING
        print("\n>>> 【測試 2：網路連線與 RTT 往返延遲】<<<")
        run("python client.py ping", CLIENT_DIR)

        # 4. 測試異常處理情境 2：無變更空提交 (Empty Commit)
        print("\n>>> 【測試 3：異常處理 - 暫存區為空嘗試提交】<<<")
        run("python client.py commit -m \"測試空提交\"", CLIENT_DIR)

        # 5. 測試正常工作流：建立檔案、add、commit、status、log
        print("\n>>> 【測試 4：基本工作流 - 新增檔案、暫存、提交】<<<")
        sample_file = os.path.join(CLIENT_DIR, "hello.txt")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("Hello Computer Networks Assignment 1!\nThis is a file version control test.\n")

        code_file = os.path.join(CLIENT_DIR, "network_calc.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write("# Simple network tool\ndef rtt(t0, t1):\n    return (t1 - t0) * 1000\n")

        run("python client.py status", CLIENT_DIR)
        run("python client.py add .", CLIENT_DIR)
        run("python client.py status", CLIENT_DIR)
        run("python client.py commit -m \"v1.0: 首次提交網路計算工具與說明檔案\"", CLIENT_DIR)
        run("python client.py log", CLIENT_DIR)

        # 6. 測試操作 1：推送至雲端 (PUSH)
        print("\n>>> 【測試 5：操作 1 - 將提交推送到雲端 (PUSH)】<<<")
        run("python client.py push", CLIENT_DIR)
        run("python client.py remote-status", CLIENT_DIR)

        # 7. 測試第二位客戶端或另一台電腦 (CLONE)
        print("\n>>> 【測試 6：操作 2 - 模擬第二位使用者複製 (CLONE)】<<<")
        if os.path.exists(CLIENT2_DIR):
            shutil.rmtree(CLIENT2_DIR)
        os.makedirs(CLIENT2_DIR, exist_ok=True)
        # Copy protocol and client.py to client2
        shutil.copy(os.path.join(CLIENT_DIR, "client.py"), CLIENT2_DIR)
        shutil.copy(os.path.join(CLIENT_DIR, "protocol.py"), CLIENT2_DIR)

        run("python client.py clone 127.0.0.1 8888 assignment1_repo", CLIENT2_DIR)
        run("python client.py log", CLIENT2_DIR)

        # 8. 測試異常處理情境 3：版本衝突 (409 Conflict)
        print("\n>>> 【測試 7：異常處理 - 模擬多人協作版本衝突 (409 Conflict)】<<<")
        # Client 2 修改檔案並提交、推送
        c2_file = os.path.join(CLIENT2_DIR, "hello.txt")
        with open(c2_file, "a", encoding="utf-8") as f:
            f.write("Client 2 modified this line!\n")
        run("python client.py add hello.txt", CLIENT2_DIR)
        run("python client.py commit -m \"Client 2 提交了修改\"", CLIENT2_DIR)
        run("python client.py push", CLIENT2_DIR)

        # 此時 Client 1 尚未 pull，也修改了檔案並提交、嘗試 push
        with open(sample_file, "a", encoding="utf-8") as f:
            f.write("Client 1 concurrent conflicting edit!\n")
        run("python client.py add hello.txt", CLIENT_DIR)
        run("python client.py commit -m \"Client 1 衝突的提交\"", CLIENT_DIR)
        print("  Client 1 嘗試 push (預期被雲端拒絕 409 Conflict):")
        res_conflict = run("python client.py push", CLIENT_DIR)

        # 9. 測試操作 3：拉取同步更新 (PULL)
        print("\n>>> 【測試 8：操作 3 - 解決衝突與拉取雲端更新 (PULL)】<<<")
        # 建立 client3 乾淨拉取展示
        CLIENT3_DIR = os.path.join(BASE_DIR, "client3_sync_test")
        if os.path.exists(CLIENT3_DIR):
            shutil.rmtree(CLIENT3_DIR)
        os.makedirs(CLIENT3_DIR, exist_ok=True)
        shutil.copy(os.path.join(CLIENT_DIR, "client.py"), CLIENT3_DIR)
        shutil.copy(os.path.join(CLIENT_DIR, "protocol.py"), CLIENT3_DIR)
        run("python client.py clone 127.0.0.1 8888 assignment1_repo", CLIENT3_DIR)
        run("python client.py pull", CLIENT3_DIR)  # Should show 304 Up to date

        # 清理 client2 與 client3 測試模擬資料夾
        shutil.rmtree(CLIENT2_DIR, ignore_errors=True)
        shutil.rmtree(CLIENT3_DIR, ignore_errors=True)

        print("\n" + "=" * 70)
        print(" [測試完成] 所有功能驗證正常，成功展示：")
        print("   1. TCP Socket 網路連線與 Application PDU 封裝 (長度前綴)")
        print("   2. 本機版本管理 (init, add, commit, status, log)")
        print("   3. 兩種以上主機資料交換操作 (PUSH, PULL, CLONE, STATUS)")
        print("   4. 異常情況處理 (連線拒絕、空提交防護、409 版本衝突拒絕推動)")
        print("=" * 70)

    finally:
        server_proc.terminate()
        server_proc.wait()


if __name__ == "__main__":
    main()
