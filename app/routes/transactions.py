# # app/routes/transactions.py
# import stripe
# from fastapi import APIRouter, HTTPException
# from app.schemas import PaymentRequest

# router = APIRouter()

# stripe.api_key = "sk_test_your_secret_key"

# @router.post("/pay")
# def pay(payment: PaymentRequest):
#     try:
#         charge = stripe.Charge.create(
#             amount=int(payment.amount * 100),
#             currency="usd",
#             source="tok_visa",
#             description="Data Purchase"
#         )
#         return {"status": charge["status"]}
#     except stripe.error.StripeError:
#         raise HTTPException(status_code=400, detail="Payment failed")
