# type: ignore

"""
Data models for the app.
"""
# flake8: noqa: F772


from pydantic import (  # pylint: disable=no-name-in-module
    BaseModel,
    NonNegativeInt,
    NonNegativeFloat,
    constr,
    conint,
)


class AudioMetadata(BaseModel):  # pylint: disable=too-few-public-methods
    """Audio metadata that is uploaded with the sample."""

    type: constr(regex=r"^(wav|mp3|raw)$")  # noqa
    samplerate: int
    bitrate: conint(multiple_of=8)
    timestamp: NonNegativeInt
    lengthseconds: NonNegativeFloat
    macaddress: constr(regex=r"^[0-9a-fA-F]{12}$", max_length=64)
    zipcode: constr(max_length=64)
