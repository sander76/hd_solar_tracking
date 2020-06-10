import pydantic

class AppConfig(pydantic.BaseSettings):
    mqtt_address:str="localhost"
