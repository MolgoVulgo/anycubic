# Generated from HAR analysis; update if endpoints change.

BASE_URL = "https://cloud-universe.anycubic.com"

AUTH = {
    "get_oauth_token": {
        "method": "GET",
        "path": "/p/p/workbench/api/v3/public/getoauthToken",
    },
    "login_with_access_token": {
        "method": "POST",
        "path": "/p/p/workbench/api/v3/public/loginWithAccessToken",
    },
}

QUOTA = {
    "get_user_store": {
        "method": "POST",
        "path": "/p/p/workbench/api/work/index/getUserStore",
    }
}

FILES = {
    "list": {
        "method": "POST",
        "path": "/p/p/workbench/api/work/index/files",
    },
    "download_url": {
        "method": "POST",
        "path": "/p/p/workbench/api/work/index/getDowdLoadUrl",
    },
    "delete": {
        "method": "POST",
        "path": "/p/p/workbench/api/work/index/delFiles",
    },
    "rename": {
        "method": "POST",
        "path": "/p/p/workbench/api/work/index/renameFile",
    },
    "upload_status": {
        "method": "POST",
        "path": "/p/p/workbench/api/work/index/getUploadStatus",
    },
}

INFO = {
    "gcode_info": {
        "method": "GET",
        "path": "/p/p/workbench/api/api/work/gcode/info",
    }
}

PRINTERS = {
    "list": {
        "method": "GET",
        "path": "/p/p/workbench/api/work/printer/getPrinters",
    },
    "info": {
        "method": "POST",
        "path": "/p/p/workbench/api/work/printer/Info",
    },
    "info_v2": {
        "method": "GET",
        "path": "/p/p/workbench/api/v2/printer/info",
    },
}

PROJECTS = {
    "list": {
        "method": "GET",
        "path": "/p/p/workbench/api/work/project/getProjects",
    }
}

UPLOAD = {
    "lock_storage_space": {
        "method": "POST",
        "path": "/p/p/workbench/api/v2/cloud_storage/lockStorageSpace",
    },
    "new_upload_file": {
        "method": "POST",
        "path": "/p/p/workbench/api/v2/profile/newUploadFile",
    },
    "unlock_storage_space": {
        "method": "POST",
        "path": "/p/p/workbench/api/v2/cloud_storage/unlockStorageSpace",
    },
}

PRINT = {
    "send_order": {
        "method": "POST",
        "path": "/p/p/workbench/api/work/operation/sendOrder",
    }
}
