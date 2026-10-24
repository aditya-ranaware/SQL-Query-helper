from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from app.limits import upload_limit
from pydantic import BaseModel, Field


from app.services.dataset import (
    MAX_CSV_BYTES,
    MAX_TABLES,
    DatasetError,
    from_csv_files,
    from_schema_text,
    sample_dataset,
    store,
)

router = APIRouter()


class SchemaRequest(BaseModel):
    text: str = Field(max_length=20_000)


def save(make):
    """Build a dataset, remember it for a while, and return what the screen needs."""
    try:
        dataset = make()
    except DatasetError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return store.add(dataset).summary()


@router.post("/dataset/csv", dependencies=[Depends(upload_limit)])
async def dataset_from_csv(files: list[UploadFile] = File(...)):
    if len(files) > MAX_TABLES:
        raise HTTPException(status_code=400, detail=f"Please upload at most {MAX_TABLES} files at a time.")
    contents = []
    for f in files:
        data = await f.read(MAX_CSV_BYTES + 1)   # never read more than the limit
        contents.append((f.filename or "table.csv", data))
    return save(lambda: from_csv_files(contents))


@router.post("/dataset/schema", dependencies=[Depends(upload_limit)])
def dataset_from_schema(req: SchemaRequest):
    return save(lambda: from_schema_text(req.text))

@router.post("/dataset/sample", dependencies=[Depends(upload_limit)])
def dataset_sample():
    return save(sample_dataset)


@router.get("/dataset/{dataset_id}")
def get_dataset(dataset_id: str):
    dataset = store.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Your data has expired. Please add it again.")
    return dataset.summary()