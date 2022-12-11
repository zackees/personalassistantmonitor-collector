"""
    app worker
"""

import os
from datetime import datetime
from tempfile import TemporaryDirectory

# import shutil
import uvicorn  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.responses import RedirectResponse, JSONResponse  # type: ignore
from fastapi import FastAPI, UploadFile, File  # type: ignore

from personalmonitor_collector.version import VERSION

STARTUP_DATETIME = datetime.now()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_description() -> str:
    """Get the app description."""
    lines = []
    lines.append("# personalmonitor_collector")
    lines.append("  * Version: " + VERSION)
    lines.append("  * Started at: " + str(STARTUP_DATETIME))
    return "\n".join(lines)


app = FastAPI(
    title="Video Server",
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

CHUNK_SIZE = 1024 * 64


async def async_download(src: UploadFile, dst: str) -> None:
    """Downloads a file to the destination."""
    with open(dst, mode="wb") as filed:
        while (chunk := await src.read(CHUNK_SIZE)) != b"":
            filed.write(chunk)
    await src.close()


@app.get("/", include_in_schema=False)
async def route_index() -> RedirectResponse:
    """By default redirect to the fastapi docs."""
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/get")
async def route_get() -> JSONResponse:
    """TODO - Add description."""
    return JSONResponse({"hello": "world"})


@app.post("/upload")
async def route_upload(file: UploadFile = File(...)) -> JSONResponse:
    """TODO - Add description."""
    with TemporaryDirectory() as temp_dir:
        temp_path: str = os.path.join(temp_dir, file.filename)
        await async_download(file, temp_path)
        # shutil.move(temp_path, final_path)
    return JSONResponse({"hello": "world"})


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8080)
