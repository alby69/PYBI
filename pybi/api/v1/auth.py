"""FastAPI router for Auth endpoints in PyBI v1 REST API."""


from fastapi import APIRouter, Depends, Header, HTTPException, status

from pybi.api.v1.models import LoginRequest, TokenResponse, UserProfile
from pybi.auth.jwt_auth import (
    AuthUser,
    create_access_token,
    decode_access_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def get_current_user(authorization: str | None = Header(None)) -> AuthUser:
    """Dependency to extract and validate AuthUser with claims from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        # Fallback default user if no authorization header provided
        return AuthUser(username="guest", role="viewer", claims={"allowed_regions": "*"})

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )

    # Extract claims from payload
    reserved_keys = {"sub", "exp", "iat", "role", "email"}
    claims = {k: v for k, v in payload.items() if k not in reserved_keys}
    if "claims" in payload and isinstance(payload["claims"], dict):
        claims.update(payload["claims"])

    return AuthUser(
        username=payload["sub"],
        role=payload.get("role", "viewer"),
        email=payload.get("email"),
        claims=claims,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    """Authenticate user and issue JWT token."""
    if not req.username:
        raise HTTPException(status_code=400, detail="Username is required")

    role = "admin" if req.username.lower() == "admin" else "editor"
    user_profile = UserProfile(username=req.username, role=role, email=f"{req.username}@example.com")

    # Grant region claim based on username for demo/testing
    allowed_region = "EU" if "eu" in req.username.lower() else ("US" if "us" in req.username.lower() else "*")

    token = create_access_token(
        data={
            "sub": user_profile.username,
            "role": user_profile.role,
            "email": user_profile.email,
            "allowed_regions": allowed_region,
        }
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_profile)


@router.get("/me", response_model=UserProfile)
def get_me(user: AuthUser = Depends(get_current_user)) -> UserProfile:
    """Get profile details for currently authenticated user."""
    return UserProfile(username=user.username, role=user.role, email=user.email)
