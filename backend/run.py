import os
import uvicorn

if __name__ == "__main__":
    env = os.getenv("ENV", "development")
    reload = env == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload)
