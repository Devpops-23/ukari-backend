from fastapi import APIRouter, Header, HTTPException
import stripe
from pydantic import BaseModel

router = APIRouter(prefix="/stripe")

fake_stripe_accounts = {}

def get_user_from_token(token: str):
    if not token or not token.startswith("token-"):
        return None
    email = token.replace("token-", "")
    return fake_users.get(email)

# 1. Create connected account
@router.post("/create-account")
def create_account(authorization: str = Header(None)):
    user = get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    account = stripe.Account.create(
        type="express",
        email=user["email"],
        capabilities={"transfers": {"requested": True}},
    )

    fake_stripe_accounts[user["email"]] = account.id

    return {"account_id": account.id}

# 2. Generate onboarding link
@router.get("/onboard")
def onboard(authorization: str = Header(None)):
    user = get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    account_id = fake_stripe_accounts.get(user["email"])
    if not account_id:
        raise HTTPException(status_code=400, detail="Account not created")

    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url="http://localhost:3000/profile",
        return_url="http://localhost:3000/profile",
        type="account_onboarding",
    )

    return {"url": link.url}

# 3. Create payout
class PayoutRequest(BaseModel):
    amount: int

@router.post("/payout")
def payout(data: PayoutRequest, authorization: str = Header(None)):
    user = get_user_from_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    account_id = fake_stripe_accounts.get(user["email"])
    if not account_id:
        raise HTTPException(status_code=400, detail="Stripe account not found")

    transfer = stripe.Transfer.create(
        amount=data.amount,
        currency="usd",
        destination=account_id,
    )

    return {"status": "payout_sent", "transfer_id": transfer.id}
