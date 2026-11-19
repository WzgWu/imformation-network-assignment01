"""
MiniGit Cloud Server (Cloud / Remote Repository Server)
Course: Computer Networks Assignment 1 - Topic 6: File and Data Services (Version Control System)
Architecture: Centralized Cloud Repository hosting Git objects, commits, and branch references over TCP Sockets.
"""

import os
import sys
import io
import json
import socket
import threading
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure UTF-8 output and real-time line flushing on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

# Import custom application layer protocol
from protocol import send_message, recv_message, pack_blobs_to_zip, unpack_blobs_from_zip, DEFAULT_PORT


class MiniGitServer:
    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT, storage_dir: str = "cloud_storage"):
        self.host = host
        self.port = port
        self.base_dir = os.path.abspath(storage_dir)
        self.repos_dir = os.path.join(self.base_dir, "repositories")
        os.makedirs(self.repos_dir, exist_ok=True)
        self.server_socket: Optional[socket.socket] = None
        self.is_running = False

    def log(self, tag: str, message: str, client_addr: Optional[tuple] = None):
        """Standardized console logging for demo and assignment submission records."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        client_info = f" [{client_addr[0]}:{client_addr[1]}]" if client_addr else ""
        print(f"[{now}] [{tag:^10}]{client_info} {message}", flush=True)

    # ==================== Repository Storage Helpers ====================

    def _get_repo_path(self, repo_name: str) -> str:
        return os.path.join(self.repos_dir, repo_name)

    def _ensure_repo(self, repo_name: str) -> str:
        repo_path = self._get_repo_path(repo_name)
        os.makedirs(os.path.join(repo_path, "objects"), exist_ok=True)
        os.makedirs(os.path.join(repo_path, "commits"), exist_ok=True)
        os.makedirs(os.path.join(repo_path, "refs", "heads"), exist_ok=True)
        return repo_path

    def _get_branch_head(self, repo_name: str, branch: str = "main") -> str:
        head_file = os.path.join(self._get_repo_path(repo_name), "refs", "heads", branch)
        if os.path.exists(head_file):
            with open(head_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def _set_branch_head(self, repo_name: str, branch: str, commit_hash: str):
        head_file = os.path.join(self._get_repo_path(repo_name), "refs", "heads", branch)
        os.makedirs(os.path.dirname(head_file), exist_ok=True)
        with open(head_file, "w", encoding="utf-8") as f:
            f.write(commit_hash.strip())

    def _save_blob(self, repo_name: str, blob_hash: str, data: bytes):
        obj_path = os.path.join(self._get_repo_path(repo_name), "objects", blob_hash)
        if not os.path.exists(obj_path):
            with open(obj_path, "wb") as f:
                f.write(data)

    def _get_blob(self, repo_name: str, blob_hash: str) -> Optional[bytes]:
        obj_path = os.path.join(self._get_repo_path(repo_name), "objects", blob_hash)
        if os.path.exists(obj_path):
            with open(obj_path, "rb") as f:
                return f.read()
        return None

    def _save_commit(self, repo_name: str, commit_dict: Dict[str, Any]):
        commit_hash = commit_dict["hash"]
        commit_path = os.path.join(self._get_repo_path(repo_name), "commits", f"{commit_hash}.json")
        with open(commit_path, "w", encoding="utf-8") as f:
            json.dump(commit_dict, f, ensure_ascii=False, indent=2)

    def _get_commit(self, repo_name: str, commit_hash: str) -> Optional[Dict[str, Any]]:
        commit_path = os.path.join(self._get_repo_path(repo_name), "commits", f"{commit_hash}.json")
        if os.path.exists(commit_path):
            with open(commit_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _get_commit_history(self, repo_name: str, start_hash: str) -> List[Dict[str, Any]]:
        """Traverse commit chain backwards from start_hash."""
        history = []
        curr = start_hash
        visited = set()
        while curr and curr not in visited:
            visited.add(curr)
            c = self._get_commit(repo_name, curr)
            if not c:
                break
            history.append(c)
            curr = c.get("parent")
        return history

    # ==================== Request Handlers ====================

    def handle_ping(self, conn: socket.socket, addr: tuple, header: Dict[str, Any]):
        self.log("PING", "收到心跳檢測 (PING)，回應 PONG", addr)
        send_message(conn, {"status": "OK", "code": 200, "message": "PONG"})

    def handle_status(self, conn: socket.socket, addr: tuple, header: Dict[str, Any]):
        repo_name = header.get("repo", "main_repo")
        branch = header.get("branch", "main")
        repo_path = self._get_repo_path(repo_name)
        
        if not os.path.exists(repo_path):
            send_message(conn, {
                "status": "OK",
                "code": 200,
                "exists": False,
                "message": f"雲端儲存庫 '{repo_name}' 尚未建立任何提交。"
            })
            return

        head = self._get_branch_head(repo_name, branch)
        history = self._get_commit_history(repo_name, head) if head else []
        self.log("STATUS", f"查詢儲存庫: {repo_name}, 分支: {branch}, 目前 HEAD: {head[:7] if head else 'None'}, 總提交數: {len(history)}", addr)

        send_message(conn, {
            "status": "OK",
            "code": 200,
            "exists": True,
            "repo": repo_name,
            "branch": branch,
            "head": head,
            "commit_count": len(history),
            "latest_commit": history[0] if history else None
        })

    def handle_push(self, conn: socket.socket, addr: tuple, header: Dict[str, Any], payload: bytes):
        repo_name = header.get("repo", "main_repo")
        branch = header.get("branch", "main")
        new_head = header.get("new_head", "")
        base_head = header.get("base_head", "")
        commits_to_apply = header.get("commits", [])

        self._ensure_repo(repo_name)
        current_head = self._get_branch_head(repo_name, branch)

        self.log("PUSH", f"收到推動請求 -> 儲存庫: {repo_name}, 分支: {branch}, 提交數: {len(commits_to_apply)}, base: {base_head[:7] if base_head else 'EMPTY'}, new: {new_head[:7]}", addr)

        # 衝突偵測 (加分項目：異常情況處理 - Non-Fast-Forward Push Conflict)
        if current_head and base_head != current_head:
            self.log("CONFLICT", f"版本衝突！遠端 HEAD ({current_head[:7]}) != 客戶端基礎 ({base_head[:7] if base_head else 'None'})", addr)
            send_message(conn, {
                "status": "CONFLICT",
                "code": 409,
                "remote_head": current_head,
                "message": (
                    f"[拒絕推動 - 409 Conflict] 雲端分支 '{branch}' 已有更新的提交 (HEAD: {current_head[:7]})\n"
                    f"您的本機分支落後於遠端，無法 Fast-Forward。\n"
                    f"解決方法：請先在 Client 端執行 'python client.py pull' 同步雲端最新版本後再推動！"
                )
            })
            return

        # 解壓縮並儲存檔案 Blobs
        blobs = unpack_blobs_from_zip(payload)
        for b_hash, b_data in blobs.items():
            self._save_blob(repo_name, b_hash, b_data)

        # 儲存 Commits 物件
        for c in commits_to_apply:
            self._save_commit(repo_name, c)

        # 更新遠端分支 HEAD 指標
        self._set_branch_head(repo_name, branch, new_head)

        self.log("SUCCESS", f"推動成功！已更新 {branch} 分支至 HEAD: {new_head[:7]}, 儲存 Blobs: {len(blobs)} 個", addr)
        send_message(conn, {
            "status": "OK",
            "code": 200,
            "head": new_head,
            "message": f"成功推送 {len(commits_to_apply)} 個提交至遠端 '{repo_name}' ({branch} -> {new_head[:7]})！"
        })

    def handle_pull(self, conn: socket.socket, addr: tuple, header: Dict[str, Any]):
        repo_name = header.get("repo", "main_repo")
        branch = header.get("branch", "main")
        client_head = header.get("client_head", "")

        repo_path = self._get_repo_path(repo_name)
        if not os.path.exists(repo_path):
            send_message(conn, {
                "status": "NOT_FOUND",
                "code": 404,
                "message": f"遠端不存在儲存庫 '{repo_name}'。"
            })
            return

        current_head = self._get_branch_head(repo_name, branch)
        self.log("PULL", f"收到拉取請求 -> Client HEAD: {client_head[:7] if client_head else 'EMPTY'}, Remote HEAD: {current_head[:7] if current_head else 'EMPTY'}", addr)

        if not current_head:
            send_message(conn, {
                "status": "UP_TO_DATE",
                "code": 304,
                "message": "遠端儲存庫目前為空，尚無任何提交。"
            })
            return

        if current_head == client_head:
            send_message(conn, {
                "status": "UP_TO_DATE",
                "code": 304,
                "message": "Already up to date (已經是最新版本，無需拉取)。"
            })
            return

        # 收集從 current_head 到 client_head 之間所有新增的 commits
        commits_to_send = []
        blobs_to_send: Dict[str, bytes] = {}
        curr = current_head

        while curr and curr != client_head:
            c = self._get_commit(repo_name, curr)
            if not c:
                break
            commits_to_send.append(c)
            # 收集此 commit 內包含的所有檔案 blob
            for filename, b_hash in c.get("tree", {}).items():
                if b_hash not in blobs_to_send:
                    b_data = self._get_blob(repo_name, b_hash)
                    if b_data is not None:
                        blobs_to_send[b_hash] = b_data
            curr = c.get("parent")

        # 打包成 ZIP
        payload = pack_blobs_to_zip(blobs_to_send)

        self.log("PULL", f"傳送 {len(commits_to_send)} 個提交、{len(blobs_to_send)} 個檔案物件 (封包大小: {len(payload)} bytes)", addr)

        send_message(conn, {
            "status": "OK",
            "code": 200,
            "head": current_head,
            "commits": commits_to_send,
            "message": f"成功拉取 {len(commits_to_send)} 個提交更新。"
        }, payload=payload)

    def handle_clone(self, conn: socket.socket, addr: tuple, header: Dict[str, Any]):
        repo_name = header.get("repo", "main_repo")
        branch = header.get("branch", "main")
        repo_path = self._get_repo_path(repo_name)

        self.log("CLONE", f"收到複製儲存庫請求 -> {repo_name}", addr)

        if not os.path.exists(repo_path):
            send_message(conn, {
                "status": "NOT_FOUND",
                "code": 404,
                "message": f"[錯誤 404] 雲端找不到儲存庫 '{repo_name}'。"
            })
            return

        current_head = self._get_branch_head(repo_name, branch)
        if not current_head:
            send_message(conn, {
                "status": "OK",
                "code": 200,
                "head": "",
                "commits": [],
                "message": "儲存庫已複製 (遠端為空儲存庫)。"
            })
            return

        all_commits = self._get_commit_history(repo_name, current_head)
        blobs_to_send = {}
        for c in all_commits:
            for fn, b_hash in c.get("tree", {}).items():
                if b_hash not in blobs_to_send:
                    b_data = self._get_blob(repo_name, b_hash)
                    if b_data is not None:
                        blobs_to_send[b_hash] = b_data

        payload = pack_blobs_to_zip(blobs_to_send)
        send_message(conn, {
            "status": "OK",
            "code": 200,
            "head": current_head,
            "branch": branch,
            "commits": all_commits,
            "message": f"成功複製倉庫 '{repo_name}' (總計 {len(all_commits)} 個提交)"
        }, payload=payload)

    def handle_log(self, conn: socket.socket, addr: tuple, header: Dict[str, Any]):
        repo_name = header.get("repo", "main_repo")
        branch = header.get("branch", "main")
        head = self._get_branch_head(repo_name, branch)
        history = self._get_commit_history(repo_name, head) if head else []

        self.log("LOG", f"查詢遠端提交紀錄 -> {repo_name} (共 {len(history)} 筆)", addr)
        send_message(conn, {
            "status": "OK",
            "code": 200,
            "repo": repo_name,
            "branch": branch,
            "head": head,
            "commits": history
        })

    # ==================== Multi-threaded Client Dispatcher ====================

    def handle_client(self, conn: socket.socket, addr: tuple):
        self.log("CONNECT", f"客戶端建立 TCP 三向交握連線", addr)
        try:
            while True:
                try:
                    header, payload = recv_message(conn)
                except ConnectionResetError:
                    self.log("DISCONNECT", "客戶端連線已正常中斷", addr)
                    break
                except Exception as e:
                    self.log("ERROR", f"接收封包解析異常: {e}", addr)
                    break

                action = header.get("action", "").upper()
                self.log("REQUEST", f"執行操作: {action} (Header大小: {len(json.dumps(header))}B, Payload: {len(payload)}B)", addr)

                if action == "PING":
                    self.handle_ping(conn, addr, header)
                elif action == "STATUS":
                    self.handle_status(conn, addr, header)
                elif action == "PUSH":
                    self.handle_push(conn, addr, header, payload)
                elif action == "PULL":
                    self.handle_pull(conn, addr, header)
                elif action == "CLONE":
                    self.handle_clone(conn, addr, header)
                elif action == "LOG":
                    self.handle_log(conn, addr, header)
                else:
                    self.log("WARN", f"未知的操作指令: {action}", addr)
                    send_message(conn, {
                        "status": "BAD_REQUEST",
                        "code": 400,
                        "message": f"未知的通訊協議指令: '{action}'"
                    })
        finally:
            conn.close()

    def get_local_ips(self) -> List[str]:
        """Fetch all host IP addresses for multi-machine demo explanation."""
        ips = ["127.0.0.1"]
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith("127.") and ip not in ips:
                    ips.append(ip)
        except Exception:
            pass
        return ips

    def start(self):
        """Starts the multithreaded socket server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.is_running = True

        print("=" * 70, flush=True)
        print(" MiniGit 雲端版本控制伺服器 (Cloud Server) 啟動中...", flush=True)
        print(" 主題: 第六項 檔案與資料服務 (版本管理與資料同步)", flush=True)
        print(f" 監聽位址 (Bind IP): {self.host}", flush=True)
        print(f" 監聽連接埠 (Port): {self.port}", flush=True)
        print(f" 雲端資料庫路徑: {self.repos_dir}", flush=True)
        print(" 可連線的 IP 位址 (本機與區域網路):", flush=True)
        for ip in self.get_local_ips():
            print(f"   -> {ip}:{self.port}", flush=True)
        print(" [提示] 兩台主機連線測試時，請在 Client 端輸入上述區域網路 IP (如 192.168.x.x)", flush=True)
        print(" 按 Ctrl + C 可安全停止伺服器", flush=True)
        print("=" * 70, flush=True)

        try:
            while self.is_running:
                conn, addr = self.server_socket.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            print("\n[系統] 收到中斷信號，正在關閉伺服器...")
        finally:
            if self.server_socket:
                self.server_socket.close()
            print("[系統] 伺服器已安全停止。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MiniGit Cloud Version Control Server")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host IP (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Binding Port (default: {DEFAULT_PORT})")
    parser.add_argument("--storage", default="cloud_storage", help="Cloud storage directory")
    args = parser.parse_args()

    server = MiniGitServer(host=args.host, port=args.port, storage_dir=args.storage)
    server.start()
