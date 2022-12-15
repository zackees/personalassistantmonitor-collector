"""
    app worker
"""

# pylint: disable=logging-fstring-interpolation

import os
from datetime import datetime
from tempfile import TemporaryDirectory
from hmac import compare_digest
import requests  # type: ignore

# import shutil
import uvicorn  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse  # type: ignore
from fastapi import FastAPI, UploadFile, File  # type: ignore

from personalmonitor_collector.version import VERSION
from personalmonitor_collector.settings import API_KEY, UPLOAD_CHUNK_SIZE
from personalmonitor_collector.log import make_logger, get_log_reversed

STARTUP_DATETIME = datetime.now()

log = make_logger(__name__)


def app_description() -> str:
    """Get the app description."""
    lines = []
    lines.append("  * Version: " + VERSION)
    lines.append("  * Started at: " + str(STARTUP_DATETIME))
    return "\n".join(lines)


app = FastAPI(
    title="Personal Monitor Assistant Collector",
    version=VERSION,
    redoc_url=None,
    license_info={
        "name": "Private program, do not distribute",
    },
    description=app_description(),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def async_download(src: UploadFile, dst: str) -> None:
    """Downloads a file to the destination."""
    with open(dst, mode="wb") as filed:
        while (chunk := await src.read(UPLOAD_CHUNK_SIZE)) != b"":
            filed.write(chunk)
    await src.close()


@app.get("/", include_in_schema=False)
async def route_index() -> RedirectResponse:
    """By default redirect to the fastapi docs."""
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/time")
async def route_time(use_iso_fmt: bool = False) -> PlainTextResponse:
    """Gets the current timestamp. if use_iso_fmt is False then use unix timestamp."""
    log.info("Time requested.")
    if use_iso_fmt:
        # return PlainTextResponse(str(datetime.now()))
        # as isoformat
        return PlainTextResponse(str(datetime.now().isoformat()))
    unix_timestamp = float(datetime.now().timestamp())
    return PlainTextResponse(str(unix_timestamp))


@app.get("/geocode_ip")
def route_geocode_ip(ip_address: str) -> JSONResponse:
    """Service translates an IP address into a location."""
    log.info("Geocoding IP address %s...", ip_address)
    request_url = f"https://www.iplocate.io/api/lookup/{ip_address}"
    response = requests.get(request_url, timeout=10)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.post("/upload")
async def route_upload(
    api_key: str,
    mac_address: str,
    datafile: UploadFile = File(...),
    metadatafile: UploadFile = File(...),
) -> PlainTextResponse:
    """Upload endpoint for the PAM-sensor]"""
    if not compare_digest(api_key, API_KEY):
        return PlainTextResponse({"error": "Invalid API key"}, status_code=403)
    log.info(f"Upload called with:\n  File: {datafile.filename}\nMAC address: {mac_address}")
    with TemporaryDirectory() as temp_dir:
        temp_datapath: str = os.path.join(temp_dir, datafile.filename)
        temp_metadatapath: str = os.path.join(temp_dir, metadatafile.filename)
        await async_download(datafile, temp_datapath)
        await datafile.close()
        log.info(f"Downloaded to {datafile.filename} to {temp_metadatapath}")
        await async_download(metadatafile, temp_metadatapath)
        await metadatafile.close()
        log.info(f"Downloaded to {metadatafile.filename} to {temp_metadatapath}")
        # shutil.move(temp_path, final_path)
    return PlainTextResponse(f"Uploaded {datafile.filename} and {metadatafile.filename}")


# get the log file
@app.get("/log")
def route_log() -> PlainTextResponse:
    """Gets the log file."""
    out = get_log_reversed(100).strip()
    if not out:
        out = "(empty log file)"
    return PlainTextResponse(out)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8080)
