
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SupplierListItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity_bags: int | None = Field(default=None, ge=0)
    tub_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")

        return self
