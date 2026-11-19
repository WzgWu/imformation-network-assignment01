"""
MiniGit Protocol Module (MGC-Protocol)
Shared network protocol logic for Client-Server communication.
Provides Length-Prefixed framing to solve TCP byte stream coalescing/fragmentation.
"""

import struct
import json
import socket
import io
import zipfile
from typing import Tuple, Dict, Any, Optional

# Protocol Constants
DEFAULT_PORT = 8888
HEADER_LENGTH_PREFIX_FORMAT = '!I'  # 4 bytes unsigned int, Network Byte Order (Big-Endian)
HEADER_LENGTH_PREFIX_SIZE = struct.calcsize(HEADER_LENGTH_PREFIX_FORMAT)
BUFFER_SIZE = 4096


def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    """
    Reads exactly `num_bytes` from the socket.
    Handles TCP byte-stream fragmentation.
    Raises ConnectionResetError if connection drops prematurely.
    """
    buffer = bytearray()
    while len(buffer) < num_bytes:
        chunk = sock.recv(num_bytes - len(buffer))
        if not chunk:
            raise ConnectionResetError("連線中斷：未接收到完整封包長度。")
        buffer.extend(chunk)
    return bytes(buffer)


def send_message(sock: socket.socket, header: Dict[str, Any], payload: bytes = b'') -> None:
    """
    Encapsulates and sends an Application Layer PDU (Protocol Data Unit).
    
    PDU Format:
    +------------------------------+---------------------------+-----------------------+
    | Header Length (4 Bytes, !I)  | JSON Header (UTF-8)       | Binary Payload        |
    +------------------------------+---------------------------+-----------------------+
    """
    header_copy = dict(header)
    header_copy['payload_size'] = len(payload)
    
    header_bytes = json.dumps(header_copy, ensure_ascii=False).encode('utf-8')
    header_len = len(header_bytes)
    
    # 4-byte big-endian header length
    length_prefix = struct.pack(HEADER_LENGTH_PREFIX_FORMAT, header_len)
    
    # Send atomic-like via sendall
    sock.sendall(length_prefix + header_bytes + payload)


def recv_message(sock: socket.socket) -> Tuple[Dict[str, Any], bytes]:
    """
    Receives and decodes an Application Layer PDU.
    Returns (header_dict, payload_bytes).
    """
    # 1. Read 4 bytes length prefix
    length_bytes = recv_exact(sock, HEADER_LENGTH_PREFIX_SIZE)
    header_len = struct.unpack(HEADER_LENGTH_PREFIX_FORMAT, length_bytes)[0]
    
    # 2. Read JSON header
    header_bytes = recv_exact(sock, header_len)
    header = json.loads(header_bytes.decode('utf-8'))
    
    # 3. Read Binary Payload if exists
    payload_size = header.get('payload_size', 0)
    if payload_size > 0:
        payload = recv_exact(sock, payload_size)
    else:
        payload = b''
        
    return header, payload


def pack_blobs_to_zip(blobs_dict: Dict[str, bytes]) -> bytes:
    """
    Compresses a dictionary of {blob_hash: file_bytes} into an in-memory ZIP byte array.
    """
    mem_file = io.BytesIO()
    with zipfile.ZipFile(mem_file, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for blob_hash, data in blobs_dict.items():
            zf.writestr(blob_hash, data)
    return mem_file.getvalue()


def unpack_blobs_from_zip(zip_bytes: bytes) -> Dict[str, bytes]:
    """
    Decompresses an in-memory ZIP byte array into {blob_hash: file_bytes}.
    """
    if not zip_bytes:
        return {}
    mem_file = io.BytesIO(zip_bytes)
    blobs = {}
    with zipfile.ZipFile(mem_file, mode='r') as zf:
        for name in zf.namelist():
            blobs[name] = zf.read(name)
    return blobs
