import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse


router = APIRouter()

PAGES_DIR = os.path.dirname(os.path.abspath(__file__))


@router.get("/home", response_class=HTMLResponse, include_in_schema=False)
def get_home():
    """
    Serve the Chat UI home page.
    """
    try:
        html_path = os.path.join(PAGES_DIR, "home.html")
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="home.html not found")


@router.get("/signup", response_class=HTMLResponse, include_in_schema=False)
def get_signup():
    """
    Serve the InsideBox Sign Up page.
    """
    try:
        html_path = os.path.join(PAGES_DIR, "signup.html")
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="signup.html not found")


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def get_login():
    """
    Serve the InsideBox Login page.
    """
    try:
        html_path = os.path.join(PAGES_DIR, "login.html")
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="login.html not found")
