from fastapi import FastAPI
app = FastAPI()

#retrieve segment to get all of the relevant information from the api call
@app.get("/")

#basic server call, without any additional information (the root call)
def read_root():
    return {"message": "HopeKCC Server says Hello!"}