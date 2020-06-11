import pydantic


class AppConfig(pydantic.BaseSettings):
    mqtt_address: str = "localhost"


class PosAngData(pydantic.BaseModel):
    angle: int
    position: int
