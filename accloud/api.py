from typing import List, Optional, Any, Dict
import json

import httpx

from endpoints import FILES, QUOTA, INFO, UPLOAD, PRINTERS, PROJECTS, PRINT
from .client import CloudClient
from .models import FileItem, Quota


def _json_or_raise(resp: httpx.Response) -> Dict[str, Any]:
    try:
        payload = resp.json()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Non-JSON response: {resp.text[:200]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected response: {payload!r}")
    code = payload.get("code")
    if code is not None and code != 1:
        msg = payload.get("msg", "Unknown error")
        raise RuntimeError(f"API error: code={code} msg={msg}")
    return payload


def get_quota(client: CloudClient) -> Quota:
    resp = client.request(QUOTA["get_user_store"]["method"], QUOTA["get_user_store"]["path"])
    payload = _json_or_raise(resp)
    data = payload.get("data") or {}
    return Quota(total_bytes=int(data.get("total_bytes", 0)), used_bytes=int(data.get("used_bytes", 0)))


def list_files(client: CloudClient, page: int = 1, limit: int = 10) -> List[FileItem]:
    payload = {"page": page, "limit": limit}
    resp = client.request(FILES["list"]["method"], FILES["list"]["path"], json=payload)
    payload = _json_or_raise(resp)
    items = []
    for row in payload.get("data") or []:
        items.append(FileItem(
            id=str(row.get("id")),
            name=row.get("old_filename") or row.get("filename") or "",
            size_bytes=int(row.get("size", 0)),
            created_at=int(row.get("time", 0)),
            file_type=row.get("file_type"),
            md5=row.get("md5"),
            url=row.get("url"),
            thumbnail=row.get("thumbnail"),
            gcode_id=str(row.get("gcode_id") or "") or None,
        ))
    return items


def get_download_url(client: CloudClient, file_id: str) -> str:
    payload = {"id": int(file_id)}
    resp = client.request(FILES["download_url"]["method"], FILES["download_url"]["path"], json=payload)
    payload = _json_or_raise(resp)
    return payload.get("data", "")


def delete_files(client: CloudClient, file_ids: List[str]) -> None:
    payload = {"idArr": [int(i) for i in file_ids]}
    resp = client.request(FILES["delete"]["method"], FILES["delete"]["path"], json=payload)
    _json_or_raise(resp)


def get_gcode_info(client: CloudClient, gcode_id: str) -> dict:
    params = {"id": int(gcode_id)}
    resp = client.request(INFO["gcode_info"]["method"], INFO["gcode_info"]["path"], params=params)
    payload = _json_or_raise(resp)
    return payload.get("data", {})


def list_printers(client: CloudClient, params: Optional[Dict[str, Any]] = None) -> dict:
    resp = client.request(PRINTERS["list"]["method"], PRINTERS["list"]["path"], params=params or {})
    payload = _json_or_raise(resp)
    return payload.get("data", payload)


def get_printer_info(client: CloudClient, printer_id: str) -> dict:
    payload = {"id": int(printer_id)}
    resp = client.request(PRINTERS["info"]["method"], PRINTERS["info"]["path"], json=payload)
    payload = _json_or_raise(resp)
    return payload.get("data", payload)


def get_printer_info_v2(client: CloudClient, printer_id: str) -> dict:
    params = {"id": int(printer_id)}
    resp = client.request(PRINTERS["info_v2"]["method"], PRINTERS["info_v2"]["path"], params=params)
    payload = _json_or_raise(resp)
    return payload.get("data", payload)


def get_projects(client: CloudClient, printer_id: str, print_status: int = 1, page: int = 1, limit: int = 10) -> dict:
    params = {
        "limit": int(limit),
        "page": int(page),
        "print_status": int(print_status),
        "printer_id": int(printer_id),
    }
    resp = client.request(PROJECTS["list"]["method"], PROJECTS["list"]["path"], params=params)
    payload = _json_or_raise(resp)
    return payload.get("data", payload)


def upload_file(client: CloudClient, path: str, name: Optional[str] = None) -> str:
    filename = name or str(path).split('/')[-1]
    size = __import__('os').path.getsize(path)

    # 1) lock storage
    lock_payload = {"name": filename, "size": size, "is_temp_file": 0}
    lock_resp = client.request(UPLOAD["lock_storage_space"]["method"], UPLOAD["lock_storage_space"]["path"], json=lock_payload)
    lock_data = _json_or_raise(lock_resp).get("data", {})
    lock_id = lock_data.get('id')
    pre_sign = lock_data.get('preSignUrl')
    if not pre_sign:
        raise RuntimeError('Missing preSignUrl from lockStorageSpace')

    # 2) PUT to S3
    with open(path, 'rb') as f:
        put_resp = httpx.put(pre_sign, content=f)
        put_resp.raise_for_status()

    # 3) register upload
    new_payload = {"user_lock_space_id": lock_id}
    new_resp = client.request(UPLOAD["new_upload_file"]["method"], UPLOAD["new_upload_file"]["path"], json=new_payload)
    file_id = _json_or_raise(new_resp).get("data", {}).get("id")

    # 4) unlock storage
    unlock_payload = {"id": lock_id, "is_delete_cos": 0}
    unlock_resp = client.request(UPLOAD["unlock_storage_space"]["method"], UPLOAD["unlock_storage_space"]["path"], json=unlock_payload)
    _json_or_raise(unlock_resp)

    return str(file_id)


def send_print_order(
    client: CloudClient,
    file_id: str,
    printer_id: str,
    project_id: str,
    order_id: str,
    is_delete_file: str,
    data_payload: Dict[str, Any],
) -> dict:
    form: Dict[str, Any] = {
        "printer_id": str(printer_id),
        "project_id": str(project_id),
        "order_id": str(order_id),
        "is_delete_file": str(is_delete_file),
        "data": json.dumps(data_payload, separators=(",", ":"), ensure_ascii=True),
    }
    if str(file_id) != str(data_payload.get("file_id", "")):
        data_payload = dict(data_payload)
        data_payload["file_id"] = str(file_id)
        form["data"] = json.dumps(data_payload, separators=(",", ":"), ensure_ascii=True)
    resp = client.request(PRINT["send_order"]["method"], PRINT["send_order"]["path"], data=form)
    return _json_or_raise(resp)


def send_video_order(client: CloudClient, printer_id: str, order_id: int = 1001) -> dict:
    # 0x3E9 (1001) correspond à l’événement vidéo MQTT observé dans l’APK.
    form: Dict[str, Any] = {
        "printer_id": int(printer_id),
        "order_id": int(order_id),
    }
    resp = client.request(PRINT["send_order"]["method"], PRINT["send_order"]["path"], data=form)
    return _json_or_raise(resp)
