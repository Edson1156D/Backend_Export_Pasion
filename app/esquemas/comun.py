from pydantic import BaseModel, ConfigDict


def to_camel(nombre: str) -> str:
    partes = nombre.split("_")
    return partes[0] + "".join(parte.capitalize() for parte in partes[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )