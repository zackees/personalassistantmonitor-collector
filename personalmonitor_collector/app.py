"""
    app worker
"""

# pylint: disable=logging-fstring-interpolation


import os
from datetime import datetime
from tempfile import TemporaryDirectory
from hmac import compare_digest
from io import StringIO
import requests  # type: ignore
import uvicorn  # type: ignore
from starlette_context import middleware, plugins, context
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.responses import RedirectResponse, PlainTextResponse  # type: ignore
from fastapi import FastAPI, UploadFile, File, Request, Header  # type: ignore
from personalmonitor_collector.settings import API_KEY, UPLOAD_CHUNK_SIZE
from personalmonitor_collector.log import make_logger, get_log_reversed
from personalmonitor_collector.version import VERSION


STARTUP_DATETIME = datetime.now()

log = make_logger(__name__)


def app_description() -> str:
    """Get the app description."""
    lines = []
    lines.append("Sensor Collection")
    lines.append("  * API Key: " + API_KEY)
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

app.add_middleware(
    middleware.ContextMiddleware,
    plugins=(plugins.ForwardedForPlugin(),),
)

# Super simple cache that stores the IP location for 24 hours.
IP_LOCATION_CACHE: dict[str, str] = {}
IP_LOCATION_CACHE_RESET_TIME = datetime.now()
IP_LOCATION_CACHE_RESET_PERIOD = 60 * 60 * 24


def try_find_ip_address(request: Request) -> str:
    """Finds the IP address of the computer."""
    # https://stackoverflow.com/a/166589
    forwarded_for = context.data.get("X-Forwarded-For", None)
    if forwarded_for is None:
        return request.client.host  # type: ignore
    first_ip = forwarded_for.split(",")[0]
    return first_ip


async def async_download(src: UploadFile, dst: str) -> None:
    """Downloads a file to the destination."""
    with open(dst, mode="wb") as filed:
        while (chunk := await src.read(UPLOAD_CHUNK_SIZE)) != b"":
            filed.write(chunk)
    await src.close()


@app.get("/", include_in_schema=False)
async def redirect_default() -> RedirectResponse:
    """By default redirect to the fastapi docs."""
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/time")
async def what_is_the_time(use_iso_fmt: bool = False) -> PlainTextResponse:
    """Gets the current timestamp. if use_iso_fmt is False then use unix timestamp."""
    log.info("Time requested.")
    if use_iso_fmt:
        # return PlainTextResponse(str(datetime.now()))
        # as isoformat
        return PlainTextResponse(str(datetime.now().isoformat()))
    unix_timestamp = float(datetime.now().timestamp())
    return PlainTextResponse(str(unix_timestamp))


@app.get("/locate_ip")
def locate_ip_address(request: Request, ip_address: str | None = None) -> PlainTextResponse:
    """
    Input an ip address and output the location.
    You can find your IP address at https://www.whatismyip.com/
    """
    global IP_LOCATION_CACHE_RESET_TIME  # pylint: disable=global-statement
    ipcache_alive_time = (datetime.now() - IP_LOCATION_CACHE_RESET_TIME).total_seconds()
    if ipcache_alive_time > IP_LOCATION_CACHE_RESET_PERIOD:
        log.info("Resetting IP location cache...")
        IP_LOCATION_CACHE_RESET_TIME = datetime.now()
        IP_LOCATION_CACHE.clear()
    ip_address = ip_address or try_find_ip_address(request)
    log.info("Geocoding IP address %s...", ip_address)
    cached_value = IP_LOCATION_CACHE.get(ip_address, None)
    if cached_value is not None:
        log.info("Using cached value for %s...", ip_address)
        return PlainTextResponse(cached_value)
    request_url = f"https://www.iplocate.io/api/lookup/{ip_address}"
    response = requests.get(request_url, timeout=10)
    response_values: dict = response.json()
    # Returns a response like:
    # {
    #   "ip": "52.119.119.42",
    #   "country": "United States",
    #   "country_code": "US",
    #   "city": "San Francisco",
    #   "continent": "North America",
    #   "latitude": 37.7703,
    #   "longitude": -122.4407,
    #   "time_zone": "America/Los_Angeles",
    #   "postal_code": "94117",
    #   "org": "MONKEYBRAINS",
    #   "asn": "AS32329",
    #   "subdivision": "California",
    #   "subdivision2": null
    # }
    buffer = StringIO()
    for key, value in response_values.items():
        buffer.write(f"{key}={value}\n")
        buffer.write("\n")
    buffer.write("\n")
    IP_LOCATION_CACHE[ip_address] = buffer.getvalue()
    return PlainTextResponse(status_code=response.status_code, content=buffer.getvalue())


@app.post("/v1/upload_mp3_data")
async def upload_sensor_data(
    mp3: UploadFile = File(...),
    api_key: str = Header(str),
    timestamp: int = Header(int),
    mac_address: str = Header(str),
    zipcode: str = Header(str),
) -> PlainTextResponse:
    """Upload endpoint for the PAM-sensor]"""
    if not compare_digest(api_key, API_KEY):
        return PlainTextResponse({"error": "Invalid API key"}, status_code=403)
    log.info(f"Upload called with:\n  File: {mp3.filename}\nMAC address: {mac_address}")
    with TemporaryDirectory() as temp_dir:
        # Just tests the download functionality and then discards the files.
        temp_datapath: str = os.path.join(temp_dir, mp3.filename)
        await async_download(mp3, temp_datapath)
        await mp3.close()
        log.info(f"Downloaded to {mp3.filename} to {temp_datapath}")
        log.info(f"mp3 timestamp: {timestamp}")
        log.info(f"mac_address: {mac_address}")
        log.info(f"zipcode: {zipcode}")

    return PlainTextResponse(f"Uploaded {mp3.filename}")


@app.post("/test_upload")
async def test_upload(datafile: UploadFile = File(...)) -> PlainTextResponse:
    """Upload endpoint for the PAM-sensor]"""
    with TemporaryDirectory() as temp_dir:
        # Just tests the download functionality and then discards the files.
        temp_datapath: str = os.path.join(temp_dir, datafile.filename)
        await async_download(datafile, temp_datapath)
        await datafile.close()
        log.info(f"Downloaded to {datafile.filename} to {temp_datapath}")
    return PlainTextResponse(f"Uploaded {datafile.filename}")


@app.get("/what_is_my_ip")
def what_is_my_ip(request: Request) -> PlainTextResponse:
    """Gets the current IP address."""
    log.info("IP address requested.")
    ip_address = try_find_ip_address(request)
    if ip_address is None:
        return PlainTextResponse(status_code=403, content="No IP address found.")
    return PlainTextResponse(ip_address)


# get the log file
@app.get("/log")
def system_log() -> PlainTextResponse:
    """Gets the log file."""
    out = get_log_reversed(100).strip()
    if not out:
        out = "(empty log file)"
    return PlainTextResponse(out)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8080)
