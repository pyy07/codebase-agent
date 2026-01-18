#!/usr/bin/env python3
from fastapi import FastAPI

# 测试基本 FastAPI 语法
app = FastAPI()


@app.get("/")
async def test_route():
    return {"status": "ok"}


if __name__ == "__main__":
    print("Testing FastAPI...")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
